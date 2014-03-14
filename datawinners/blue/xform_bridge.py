import itertools
import os
from xml.etree import ElementTree as ET

from lxml import etree
import xmldict
from pyxform import create_survey_element_from_dict
from pyxform.xls2json import parse_file_to_json

from mangrove.errors.MangroveException import QuestionAlreadyExistsException
from datawinners.accountmanagement.models import NGOUserProfile
from datawinners.main.database import get_database_manager
from datawinners.project.helper import generate_questionnaire_code
from datawinners.project.models import Project
from datawinners.questionnaire.questionnaire_builder import QuestionnaireBuilder
from mangrove.form_model.field import FieldSet, GeoCodeField, DateField
from mangrove.form_model.form_model import FormModel


# noinspection PyUnresolvedReferences
from datawinners.search import *

class XlsFormParser():
    type_dict = {'repeat': ['repeat'],
                 'field': ['text', 'integer', 'date', 'geopoint'],
                 'select': ['select one', 'select all that apply']
                 }
    supported_type = list(itertools.chain(*type_dict.values()))

    def __init__(self, path_or_file, project_name='Project'):
        if isinstance(path_or_file, basestring):
            self._file_object = None
            path = path_or_file
        else:
            self._file_object = path_or_file
            path = path_or_file.name

        self.xform_dict = parse_file_to_json(path, default_name=project_name, file_object=path_or_file)
        survey = create_survey_element_from_dict(self.xform_dict)
        self.xform = survey.to_xml()

    def _create_question(self, c):
        question = None
        if c['type'] in self.type_dict['repeat']:
            question = self._repeat(c)
        elif c['type'] in self.type_dict['field']:
            question = self._field(c)
        elif c['type'] in self.type_dict['select']:
            question = self._select(c)
        return question

    def parse(self):
        questions = [self._create_question(c) for c in self.xform_dict['children'] if c['type'] in self.supported_type]
        return self.xform, questions

    def _repeat(self, repeat):
        group_label = repeat['label']
        if not group_label: #todo create appropriate error class
            raise QuestionAlreadyExistsException('Unique repeat label is required')
        group_name = repeat['name']
        children = repeat['children']
        questions = [self._create_question(c) for c in children if c['type'] in self.supported_type]
        q = {'title': group_label, 'type': 'field_set', "is_entity_question": False,
                 "code": group_name, "name": group_label, 'required': False,
                 "instruction": "No answer required",
                 'fields':questions}
        return q

    def _field(self, field):
        xform_dw_type_dict = {'text': 'text', 'integer': 'integer', 'date': 'date', 'geopoint': 'geocode'}
        help_dict = {'text': 'word', 'integer': 'number', 'date': 'date', 'geopoint': 'geopoint'}
        name = field['label']
        code = field['name']
        type = field['type']

        q = {'title': name, 'type': xform_dw_type_dict[type], "is_entity_question": False,
                 "code": code, "name": name, 'required': self.is_required(field),
                 "instruction": "Answer must be a %s" % help_dict[type]} # todo help text need improvement
        if type == 'date':
                q.update({'date_format': 'dd.mm.yyyy', 'event_time_field_flag': False,
                          "instruction": "Answer must be a date in the following format: day.month.year. Example: 25.12.2011"})
        return q

    def _select(self, field):
        name = field['label']
        code = field['name']
        question = {"title": name, "code": code, "type": "select", 'required': self.is_required(field),
                 "choices": [{'value':{'text':f['label'], 'val':f['name']}} for f in field['choices']], "is_entity_question": False}
        if field['type'] == 'select one':
            question.update({"type": "select1"})
        return question

    def is_required(self, field):
        if field.get('bind') and 'yes' == str(field['bind'].get('required')).lower():
            return True
        return False

