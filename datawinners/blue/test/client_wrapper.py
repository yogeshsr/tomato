import hashlib
import os
from django.test import Client
from django.test.client import MULTIPART_CONTENT
from requests.utils import parse_dict_header
import time


class ClientWrapper(Client):

    def __init__(self, user='tester150411@gmail.com', password='tester150411'):
        Client.__init__()
        response = self.post('/xforms/submission',
                                         {'example': 'example'})
        self.auth = self.build_digest_header(user, password,
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

    def post(self, path, data={}, content_type=MULTIPART_CONTENT,
             follow=False):
        super(ClientWrapper, self).post(path, data=data, content_type, follow, self.auth)

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