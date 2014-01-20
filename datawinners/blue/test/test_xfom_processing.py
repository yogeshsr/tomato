import unittest
from django.test import Client
from datawinners.blue.xfom_bridge import XfromToJson, MangroveService, XlsFormToJson


class TestXFormProcessing(unittest.TestCase):

    def test_should_create_project_using_xlsform_file_path(self):

        xform_as_string, json_xform_data = XlsFormToJson('text_and_integer.xls', is_path_to_file=True).parse()

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