class MangroveService():

    def __init__(self, user, xform_as_string, json_xform_data, questionnaire_code=None, project_name=None):
        self.user = user
        user_profile = NGOUserProfile.objects.filter(user=self.user)[0]
        self.manager = get_database_manager(self.user)
        self.entity_type = ['reporter']
        self.questionnaire_code =  questionnaire_code if questionnaire_code else generate_questionnaire_code(self.manager)
        self.name = 'Xlsform Project-' + self.questionnaire_code if not project_name else project_name
        self.language = 'en'
        self.xform = xform_as_string
        self.xform_with_form_code = self._update_xform(xform_as_string, self.questionnaire_code, user_profile.reporter_id)
        self.json_xform_data = json_xform_data

    def _create_questionnaire(self):
        form_model = FormModel(self.manager, entity_type=self.entity_type, name=self.name, type='survey',
                               fields=[], form_code=self.questionnaire_code, language=self.language)
        QuestionnaireBuilder(form_model, self.manager).update_questionnaire_with_questions(self.json_xform_data)
        form_model.xform = self.xform_with_form_code
        questionnaire_id = form_model.save()
        return questionnaire_id

    def _add_model_sub_element(self, root, name, value):
        project_name = [r.text for r in root.iter('{http://www.w3.org/1999/xhtml}title')][0]
        model = '{http://www.w3.org/2002/xforms}%s' % project_name
        [self._add(r, name, value) for r in root.iter(model)]

        node_set = '/%s/%s' % (project_name, name)
        [ET.SubElement(r, '{http://www.w3.org/2002/xforms}bind', {'nodeset': node_set, 'type': "string"}) for r in root.getiterator() if
            r.tag == '{http://www.w3.org/2002/xforms}model']

    def _add(self, instance, name, value):
        e = ET.SubElement(instance,'{http://www.w3.org/2002/xforms}%s' %name)
        e.text = value
        return e

    def _update_xform(self, xform_as_string, questionnaire_code, rep_id):
        xform_with_form_code = self._add_from_code(xform_as_string, questionnaire_code)
        xform_with_rep_id = self._add_reporter_id(xform_with_form_code, rep_id)
        return xform_with_rep_id


    def _add_from_code(self, xform, form_code):
        ET.register_namespace('', 'http://www.w3.org/2002/xforms')
        root = ET.fromstring(xform.encode('utf-8'))
        self._add_model_sub_element(root, 'form_code', form_code)
        return '<?xml version="1.0"?>%s' % ET.tostring(root)

    def _add_reporter_id(self, xform, rep_id):
        ET.register_namespace('', 'http://www.w3.org/2002/xforms')
        root = ET.fromstring(xform)
        self._add_model_sub_element(root, 'eid', rep_id)
        return '<?xml version="1.0"?>%s' % ET.tostring(root)


    def create_project(self):
        questionnaire_id = self._create_questionnaire()

        project = Project(name=self.name, goals='project created using xform',
                  project_type='survey', entity_type=self.entity_type[0],
                  activity_report='yes',
                  devices=[u'sms', u'web', u'smartPhone'],
                  language=self.language)
        project.qid = questionnaire_id

        ngo_admin = NGOUserProfile.objects.get(user=self.user)
        project.data_senders.append(ngo_admin.reporter_id)

        id = project.save(self.manager)

        return id, self.name


class XFormSubmissionProcessor():

    def get_dict(self, field, value):
        if not value:
            return {field.code: ''}
        if type(field) is FieldSet:
            dicts = []
            for v in value:
                dict = {}
                for f in field.fields:
                    dict.update(self.get_dict(f, v[f.code]))
                dicts.append(dict)
            return {field.code: dicts}
        elif type(field) is DateField:
            return {field.code: '-'.join(value.split('.')[::-1])}
        elif type(field) is GeoCodeField:
            return {field.code: value.replace(',', ' ')}
        else:
            return {field.code: value}

    def create_xform_instance_of_submission(self, form_model_fields, submission_values):
        # todo instead of using form_model fields, user xform to find the fields
        d, s = {}, {}
        for f in form_model_fields:
            d.update(self.get_dict(f, submission_values[f.code]))
        s.update({'instance':d})
        instance_xml = xmldict.dict_to_xml(s)
        instance_xml_with_ns = instance_xml.replace('>', ' xmlns="http://www.w3.org/2002/xforms">', 1)
        return instance_xml_with_ns

    def remove_and_add_new_instance(self, instance_node, new_instance_element):
        project_model_node = [f for f in instance_node][0]

        keep = ['{http://www.w3.org/2002/xforms}meta',
            '{http://www.w3.org/2002/xforms}form_code']

        keep_these = [child for child in project_model_node if child.tag in keep]
        del project_model_node[:]
        project_model_node.extend(keep_these)

        #ET.register_namespace('', 'http://www.w3.org/2002/xforms')
        et_fromstring = ET.fromstring(new_instance_element.encode('utf-8'))

        [project_model_node.append(f) for f in et_fromstring]

        return project_model_node


    def update_instance_children(self, xform, new_instance_element):
        ET.register_namespace('', 'http://www.w3.org/2002/xforms')
        root = ET.fromstring(xform.encode('utf-8'))
        # todo find a better way instead of using getiterator
        [self.remove_and_add_new_instance(e, new_instance_element)
            for e in root.getiterator() if e.tag == '{http://www.w3.org/2002/xforms}instance']

        return ET.tostring(root)


    def xform_edit_submission(self, form_fields, xform, submission_values):
        instance_xml = self.create_xform_instance_of_submission(form_fields, submission_values)
        submission_xform = self.update_instance_children(xform, instance_xml)
        return submission_xform

DIR = os.path.dirname(__file__)

class XFormTransformer():

    def __init__(self, xform_as_string):
        self.xform = xform_as_string
        self.xls_folder = os.path.join(DIR, 'xsl')
        self.HTML_FORM = os.path.join(self.xls_folder, 'openrosa2html5form_php5.xsl')
        self.XML_MODEL = os.path.join(self.xls_folder, 'openrosa2xmlmodel.xsl')

    def transform(self):
        model_xslt = etree.XML(open(self.XML_MODEL, 'r').read())
        transform_model = etree.XSLT(model_xslt)
        model_doc = etree.fromstring(self.xform)
        model_tree = transform_model(model_doc)

        form_xslt = etree.XML(open(self.HTML_FORM, 'r').read())
        transform_form = etree.XSLT(form_xslt)
        form_doc = etree.fromstring(self.xform)
        form_tree = transform_form(form_doc)

        r = model_tree.getroot()
        r.extend(form_tree.getroot())
        return etree.tostring(r)
