import os
import tempfile
import unittest
from django_digest.test import Client as DigestClient
from datawinners.blue.xform_bridge import XFormSubmissionProcessor
from mangrove.form_model.field import TextField, FieldSet, DateField, IntegerField, SelectField, GeoCodeField
from xml.etree import ElementTree as ET

DIR = os.path.dirname(__file__)

class TestXFromClientSubmission(unittest.TestCase):

    def setUp(self):
        self.client = DigestClient()
        self.client.set_authorization('tester150411@gmail.com','tester150411', 'Digest')
        self.test_data = os.path.join(DIR, 'testdata')
        self.XFORM_XML = os.path.join(self.test_data,'xform-024.xml')
        self.XFORM_XML_ALL_FIELDS = os.path.join(self.test_data,'xform_all_fields.xml')

    #todo Test data is hardcoded currently. Need to fix this ex by creating required project.

    #integration
    # def test_should_download_xform_with_repeat_field(self):
    #     project_id = '0528ba5a835a11e3bbaa001c42af7554'
    #     r = self.client.get(path='/xforms/%s' %project_id)
    #     self.assertEquals(r.status_code, 200)

    #integration
    # def test_should_update_xform_submission_with_reporter_id(self):
    #     # todo same as test_should_update_xform_submission_with_reporter_id
    #     submission_xml = os.path.join(self.test_data, 'repeat-submission.xml')
    #
    #     r = self._do_submission(submission_xml)
    #
    #     self.assertEquals(r.status_code, 201)
    #     submission_id = r.get('submission_id', None)
    #     self.assertIsNotNone(submission_id)
    #     #todo verify the rep_id is present in submission doc

    def _do_submission(self, submission_xml):
        with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
            temp_file.write(open(submission_xml, 'r').read())
            temp_file.seek(0)
            r = self.client.post(
                '/xforms/submission',
                {'xml_submission_file': temp_file},
        )
        return r

    #integration
    # def test_should_update_xform_submission_with_reporter_id(self):
    #     # todo Project needs to be created and the eid and form_code need to be updated the in the repeat-submission.xml
    #     submission_xml = os.path.join(self.test_data, 'repeat-submission.xml')
    #
    #     r = self._do_submission(submission_xml)
    #
    #     self.assertEquals(r.status_code, 201)
    #     submission_id = r.get('submission_id', None)
    #     self.assertIsNotNone(submission_id)

        # todo fetch submission doc and verify; append something unique to submission to make it specific

    def test_should_update_xform_instance_with_submission_data(self):
        xform_024 = open(self.XFORM_XML, 'r').read()
        form_fields, survey_response_values = self.create_test_fields_and_survey()
        submissionProcessor = XFormSubmissionProcessor()
        xform_instance_xml = submissionProcessor.get_model_edit_str(form_fields, survey_response_values)

        xform_with_submission = submissionProcessor.update_instance_children(xform_024, xform_instance_xml)

        #todo asset submission in xml
        print xform_with_submission

    def create_code_value(self, node):
        if node.getchildren():
            return {node.tag.split('}')[1]: [self.create_code_value(c) for c in node.getchildren()]}
        else:
            return {node.tag.split('}')[1]: node.text if node.text else ''}

    def get_submission_from_xform(self, xform_with_submission):
        ET.register_namespace('', 'http://www.w3.org/2002/xforms')
        root = ET.fromstring(xform_with_submission)
        #todo remove the project name hardcoding; instead find the project name from xform title.
        children = [e for e in root.getiterator() if e.tag == '{http://www.w3.org/2002/xforms}Project'][0].getchildren()
        code_value_dict = [self.create_code_value(child) for child in children]
        return code_value_dict

    def test_should_update_xform_instance_with_submission_data_for_all_field_types(self):
        xform = open(self.XFORM_XML_ALL_FIELDS, 'r').read()
        form_fields, survey_response_values = self.create_test_fields_and_survey_for_all_fields_type()
        submissionProcessor = XFormSubmissionProcessor()
        xform_instance_xml = submissionProcessor.get_model_edit_str(form_fields, survey_response_values)

        xform_with_submission = submissionProcessor.update_instance_children(xform, xform_instance_xml)

        code_value_dict = self.get_submission_from_xform(xform_with_submission)
        expected_code_val_dict = [{'meta': [{'instanceID': ''}]}, {'form_code': '023'},
                                  {'other': 'Samosa'},
                                  {'name': 'Santa'}, {'location': '4.9158 11.9531'}, {'pizza_type': ''},
                                  {'age': '30'},
                                  {'education': [{'completed_on': '2014-02-10'}, {'degree': 'SantaSSC'}]},
                                  {'fav_color': 'red blue'}, {'pizza_fan': 'yes'}]

        self.assertEqual(expected_code_val_dict, code_value_dict)

    def create_test_fields_and_survey_for_all_fields_type(self):
        name = TextField('name', 'name' ,'What is your name?')
        degree = TextField('degree', 'degree' ,'Degree name')
        completed_on = DateField('completed_on', 'completed_on','Degree completion year', 'dd.mm.yyyy')
        education = FieldSet('education', 'education', 'Education', field_set=[degree,completed_on])
        age = IntegerField('age', 'age' ,'What is your age?')
        opt_fav_col = [('red','Red'), ('blue','Blue'),('c','Green')]
        fav_col = SelectField('fav_color', 'fav_color', 'Which colors you like?', opt_fav_col)
        opt_pizza_col = [('yes', 'Yes'),('no','No')]
        pizza_fan = SelectField('pizza_fan', 'pizza_fan', 'Do you like pizza?', opt_pizza_col)
        other = TextField('other', 'other' ,'What else you like?')
        pizza_type = TextField('pizza_type', 'pizza_type' ,'Which pizza type you like?')
        location = GeoCodeField('location', 'location' ,'Your location?')

        form_fields = [name, education, age, fav_col, pizza_fan, other, pizza_type, location]

        # todo how required will be handled
        survey_response_values = {'name': 'Santa', 'pizza_type': None, 'age': '30', 'other': 'Samosa', 'location': '4.9158,11.9531', 'education': [{'completed_on': u'10.02.2014', 'degree': 'SantaSSC'}], 'pizza_fan': 'yes', 'fav_color': 'red blue'}
        return form_fields, survey_response_values


    def create_test_fields_and_survey(self):
        #change this to reporter
        #entity_field = TextField('clinic', 'ID', 'clinic label', entity_question_flag=True)
        city_field = TextField('city', 'city', 'What is the City name?')
        name_field = TextField('centername', 'centername', 'Center Name?')
        area_field = TextField('area', 'area', 'Area?')
        center_field_set = FieldSet('center', 'center', 'Center Information', field_set=[name_field, area_field])
        form_fields = [#entity_field,
                       city_field, center_field_set]
        survey_response_values = {'city': 'Bhopal',
                                  'center': [{'centername': 'Boot', 'area': 'New Market'},
                                             {'centername': 'Weene', 'area': 'Bgh'}], 'eid': 'rep276'}
        return form_fields, survey_response_values

    def test_should_create_xform_model_str(self):
        form_fields, survey_response_values = self.create_test_fields_and_survey()
        submissionProcessor = XFormSubmissionProcessor()
        expected_xml = '<project-name-01><city>Bhopal</city><center><centername>Boot</centername><area>New Market</area></center><center><centername>Weene</centername><area>Bgh</area></center></project-name-01>'

        instance_node_xml = submissionProcessor.get_model_edit_str(form_fields, survey_response_values, 'project-name-01')

        self.assertEqual(expected_xml, instance_node_xml)