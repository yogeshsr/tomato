from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET

from django.contrib.auth.models import User
from mangrove.errors.MangroveException import QuestionAlreadyExistsException
from pyxform import create_survey_from_path, create_survey_element_from_dict
from pyxform.xform2json import XFormToDict
from pyxform.xls2json import workbook_to_json
from pyxform.xls2json_backends import xls_to_dict

from datawinners.accountmanagement.models import NGOUserProfile
from datawinners.main.database import get_database_manager
from datawinners.project.helper import generate_questionnaire_code
from datawinners.project.models import Project
from datawinners.questionnaire.questionnaire_builder import QuestionnaireBuilder
from mangrove.form_model.form_model import FormModel

# noinspection PyUnresolvedReferences
from datawinners.search import *

class XlsFormToJson():

    def __init__(self, file_content_or_path, is_path_to_file=False):
        if is_path_to_file:
            survey = create_survey_from_path(file_content_or_path)
            self.xform_as_string = survey.to_xml()
        else:
            f = NamedTemporaryFile(delete=True)
            f.write(file_content_or_path)
            f.seek(0)
            workbook_dict = xls_to_dict(f)
            json_dict = workbook_to_json(workbook_dict, form_name='some_name')
            survey = create_survey_element_from_dict(json_dict)
            self.xform_as_string = survey.to_xml()

    def parse(self):
        return self.xform_as_string, XfromToJson(self.xform_as_string).parse()


class XfromToJson():

    def __init__(self, xform_as_string):
        self.xform = xform_as_string

    def parse(self):
        return self._transform()

    def _transform(self):
        xform_dict = XFormToDict(self.xform).get_dict()
        self.name_attrib_dict = {self.last_value(bind['nodeset']): bind for bind in xform_dict['html']['head']['model']['bind']}
        questions = []
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

    def __init__(self, xform_as_string, json_xform_data):
        self.user = User.objects.get(username="tester150411@gmail.com")
        self.manager = get_database_manager(self.user)
        self.entity_type = ['reporter']
        self.questionnaire_code =  generate_questionnaire_code(self.manager)
        self.name = 'Xlsform Project-' + self.questionnaire_code
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

        p = project.save(self.manager)

        return p, self.name