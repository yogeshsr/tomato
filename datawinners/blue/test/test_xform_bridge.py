from __builtin__ import type
import os
import unittest
from xml.etree import ElementTree as ET

from django.test import Client
from mock import Mock

from datawinners.blue.xform_bridge import MangroveService, XlsFormParser, XFormSubmissionProcessor
from mangrove.datastore.database import DatabaseManager
from mangrove.datastore.datadict import DataDictType
from mangrove.form_model.field import FieldSet, TextField
from mangrove.form_model.form_model import get_form_model_by_code

DIR = os.path.dirname(__file__)

class TestXFormBridge(unittest.TestCase):

    def setUp(self):
        self.test_data = os.path.join(DIR, 'testdata')
        self.ALL_FIELDS = os.path.join(self.test_data,'all_fields.xls')
        self.SIMPLE = os.path.join(self.test_data,'text_and_integer.xls')
        self.REPEAT = os.path.join(self.test_data,'repeat.xls')
        self.SKIP = os.path.join(self.test_data,'skip-sample.xls')
        self.MULTI_SELECT = os.path.join(self.test_data,'multi-select.xls')
        self.MANY_FIELD = os.path.join(self.test_data,'many-fields.xls')
        self.NAME_SPACE = os.path.join(self.test_data,'xpath-sample.xml')

    def test_should_create_project_using_xlsform_file(self):

        xform, json_xform_data = XlsFormParser(self.ALL_FIELDS).parse()

        mangroveService = MangroveService(xform, json_xform_data)
        id, name = mangroveService.create_project()

        self.assertIsNotNone(id)
        self.assertIsNotNone(name)

    def test_should_convert_skip_logic_question(self):
        xform_as_string, json_xform_data = XlsFormParser(self.SKIP, is_path_to_file=True).parse()
        mangroveService = MangroveService(xform_as_string, json_xform_data)
        id, name = mangroveService.create_project()

        self.assertIsNotNone(id)
        self.assertIsNotNone(name)

    def test_should_convert_multi_select_question(self):
        xform_as_string, json_xform_data = XlsFormParser(self.MULTI_SELECT, is_path_to_file=True).parse()
        mangroveService = MangroveService(xform_as_string, json_xform_data)
        id, name = mangroveService.create_project()

        self.assertIsNotNone(id)
        self.assertIsNotNone(name)

    def test_all_fields_types_in_xlsform_is_converted_to_json(self):
        xform, json_xform_data = XlsFormParser(self.ALL_FIELDS).parse()

        expected_json = \
            [{'code': 'name', 'name': 'What is your name?', 'title': 'What is your name?', 'required': True, 'is_entity_question': False, 'instruction': 'Answer must be a word', 'type': 'text'},
             {'code': 'education', 'instruction': 'No answer required', 'name': 'Education', 'title': 'Education',
                'fields': [{'code': 'degree', 'name': 'Degree name', 'title': 'Degree name', 'required': True, 'is_entity_question': False, 'instruction': 'Answer must be a word', 'type': 'text'},
                         {'code': 'completed_on', 'date_format': 'dd.mm.yyyy', 'name': 'Degree completion year', 'title': 'Degree completion year', 'required': True, 'is_entity_question': False, 'instruction': 'Answer must be a date in the following format: day.month.year. Example: 25.12.2011','event_time_field_flag': False, 'type': 'date'}], 'is_entity_question': False,
              'type': 'field_set', 'required': False},
             {'code': 'age', 'name': 'What is your age?', 'title': 'What is your age?', 'required': True, 'is_entity_question': False, 'instruction': 'Answer must be a number', 'type': 'integer'},
             {'code': 'fav_color', 'title': 'Which colors you like?', 'required': True,
                'choices': [{'text': 'Red', 'val': 'r'}, {'text': 'Blue', 'val': 'b'},
                          {'text': 'Green', 'val': 'g'}], 'is_entity_question': False, 'type': 'select'},
             {'code': 'pizza_fan', 'title': 'Do you like pizza?', 'required': True,
                'choices': [{'text': 'Yes', 'val': 'y'}, {'text': 'No', 'val': 'n'}], 'is_entity_question': False, 'type': 'select1'},
             {'code': 'other', 'name': 'What else you like?', 'title': 'What else you like?', 'required': True, 'is_entity_question': False, 'instruction': 'Answer must be a word', 'type': 'text'},
             {'code': 'pizza_type', 'name': 'Which pizza type you like?', 'title': 'Which pizza type you like?', 'required': True, 'is_entity_question': False, 'instruction': 'Answer must be a word', 'type': 'text'}]

        #expected_xml = '<?xml version="1.0"?> <h:html xmlns="http://www.w3.org/2002/xforms" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:h="http://www.w3.org/1999/xhtml" xmlns:jr="http://openrosa.org/javarosa" xmlns:orx="http://openrosa.org/xforms/" xmlns:xsd="http://www.w3.org/2001/XMLSchema"> <h:head> <h:title>Project</h:title> <model> <instance> <Project id="Project"> <name/> <education jr:template=""> <degree/> <completed_on/> </education> <age/> <fav_color/> <pizza_fan/> <other/> <pizza_type/> <meta> <instanceID/> </meta> </Project> </instance> <bind nodeset="/Project/name" type="string"/> <bind nodeset="/Project/education/degree" type="string"/> <bind nodeset="/Project/education/completed_on" type="date"/> <bind nodeset="/Project/age" type="int"/> <bind nodeset="/Project/fav_color" type="select"/> <bind nodeset="/Project/pizza_fan" type="select1"/> <bind nodeset="/Project/other" relevant=" /Project/pizza_fan  = 'n'" type="string"/> <bind nodeset="/Project/pizza_type" relevant=" /Project/pizza_fan  = 'y'" type="string"/> <bind calculate="concat('uuid:', uuid())" nodeset="/Project/meta/instanceID" readonly="true()" type="string"/> </model> </h:head> <h:body> <input ref="/Project/name"> <label>What is your name?</label> </input> <group ref="/Project/education"> <label>Education</label> <repeat nodeset="/Project/education"> <input ref="/Project/education/degree"> <label>Degree name</label> </input> <input ref="/Project/education/completed_on"> <label>Degree completion year</label> </input> </repeat> </group> <input ref="/Project/age"> <label>What is your age?</label> </input> <select ref="/Project/fav_color"> <label>Which colors you like?</label> <item> <label>Red</label> <value>r</value> </item> <item> <label>Blue</label> <value>b</value> </item> <item> <label>Green</label> <value>g</value> </item> </select> <select1 ref="/Project/pizza_fan"> <label>Do you like pizza?</label> <item> <label>Yes</label> <value>y</value> </item> <item> <label>No</label> <value>n</value> </item> </select1> <input ref="/Project/other"> <label>What else you like?</label> </input> <input ref="/Project/pizza_type"> <label>Which pizza type you like?</label> </input> </h:body> </h:html>'

        self.assertEqual(expected_json, json_xform_data)
        self.assertIsNotNone(xform)

    def test_sequence_of_the_fields_in_form_model_should_be_same_as_in_xlsform(self):

        xform_as_string, json_xform_data = XlsFormParser(self.MANY_FIELD).parse()

        self.assertIsNotNone(xform_as_string)
        names = [f['code'] for f in json_xform_data]
        expected_names = ["a312name1312","a528name2528","a972name3972","a667name4667","a868name5868","a970name6970","a870name7870","a320name8320","a863name9863","a509name10509","a191name11191","a216name12216","a320name13320","a165name14165","a116name15116","a413name16413","a568name17568","a379name18379","a863name19863","a929name20929","a640name21640","a392name22392","a264name23264","a868name24868","a191name25191","a316name26316","a908name27908","a488name28488","a455name29455","a802name30802","a595name31595","a668name32668","a329name33329","a566name34566","a335name35335","a197name36197","a536name37536","a204name38204","a418name39418","a399name40399","a614name41614","a510name42510","a515name43515","a835name44835","a575name45575","a531name46531","a247name47247","a143name48143","a811name49811","a110name50110"]
        self.assertEqual(names, expected_names)

    def _repeat_codes(self, repeat):
        code = repeat['code']
        children_code = [f['code'] for f in repeat['fields']]
        r = []
        r.append(code)
        r.append(children_code)
        return r

    def test_sequence_of_the_mixed_type_fields_in_from_model_should_be_same_as_xlsform(self):
        parser = XlsFormParser(self.REPEAT)

        xform, json_xform_data = parser.parse()

        names = [f['code'] if f['type'] != 'field_set' else self._repeat_codes(f) for f in json_xform_data]
        expected_names = ['familyname',
                          ['family',['name','age']],
                          'city',
                          ['house',['name','room','numberofrooms']]]
        self.assertEqual(names, expected_names)

    def test_xform_is_the_default_namespace(self):
        # while parsing submission we assume that xform element without namespace since being default.
        xform_as_string = open(self.NAME_SPACE, 'r').read()
        default_namespace_definition_format = 'xmlns="http://www.w3.org/2002/xforms"'

        updated_xform = MangroveService(xform_as_string, None)._add_from_code(xform_as_string, None)

        self.assertTrue(updated_xform.find(default_namespace_definition_format) != -1)

    def _parse_form_code_and_project_name(self, updated_xform):
        ET.register_namespace('', 'http://www.w3.org/2002/xforms')
        root = ET.fromstring(updated_xform)
        xform_ns = '{http://www.w3.org/2002/xforms}'
        html_ns = '{http://www.w3.org/1999/xhtml}'
        title_path = html_ns.join(['', 'head/', 'title'])
        project_name = root.findall(title_path)[0].text
        head_path = '%shead' % html_ns
        form_code_path = head_path + '/' + xform_ns.join(['', 'model/', 'instance/', 'summary-project/', 'form_code'])
        form_code = root.findall(form_code_path)[0].text
        return form_code, project_name

    def test_should_add_form_code_and_bind_element_to_xform(self):
        # todo instead of reading xform file use hard coded string
        xform_as_string = open(self.xform_with_default_namespace, 'r').read()
        expected_form_code = '022-somthing-making-it-unique-in-xml'

        updated_xform = MangroveService(xform_as_string, None)\
            ._add_from_code(xform_as_string, '%s' % expected_form_code)

        form_code, project_name = self._parse_form_code_and_project_name(updated_xform)
        self.assertEqual(project_name, 'summary-project')
        self.assertEqual(form_code, expected_form_code)

    def test_should_verify_xform_is_stored_when_project_created(self):
        xform_as_string, json_xform_data = XlsFormParser(self.REPEAT).parse()

        mangroveService = MangroveService(xform_as_string, json_xform_data)
        mangroveService.create_project()

        questionnaire_code = mangroveService.questionnaire_code
        mgr = mangroveService.manager
        from_model = get_form_model_by_code(mgr, questionnaire_code)
        self.assertIsNotNone(from_model.xform)

    def test_should_verify_repeat_field_added_to_questionnaire(self):
        xform_as_string, json_xform_data = XlsFormParser(self.REPEAT).parse()
        mangroveService = MangroveService(xform_as_string, json_xform_data)
        mangroveService.create_project()

        questionnaire_code = mangroveService.questionnaire_code
        mgr = mangroveService.manager
        from_model = get_form_model_by_code(mgr, questionnaire_code)

        self.assertNotEqual([], [f for f in from_model.fields if type(f) is FieldSet and f.fields])

    def test_should_convert_simple_single_question(self):
        pass

    def test_should_convert_multiple_simple_questions(self):
        pass

    def test_should_convert_single_simple_and_single_repeat_question(self):
        pass

    def test_should_convert_multiple_simple_and_multiple_repeat_question(self):
        pass

    def test_should_expect_exception_for_empty_or_duplicate_repeat_label(self):
        pass

    def test_form_model_has_fields_list_for_repeat_question(self):
        pass

    #integration
    def test_should_create_project_when_xlsform_is_uploaded(self):
        client = Client()
        client.login(username='tester150411@gmail.com', password='tester150411')

        r = client.post(path='/xlsform/upload/?qqfile=text_and_integer.xls',
                        data=open(os.path.join(self.test_data, 'text_and_integer.xls'), 'r').read(),
                                  content_type='application/octet-stream')

        self.assertEquals(r.status_code, 200)
        self.assertNotEqual(r._container[0].find('project_name'), -1)

    def create_test_fields_and_survey(self):
        default_ddtype = DataDictType(Mock(spec=DatabaseManager), name='default dd type', slug='string_default',
                                      primitive_type='string')
        #change this to reporter
        #entity_field = TextField('clinic', 'ID', 'clinic label', default_ddtype, entity_question_flag=True)
        city_field = TextField('city', 'city', 'What is the City name?', default_ddtype)
        name_field = TextField('centername', 'centername', 'Center Name?', default_ddtype)
        area_field = TextField('area', 'area', 'Area?', default_ddtype)
        center_field_set = FieldSet('center', 'center', 'Center Information', default_ddtype, field_set=[name_field, area_field])
        form_fields = [#entity_field,
                       city_field, center_field_set]
        survey_response_values = {'city': 'Bhopal',
                                  'center': [{'centername': 'Boot', 'area': 'New Market'},
                                             {'centername': 'Weene', 'area': 'Bgh'}], 'eid': 'rep276'}
        return form_fields, survey_response_values

    def test_should_create_xform_instance_for_submission(self):
        form_fields, survey_response_values = self.create_test_fields_and_survey()
        submissionProcessor = XFormSubmissionProcessor()
        expected_xml = '<instance xmlns="http://www.w3.org/2002/xforms"><city>Bhopal</city><center><centername>Boot</centername><area>New Market</area></center><center><centername>Weene</centername><area>Bgh</area></center></instance>'

        instance_node_xml = submissionProcessor.create_xform_instance_of_submission(form_fields, survey_response_values)

        self.assertEqual(expected_xml, instance_node_xml)

    def test_should_update_xform_instance_with_submission_data(self):
        xform_024 = open('testdata/xform-024.xml', 'r').read()
        form_fields, survey_response_values = self.create_test_fields_and_survey()
        submissionProcessor = XFormSubmissionProcessor()
        xform_instance_xml = submissionProcessor.create_xform_instance_of_submission(form_fields, survey_response_values)

        xform_with_submission = submissionProcessor.update_instance_children(xform_024, xform_instance_xml)

        #todo asset submission in xml
        print xform_with_submission


    # def test_a(self):
    #     f = open('testdata/contacts.csv','r').read(1024)
    #     print f