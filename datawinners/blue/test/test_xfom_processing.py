import unittest
from pyxform import create_survey_from_path
from pyxform.xform2json import XFormToDict
from datawinners.blue.xfom_bridge import XfromToJson, MangroveService


class TestXFormProcessing(unittest.TestCase):

    def setUp(self):
        self.always_increment_before_each_test_run = 21

    def test_some(self):
        xform_dict = XFormToDict(open('repeat.xml', 'r').read()).get_dict()
        print xform_dict

    def test_should_create_project_using_xlsform(self):
        xls_form_name = 'text_and_integer.xls'
        survey = create_survey_from_path(xls_form_name)
        xform_as_string = survey.to_xml()

        json_xform_data = XfromToJson(xform_as_string).parse()

        # mangrove code
        mangroveService = MangroveService(xform_as_string, self.always_increment_before_each_test_run)
        questionnaire_id = mangroveService.create_questionnaire(json_xform_data)
        p = mangroveService.create_project(questionnaire_id)

        self.assertIsNotNone(p)

    def test_project_created_using_xform(self):

        xform_as_string = open('xpath-sample.xml', 'r').read()

        json_xform_data = XfromToJson(xform_as_string).parse()

        # mangrove code
        mangroveService = MangroveService(xform_as_string, self.always_increment_before_each_test_run)
        questionnaire_id = mangroveService.create_questionnaire(json_xform_data)
        p = mangroveService.create_project(questionnaire_id)

        self.assertIsNotNone(p)