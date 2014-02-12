from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET

from django.contrib.auth.models import User
import xmldict
from mangrove.errors.MangroveException import QuestionAlreadyExistsException
from pyxform import create_survey_from_path, create_survey_element_from_dict, create_survey_from_xls
from pyxform.xform2json import XFormToDict
from pyxform.xls2json import workbook_to_json, SurveyReader
from pyxform.xls2json_backends import xls_to_dict

from datawinners.accountmanagement.models import NGOUserProfile
from datawinners.main.database import get_database_manager
from datawinners.project.helper import generate_questionnaire_code
from datawinners.project.models import Project
from datawinners.questionnaire.questionnaire_builder import QuestionnaireBuilder
from mangrove.form_model.field import FieldSet
from mangrove.form_model.form_model import FormModel

# noinspection PyUnresolvedReferences
from datawinners.search import *

class XlsFormToJson():

    def __init__(self, file_content_or_path, is_path_to_file=False, project_name='Project'):
        if is_path_to_file:
            survey = create_survey_from_path(file_content_or_path)
            self.xform_as_string = survey.to_xml()
            self.file_path = file_content_or_path
        else:
            f = NamedTemporaryFile(delete=True)
            f.write(file_content_or_path)
            f.seek(0)
            workbook_dict = xls_to_dict(f)
            json_dict = workbook_to_json(workbook_dict, form_name=project_name)
            survey = create_survey_element_from_dict(json_dict)
            self.xform_as_string = survey.to_xml()

    def parse(self):
        return self.xform_as_string, XfromToJson(self.xform_as_string).parse()

    def parse_new(self):
        excel_reader = SurveyReader(self.file_path)
        d = excel_reader.to_json_dict()
        questions = []
        for c in d['children']:
            if c['type'] == 'repeat':
                questions.append(self._repeat(c))
            elif c['type'] in ['text', 'int', 'date']:
                questions.append(self._field(c))
            elif c['type'] == 'select one':
                questions.append(self._select1(c))
        return self.xform_as_string, questions

    def _repeat(self, repeat):
        group_label = repeat['label']
        if not group_label: #todo create appropriate error class
            raise QuestionAlreadyExistsException('Unique repeat label is required')
        group_name = repeat['name']
        children = repeat['children']
        questions = []
        questions.extend([self._field(c) for c in children])
        q = {'title': group_label, 'type': 'field_set', "is_entity_question": False,
                 "code": group_name, "name": group_label, 'required': False,
                 "instruction": "No answer required",
                 'fields':questions}
        return q

    def _field(self, field):
        xform_dw_type_dict = {'text': 'text', 'int': 'integer', 'date': 'date'}
        help_dict = {'text': 'word', 'int': 'number', 'date': 'date'}
        name = field['label']
        code = field['name']
        type = field['type']
        q = {'title': name, 'type': xform_dw_type_dict[type], "is_entity_question": False,
                 "code": code, "name": name, 'required': True,
                 "instruction": "Answer must be a %s" % help_dict[type]} # todo help text need improvement
        if type == 'date':
                q.update({'date_format': 'dd.mm.yyyy', 'event_time_field_flag': False,
                          "instruction": "Answer must be a date in the following format: day.month.year. Example: 25.12.2011"})
        return q

    def _select1(self, field):
        name = field['label']
        code = field['name']

        q = {"title": name, "type": "select1", "code": code, 'required': True,
                 "choices": [{'text':f['label'], 'val':f['name']} for f in field['choices']], "is_entity_question": False}
        return q

class XfromToJson():

    def __init__(self, xform_as_string):
        self.xform = xform_as_string

    def parse(self):
        return self._transform()

    def _transform(self):
        xform_dict = XFormToDict(self.xform).get_dict()
        self.name_attrib_dict = {self.last_value(bind['nodeset']): bind for bind in xform_dict['html']['head']['model']['bind']}
        questions = []

        [f['nodeset'] for f in xform_dict['html']['head']['model']['bind'] if f['nodeset'].find]

        groups = xform_dict['html']['body'].get('group')
        if groups:
            questions.extend(self.call_appropriate(groups,self.convert_group))
        inputs = xform_dict['html']['body']['input']
        questions.extend(self.call_appropriate(inputs, self.create_question))
        return questions


    def call_appropriate(self, param, call_fun, return_list=True):
        if type(param) is list:
            return [call_fun(o) for o in param]
        else:
            return [call_fun(param)] if return_list else call_fun(param)

    def last_value(self, input):
        return input.rsplit('/', 1)[-1]

    def convert_group(self, group):
        group_label = group['label']
        if not group_label: #todo create appropriate error class
            raise QuestionAlreadyExistsException('Unique group label is required')
        group_name = self.last_value(group['ref'])
        repeats = group['repeat']
        questions = []
        questions.extend(self.call_appropriate(repeats, self.convert_repeat, False))
        #todo remove this duplication; note: required is Flase
        q = {'title': group_label, 'type': 'field_set', "is_entity_question": False,
                 "code": group_name, "name": group_label, 'required': False,
                 "instruction": "No answer required",
                 'fields':questions}
        return q

    def _parse_field_set(self):
        pass

    def convert_repeat(self, repeat):
        inputs = repeat['input']
        return self.call_appropriate(inputs, self.create_question)

    def create_question(self, input):
        xform_dw_type_dict = {'string': 'text', 'int': 'integer', 'date': 'date'}
        help_dict = {'string': 'word', 'int': 'number', 'date': 'date'}
        name = input['label']
        code = self.last_value(input['ref'])
        type = self.name_attrib_dict[code]['type']
        # todo entityquestion
        # todo maintain the sequence of fields
        q = {'title': name, 'type': xform_dw_type_dict[type], "is_entity_question": False,
                 "code": code, "name": name, 'required': True,
                 "instruction": "Answer must be a %s" % help_dict[type]} # todo help text need improvement
        if type == 'date':
                q.update({'date_format': 'dd.mm.yyyy', 'event_time_field_flag': False,
                          "instruction": "Answer must be a date in the following format: day.month.year. Example: 25.12.2011"})

        return q

