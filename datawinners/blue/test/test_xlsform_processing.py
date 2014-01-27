from __builtin__ import type
import base64
import hashlib
import os
import tempfile
import unittest
from django.test import Client
from pyxform.xls2json import SurveyReader
from requests.utils import parse_dict_header
from rest_framework.test import APIClient
from xml.etree import ElementTree as ET
import time
from datawinners.blue.xfom_bridge import XfromToJson, MangroveService, XlsFormToJson
from mangrove.form_model.field import FieldSet
from mangrove.form_model.form_model import get_form_model_by_code


class TestXLSFormProcessing(unittest.TestCase):

    TEST_XLSFORMS = [
        'text_and_integer.xls', 'repeat.xls', 'many-fields.xls'
    ]

    def test_should_create_project_using_xlsform_file_path(self):

        xform_as_string, json_xform_data = XlsFormToJson(self.TEST_XLSFORMS[2], is_path_to_file=True).parse()

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


    def test_xlsform_conversion_to_xform_and_json(self):
        parser = XlsFormToJson(self.TEST_XLSFORMS[1], True)

        xform, json_xform_data = parser.parse_new()

        self.assertIsNotNone(json_xform_data)
        self.assertIsNotNone(xform)

    def test_sequence_of_the_fields_in_form_model_should_be_same_as_in_xlsform(self):

        xform_as_string, json_xform_data = XlsFormToJson(self.TEST_XLSFORMS[2], is_path_to_file=True).parse()

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
        parser = XlsFormToJson(self.TEST_XLSFORMS[1], True)

        xform, json_xform_data = parser.parse_new()

        names = [f['code'] if f['type'] != 'field_set' else self._repeat_codes(f) for f in json_xform_data]
        expected_names = ['familyname',
                          ['family',['name','age']],
                          'city',
                          ['house',['name','room','numberofrooms']]]
        self.assertEqual(names, expected_names)

    def test_should_update_xform_submission_with_reporter_id(self):
        client = Client()
        # client.login(username='tester150411@gmail.com', password='tester150411')
        # client.
        auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + base64.b64encode('tester150411@gmail.com:tester150411'),
        }
        response = client.post('/xforms/submission',
                                         {'example': 'example'})
        auth = self.build_digest_header('tester150411@gmail.com',
                                   'tester150411',
                                   response['WWW-Authenticate'],
                                   'POST',
                                   '/xforms/submission')

        with tempfile.NamedTemporaryFile(suffix='.txt') as example_file:
            example_file.write(open('repeat-submission.xml', 'r').read())
            example_file.seek(0)
            r = client.post(
                '/xforms/submission',
                {'xml_submission_file': example_file}, HTTP_AUTHORIZATION=auth
        )
        # r = client.post(
        #         '/xforms/submission',
        #          HTTP_AUTHORIZATION=auth
        # )
        self.assertEquals(r.status_code, 201)
        submission_id = r.get('submission_id', None)
        self.assertIsNotNone(submission_id)

        # todo fetch submission and verify

    def build_digest_header(self, username, password, challenge_header, method, path):
        challenge_data = parse_dict_header(challenge_header.replace('Digest ', ''))
        realm = challenge_data['realm']
        nonce = challenge_data['nonce']
        qop = challenge_data['qop']
        opaque = challenge_data['opaque']

        def md5_utf8(x):
            if isinstance(x, str):
                x = x.encode('utf-8')
            return hashlib.md5(x).hexdigest()
        hash_utf8 = md5_utf8

        KD = lambda s, d: hash_utf8("%s:%s" % (s, d))

        A1 = '%s:%s:%s' % (username, realm, password)
        A2 = '%s:%s' % (method, path)

        nonce_count = 1
        ncvalue = '%08x' % nonce_count
        s = str(nonce_count).encode('utf-8')
        s += nonce.encode('utf-8')
        s += time.ctime().encode('utf-8')
        s += os.urandom(8)

        cnonce = (hashlib.sha1(s).hexdigest()[:16])
        noncebit = "%s:%s:%s:%s:%s" % (nonce, ncvalue, cnonce, qop, hash_utf8(A2))
        respdig = KD(hash_utf8(A1), noncebit)

        base = 'username="%s", realm="%s", nonce="%s", uri="%s", '\
               'response="%s", algorithm="MD5"'
        base = base % (username, realm, nonce, path, respdig)

        if opaque:
            base += ', opaque="%s"' % opaque
        if qop:
            base += ', qop=auth, nc=%s, cnonce="%s"' % (ncvalue, cnonce)
        return 'Digest %s' % base

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