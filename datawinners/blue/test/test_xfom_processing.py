import tempfile
import unittest
from django.test import Client
from rest_framework.test import APIClient
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

        xform_test_string = open('xpath-sample.xml', 'r').read()

        json_xform_data = XfromToJson(xform_test_string).parse()

        # mangrove code
        id, name = MangroveService(xform_test_string, json_xform_data).create_project()
        self.assertIsNotNone(id)
        self.assertIsNotNone(name)

    def test_should_create_project_when_xlsform_is_uploaded(self):
        client = Client()
        client.login(username='tester150411@gmail.com', password='tester150411')

        r = client.post(path='/xlsform/upload/?qqfile=text_and_integer.xls', data=open('text_and_integer.xls', 'r').read(), content_type='application/octet-stream')

        self.assertEquals(r.status_code, 200)
        self.assertNotEqual(r._container[0].find('project_name'), -1)

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
        # credentials = base64.b64encode('tester150411@gmail.com:tester150411')
        # client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials

        r = client.get(path='/xforms/0a31db56833e11e3b3fd001c42af7554')
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
