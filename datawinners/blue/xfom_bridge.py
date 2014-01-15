from django.contrib.auth.models import User
from xml.etree import ElementTree as ET
from pyxform.xform2json import XFormToDict
from datawinners.accountmanagement.models import NGOUserProfile
from datawinners.main.database import get_database_manager
from datawinners.project.models import Project
from datawinners.questionnaire.questionnaire_builder import QuestionnaireBuilder
from mangrove.form_model.form_model import FormModel
# noinspection PyUnresolvedReferences
from datawinners.search import *

class XfromToJson():

    def __init__(self, xform_as_string):
        self.xform = xform_as_string

    def parse(self):
        name_label_type_dict = self._parse_xform()
        return self._transform_xform_to_json_post(name_label_type_dict)

    # intial implementation; can be removed
    def _parse_xform_custom(self):
        root = ET.fromstring(self.xform)
        name_label_dict = {r.attrib['ref']: r._children[0].text for r in root.iter('{http://www.w3.org/2002/xforms}input')}
        name_attrib_dict = {r.attrib['nodeset']: r.attrib for r in root.iter('{http://www.w3.org/2002/xforms}bind')}

        name_label_type_dict = {n: {'label':name_label_dict[n], 'type':name_attrib_dict[n]['type']} for n,l in name_label_dict.items()}

        return name_label_type_dict

    def _parse_xform(self):
        # using pyxform
        xform_dict = XFormToDict(self.xform).get_dict()
        name_label_dict = {input['ref']: input['label'] for input in xform_dict['html']['body']['input']}
        name_attrib_dict = {bind['nodeset']: bind for bind in xform_dict['html']['head']['model']['bind']}

        name_label_type_dict = {n: {'label':name_label_dict[n], 'type':name_attrib_dict[n]['type']} for n,l in name_label_dict.items()}

        return name_label_type_dict

    def _transform_xform_to_json_post(self, name_label_type_dict):
        xform_dw_type_dict = {'string': 'text', 'int': 'integer', 'date': 'date'}
        help_dict = {'string': 'word', 'int': 'number', 'date': 'date'}
        json_xform_data = []
        for k, v in name_label_type_dict.items():
            d = {'title': v['label'], 'type': xform_dw_type_dict[v['type']], "is_entity_question": False,
                 "code": k.rsplit('/', 1)[-1], "name": k, 'required': True,
                 "instruction": "Answer must be a %s" % help_dict[v['type']]} # todo help text need improvement

            if v['type'] == 'date':
                d.update({'date_format': 'dd.mm.yyyy', 'event_time_field_flag': False,
                          "instruction": "Answer must be a date in the following format: day.month.year. Example: 25.12.2011"})

            json_xform_data.append(d)
        return json_xform_data

class MangroveService():

    def __init__(self, xform_as_string, incremented_number):
        i = incremented_number
        self.user = User.objects.get(username="tester150411@gmail.com")
        self.manager = get_database_manager(self.user)
        self.entity_type = ['reporter']
        self.name = 'xform-project-' + str(i)
        self.questionnaire_code = str(47 + i)
        self.project_state = 'Test'
        self.language = 'en'
        self.xform = xform_as_string

    def create_questionnaire(self, json_xform_data):

        form_model = FormModel(self.manager, entity_type=self.entity_type, name=self.name, type='survey',
                               state=self.project_state, fields=[], form_code=self.questionnaire_code, language=self.language)
        QuestionnaireBuilder(form_model, self.manager).update_questionnaire_with_questions(json_xform_data)
        form_model.xform = self.xform
        questionnaire_id = form_model.save()
        return questionnaire_id

    def create_project(self, questionnaire_id):

        project = Project(name=self.name, goals='project created using xform',
                  project_type='survey', entity_type=self.entity_type[0],
                  activity_report='yes',
                  state=self.project_state, devices=[u'sms', u'web', u'smartPhone'],
                  language=self.language)
        project.qid = questionnaire_id

        ngo_admin = NGOUserProfile.objects.get(user=self.user)
        project.data_senders.append(ngo_admin.reporter_id)

        p = project.save(self.manager)

        return p
