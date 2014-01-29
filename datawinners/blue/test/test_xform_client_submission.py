import os
import tempfile
import unittest
from django_digest.test import Client as DigestClient

DIR = os.path.dirname(__file__)

class TestXFromClientSubmission(unittest.TestCase):

    def setUp(self):
        self.client = DigestClient()
        self.client.set_authorization('tester150411@gmail.com','tester150411', 'Digest')
        self.test_data = os.path.join(DIR, 'testdata')

    #todo Test data is hardcoded currently. Need to fix this ex by creating required project.

    #integration
    def test_should_download_xform_with_repeat_field(self):
        project_id = '0528ba5a835a11e3bbaa001c42af7554'
        r = self.client.get(path='/xforms/%s' %project_id)
        self.assertEquals(r.status_code, 200)

    #integration
    def test_should_update_xform_submission_with_reporter_id(self):
        submission_xml = os.path.join(self.test_data, 'repeat-submission.xml')

        r = self._do_submission(submission_xml)

        self.assertEquals(r.status_code, 201)
        submission_id = r.get('submission_id', None)
        self.assertIsNotNone(submission_id)
        #todo verify the rep_id is present in submission doc

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
    def test_should_update_xform_submission_with_reporter_id(self):
        submission_xml = os.path.join(self.test_data, 'repeat-submission.xml')

        r = self._do_submission(submission_xml)

        self.assertEquals(r.status_code, 201)
        submission_id = r.get('submission_id', None)
        self.assertIsNotNone(submission_id)

        # todo fetch submission doc and verify; append something unique to submission to make it specific