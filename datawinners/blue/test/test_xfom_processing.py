import tempfile
import unittest
from django.test import Client
from rest_framework.test import APIClient
from xml.etree import ElementTree as ET
from datawinners.blue.xfom_bridge import XfromToJson, MangroveService, XlsFormToJson


class TestXFormProcessing(unittest.TestCase):

    TEST_XLSFORMS = [
        'text_and_integer.xls', 'repeat.xls'
    ]

    def test_should_create_project_using_xlsform_file_path(self):

        xform_as_string, json_xform_data = XlsFormToJson(self.TEST_XLSFORMS[1], is_path_to_file=True).parse()

        # mangrove code
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

    def test_should_create_project_when_xlsform_is_uploaded(self):
        client = Client()
        client.login(username='tester150411@gmail.com', password='tester150411')

        r = client.post(path='/xlsform/upload/?qqfile=text_and_integer.xls', data=open('text_and_integer.xls', 'r').read(), content_type='application/octet-stream')

        self.assertEquals(r.status_code, 200)
        self.assertNotEqual(r._container[0].find('project_name'), -1)

    def test_should_update_xform_submission_with_reporter_id(self):
        client = APIClient()
        client.login(username='tester150411@gmail.com', password='tester150411')

        with tempfile.NamedTemporaryFile(suffix='.txt') as example_file:
            example_file.write(open('repeat-submission.xml', 'r').read())
            example_file.seek(0)
            r = client.post(
                '/xforms/submission',
                {'xml_submission_file': example_file},
        )

        self.assertEquals(r.status_code, 201)
        submission_id = r.get('submission_id', None)
        self.assertIsNotNone(submission_id)

        # todo fetch submission and verify

    def test_should_test_xfrom_is_the_default_namespace(self):
        # otherwise the submission from enkito can't be parsed,
        # since it will contain the namespace for the root (project_name) element
        pass

    def test_should_add_form_code_and_bind_element_to_xform(self):
        xform_as_string = open('xpath-sample.xml', 'r').read()
        expected_form_code = '022-somthing-making-it-unique-in-xml'

        updated_xform = MangroveService(xform_as_string, None)._add_from_code(xform_as_string, '%s' % expected_form_code)

        root = ET.fromstring(updated_xform)
        xform_ns = '{http://www.w3.org/2002/xforms}'
        html_ns = '{http://www.w3.org/1999/xhtml}'
        title_path = html_ns.join(['', 'head/', 'title'])
        project_name = root.findall(title_path)[0].text
        head_path = '%shead' % html_ns
        form_code_path = head_path + '/' + xform_ns.join(['', 'model/', 'instance/', 'summary-project/', 'form_code'])
        form_code = root.findall(form_code_path)[0].text

        self.assertEqual(project_name, 'summary-project')
        self.assertEqual(form_code, expected_form_code)

    def test_should_verify_xform_is_stored_when_project_created(self):
        pass

    def test_should_verify_repeat_field_added_to_questionnaire(self):
        xform_as_string, json_xform_data = XlsFormToJson('repeat.xls', is_path_to_file=True).parse()
        id, name = MangroveService(xform_as_string, json_xform_data).create_project()
        self.assertIsNotNone(id)
        self.assertIsNotNone(name)

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

    def test_should_download_xform_with_repeat_field(self):
        client = Client()
        client.login(username='tester150411@gmail.com', password='tester150411')

        r = client.get(path='/xforms/0528ba5a835a11e3bbaa001c42af7554')
        self.assertEquals(r.status_code, 200)

    def test_should_save_xform_submission(self):
        client = APIClient()
        client.login(username='tester150411@gmail.com', password='tester150411')
        # file={'xml_submission_file':open('repeat-submission.xml', 'r').read()}
        # r = client.post(path='/xforms/submission', file, content_type='multipart')


        with tempfile.NamedTemporaryFile(suffix='.txt') as example_file:
            example_file.write(open('repeat-submission.xml', 'r').read())
            example_file.seek(0)
            r = client.post(
                '/xforms/submission',
                {'xml_submission_file': example_file},
        )

        self.assertEquals(r.status_code, 201)
        self.assertIsNotNone(r.get('location', None))