class MangroveService():

    def __init__(self, xform_as_string, json_xform_data, project_name=None):
        self.user = User.objects.get(username="tester150411@gmail.com")
        self.manager = get_database_manager(self.user)
        self.entity_type = ['reporter']
        self.questionnaire_code =  generate_questionnaire_code(self.manager)
        self.name = 'Xlsform Project-' + self.questionnaire_code if not project_name else project_name + "-" + self.questionnaire_code
        self.project_state = 'Test'
        self.language = 'en'
        self.xform = xform_as_string
        self.xform_with_form_code = self._add_from_code(xform_as_string, self.questionnaire_code)
        self.json_xform_data = json_xform_data

    def _create_questionnaire(self):

        #todo make sure that xform field is added to FormModel
        '''
        @property
        def xform(self):
            return self._doc.xform

        @xform.setter
        def xform(self, value):
            self._doc.xform = value
        '''

        form_model = FormModel(self.manager, entity_type=self.entity_type, name=self.name, type='survey',
                               state=self.project_state, fields=[], form_code=self.questionnaire_code, language=self.language)
        QuestionnaireBuilder(form_model, self.manager).update_questionnaire_with_questions(self.json_xform_data)
        form_model.xform = self.xform_with_form_code
        questionnaire_id = form_model.save()
        return questionnaire_id

    def _add_form_code_bind_element(self, root):
        project_name = [r.text for r in root.iter('{http://www.w3.org/1999/xhtml}title')][0]
        node_set = '/%s/form_code' % project_name
        [ET.SubElement(r, '{http://www.w3.org/2002/xforms}bind', {'nodeset': node_set, 'type': "string"}) for r in root.getiterator() if
            r.tag == '{http://www.w3.org/2002/xforms}model']

    def _add_from_code_element(self, form_code, root):
        project_name = [r.text for r in root.iter('{http://www.w3.org/1999/xhtml}title')][0]
        a = '{http://www.w3.org/2002/xforms}%s' % project_name
        [self._assign(r, form_code) for r in root.iter(a)]

    def _add_from_code(self, xform, form_code):
        ET.register_namespace('', 'http://www.w3.org/2002/xforms')
        root = ET.fromstring(xform)
        self._add_form_code_bind_element(root)
        self._add_from_code_element(form_code, root)
        return '<?xml version="1.0"?>%s' % ET.tostring(root)

    def _assign(self, instance, form_code):
        e = ET.SubElement(instance,'{http://www.w3.org/2002/xforms}form_code')
        e.text = form_code
        return e

    def create_project(self):
        questionnaire_id = self._create_questionnaire()

        project = Project(name=self.name, goals='project created using xform',
                  project_type='survey', entity_type=self.entity_type[0],
                  activity_report='yes',
                  state=self.project_state, devices=[u'sms', u'web', u'smartPhone'],
                  language=self.language)
        project.qid = questionnaire_id

        ngo_admin = NGOUserProfile.objects.get(user=self.user)
        project.data_senders.append(ngo_admin.reporter_id)

        id = project.save(self.manager)

        return id, self.name


class XFormSubmissionProcessor():

    def get_dict(self, field, value):
        if type(field) is FieldSet:
            dicts = []
            for v in value:
                dict = {}
                for f in field.fields:
                    dict.update(self.get_dict(f, v[f.code]))
                dicts.append(dict)
            return {field.code: dicts}
        else:
            return {field.code: value}

    def create_xform_instance_of_submission(self, form_model_fields, submission_values):
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
        et_fromstring = ET.fromstring(new_instance_element)

        [project_model_node.append(f) for f in et_fromstring]

        return project_model_node


    def update_instance_children(self, xform, new_instance_element):
        ET.register_namespace('', 'http://www.w3.org/2002/xforms')
        root = ET.fromstring(xform)
        # todo find a better way instead of using getiterator
        [self.remove_and_add_new_instance(e, new_instance_element)
            for e in root.getiterator() if e.tag == '{http://www.w3.org/2002/xforms}instance']

        return ET.tostring(root)


    def xform_edit_submission(self, form_fields, xform, submission_values):
        instance_xml = self.create_xform_instance_of_submission(form_fields, submission_values)
        submission_xform = self.update_instance_children(xform, instance_xml)
        return submission_xform