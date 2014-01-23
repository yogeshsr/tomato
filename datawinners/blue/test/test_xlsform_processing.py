from __builtin__ import type
import base64
import tempfile
import unittest
from django.test import Client
from rest_framework.test import APIClient
from xml.etree import ElementTree as ET
from datawinners.blue.xfom_bridge import XfromToJson, MangroveService, XlsFormToJson
from mangrove.form_model.field import FieldSet
from mangrove.form_model.form_model import get_form_model_by_code


class TestXLSFormProcessing(unittest.TestCase):

    TEST_XLSFORMS = [
        'text_and_integer.xls', 'repeat.xls'
    ]

    def test_should_create_project_using_xlsform_file_path(self):

        xform_as_string, json_xform_data = XlsFormToJson(self.TEST_XLSFORMS[1], is_path_to_file=True).parse()

        mangroveService = MangroveService(xform_as_string, json_xform_data)
        id, name = mangroveService.create_project()

        self.assertIsNotNone(id)
        self.assertIsNotNone(name)

    def test_project_created_using_xform_string(self):
        xform_as_string = open('xpath-sample.xml', 'r').read()
        json_xform_data = XfromToJson(xform_as_string).parse()

        # mangrove code
        id, name = MangroveService(xform_as_string, json_xform_data).create_project()

        self.assertIsNotNone(id)
        self.assertIsNotNone(name)

    def test_should_update_xform_submission_with_reporter_id(self):
        client = APIClient()
        client.credentials(username='tester150411@gmail.com', password='tester150411')
        auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + base64.b64encode('tester150411@gmail.com:tester150411'),
        }
        with tempfile.NamedTemporaryFile(suffix='.txt') as example_file:
            example_file.write(open('repeat-submission.xml', 'r').read())
            example_file.seek(0)
            r = client.post(
                '/xforms/submission',
                {'xml_submission_file': example_file}, **auth_headers
        )

        self.assertEquals(r.status_code, 201)
        submission_id = r.get('submission_id', None)
        self.assertIsNotNone(submission_id)

        # todo fetch submission and verify

    def test_xform_is_the_default_namespace(self):
        # while parsing submission we assume that xform element without namespace since being default.
        xform_as_string = open('xpath-sample.xml', 'r').read()
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
        xform_as_string = open('xpath-sample.xml', 'r').read()
        expected_form_code = '022-somthing-making-it-unique-in-xml'

        updated_xform = MangroveService(xform_as_string, None)\
            ._add_from_code(xform_as_string, '%s' % expected_form_code)

        form_code, project_name = self._parse_form_code_and_project_name(updated_xform)
        self.assertEqual(project_name, 'summary-project')
        self.assertEqual(form_code, expected_form_code)

    def test_should_verify_xform_is_stored_when_project_created(self):
        xform_as_string, json_xform_data = XlsFormToJson(self.TEST_XLSFORMS[1], is_path_to_file=True).parse()

        mangroveService = MangroveService(xform_as_string, json_xform_data)
        mangroveService.create_project()

        questionnaire_code = mangroveService.questionnaire_code
        mgr = mangroveService.manager
        from_model = get_form_model_by_code(mgr, questionnaire_code)
        self.assertIsNotNone(from_model.xform)

    def test_should_verify_repeat_field_added_to_questionnaire(self):
        xform_as_string, json_xform_data = XlsFormToJson('repeat.xls', is_path_to_file=True).parse()
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
        xform_as_string, json_xform_data = XlsFormToJson('repeat.xls', is_path_to_file=True).parse()
        self.assertIsNotNone(json_xform_data)

    def test_should_expect_exception_for_empty_or_duplicate_repeat_label(self):
        pass

    def test_form_model_has_fields_list_for_repeat_question(self):
        pass


    #integration
    def test_should_create_project_when_xlsform_is_uploaded(self):
        client = Client()
        client.login(username='tester150411@gmail.com', password='tester150411')

        r = client.post(path='/xlsform/upload/?qqfile=text_and_integer.xls', data=open('text_and_integer.xls', 'r').read(), content_type='application/octet-stream')

        self.assertEquals(r.status_code, 200)
        self.assertNotEqual(r._container[0].find('project_name'), -1)