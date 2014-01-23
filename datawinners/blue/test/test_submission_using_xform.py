import tempfile
import unittest
from django.test import Client
from rest_framework.test import APIClient


class TestSubmissionUsingXFrom(unittest.TestCase):
    #integration
    def test_should_download_xform_with_repeat_field(self):
        client = Client()
        client.login(username='tester150411@gmail.com', password='tester150411')

        r = client.get(path='/xforms/0528ba5a835a11e3bbaa001c42af7554')
        self.assertEquals(r.status_code, 200)

    #integration
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
