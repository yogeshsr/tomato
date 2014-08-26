# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils import unittest
from registration.models import RegistrationProfile
from datawinners.accountmanagement.models import Organization, NGOUserProfile, PaymentDetails
from datawinners.accountmanagement.organization_id_creator import OrganizationIdCreator
from datawinners.accountmanagement.registration_backend import RegistrationBackend
from datawinners.accountmanagement.registration_processors import \
    ProSMSAccountRegistrationProcessor, PaidAccountRegistrationProcessor, TrialAccountRegistrationProcessor
from django.contrib.sites.models import Site
from django.conf import settings
from datawinners.tests.email_utils import set_email_settings
from mangrove.utils.types import is_not_empty
from django.core import mail
from mock import patch
from datawinners.accountmanagement.utils import PRO_SMS_MONTHLY_PRICING

class TestRegistrationProcessor(unittest.TestCase):
    def prepare_organization(self):
        self.paid_organization = Organization(name='test_org_for_paid_account',
                                              sector='PublicHealth', address='add',
                                              city='Pune', country='India',
                                              zipcode='411006', account_type='Pro SMS',
                                              org_id=OrganizationIdCreator().generateId())
        
        self.trial_organization = Organization(name='test_org_for_trial_account',
                                                            sector='PublicHealth', address='add',
                                                            city='Pune', country='India',
                                                            zipcode='411006', account_type='Basic',
                                                            org_id=OrganizationIdCreator().generateId())
        self.paid_organization.save()
        self.trial_organization.save()

    def setUp(self):
        set_email_settings()
        User.objects.filter(username = 'paid_account@mail.com').delete()
        User.objects.filter(username = 'trial_account@mail.com').delete()
        Organization.objects.filter(name='test_org_for_paid_account').delete()
        Organization.objects.filter(name='test_org_for_trial_account').delete()

        self.user1 = RegistrationProfile.objects.create_inactive_user(username='paid_account@mail.com', email='paid_account@mail.com', password='hi', site=Site(), send_email=False)
        self.user2 = RegistrationProfile.objects.create_inactive_user(username='trial_account@mail.com', email='trial_account@mail.com', password='hi', site=Site(), send_email=False)

        self.user1.first_name = 'first_name1 last_name1'

        self.user2.first_name = 'first_name2 last_name2'

        self.user1.save()
        self.user2.save()

        self.prepare_organization()

        NGOUserProfile(user = self.user1,title = 'Mr.',org_id = self.paid_organization.org_id).save()
        NGOUserProfile(user = self.user2,title = 'Ms.',org_id = self.trial_organization.org_id).save()
        self.processor = RegistrationBackend()


    def tearDown(self):
        self.user1.delete()
        self.user2.delete()
        self.paid_organization.delete()
        self.trial_organization.delete()


    def test_should_get_the_correct_registration_processor(self):

        self.assertTrue(isinstance(self.processor.get_registration_processor(self.trial_organization), TrialAccountRegistrationProcessor))

        self.assertTrue(isinstance(self.processor.get_registration_processor(self.paid_organization), PaidAccountRegistrationProcessor))

    def test_should_process_registration_data_for_paid_acccount_in_english(self):
        with patch.object(ProSMSAccountRegistrationProcessor, '_get_invoice_total') as get_invoice_total_patch:
            get_invoice_total_patch.return_value = PRO_SMS_MONTHLY_PRICING, '1 month'
            processor = self.processor.get_registration_processor(self.paid_organization)


            site = Site(domain='test', name='test_site')
            kwargs = dict(invoice_period='', preferred_payment='')

            processor.process(self.user1, site, 'en', kwargs)

            emails = [mail.outbox.pop() for i in range(len(mail.outbox))]

            self.assertEqual(1, len(emails))
            sent_email = emails[0]

            self.assertEqual("html", sent_email.content_subtype)
            self.assertEqual(settings.EMAIL_HOST_USER, sent_email.from_email)
            self.assertEqual(['paid_account@mail.com'], sent_email.to)
            self.assertEqual([settings.HNI_SUPPORT_EMAIL_ID], sent_email.bcc)

            self.assertEqual(render_to_string('registration/activation_email_subject_in_en.txt'), sent_email.subject)
            ctx_dict = {'activation_key': RegistrationProfile.objects.get(user=self.user1).activation_key,
                        'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                        'site': site,
                        'username': self.user1.first_name,
                        'invoice_total': PRO_SMS_MONTHLY_PRICING,
                        'period': '1 month'
                        }
            self.assertEqual(render_to_string('registration/pro_sms_activation_email_in_en.html', ctx_dict), sent_email.body)

            payment_detail = PaymentDetails.objects.filter(organization=self.paid_organization)
            self.assertTrue(is_not_empty(payment_detail))
            payment_detail.delete()

    def test_should_process_registration_data_for_trial_acccount_in_english(self):
        processor = self.processor.get_registration_processor(self.trial_organization)

        site = Site(domain='test', name='test_site')
        kwargs = dict(invoice_period='', preferred_payment='')

        processor.process(self.user2, site, 'en', kwargs)

        emails = [mail.outbox.pop() for i in range(len(mail.outbox))]

        self.assertEqual(1, len(emails))
        sent_email = emails[0]

        self.assertEqual("html", sent_email.content_subtype)
        self.assertEqual(settings.EMAIL_HOST_USER, sent_email.from_email)
        self.assertEqual(['trial_account@mail.com'], sent_email.to)
        self.assertEqual([settings.HNI_SUPPORT_EMAIL_ID], sent_email.bcc)

        ctx_dict = {'activation_key': RegistrationProfile.objects.get(user=self.user2).activation_key,
                    'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                    'site': site,
                    'username': self.user2.first_name}
        self.assertEqual(render_to_string('registration/activation_email_subject_for_trial_account_in_en.txt'), sent_email.subject)
        self.assertEqual(render_to_string('registration/activation_email_for_trial_account_in_en.html', ctx_dict), sent_email.body)

    def test_should_process_registration_data_for_paid_acccount_in_french(self):
        with patch.object(ProSMSAccountRegistrationProcessor, '_get_invoice_total') as get_invoice_total_patch:
            get_invoice_total_patch.return_value = PRO_SMS_MONTHLY_PRICING, '1 month'
            processor = self.processor.get_registration_processor(self.paid_organization)

            site = Site(domain='test', name='test_site')
            kwargs = dict(invoice_period='', preferred_payment='')

            processor.process(self.user1, site, 'fr', kwargs)

            emails = [mail.outbox.pop() for i in range(len(mail.outbox))]

            self.assertEqual(1, len(emails))
            sent_email = emails[0]

            self.assertEqual("html", sent_email.content_subtype)
            self.assertEqual(settings.EMAIL_HOST_USER, sent_email.from_email)
            self.assertEqual(['paid_account@mail.com'], sent_email.to)
            self.assertEqual([settings.HNI_SUPPORT_EMAIL_ID], sent_email.bcc)

            self.assertEqual(render_to_string('registration/activation_email_subject_in_fr.txt'), sent_email.subject)
            ctx_dict = {'activation_key': RegistrationProfile.objects.get(user=self.user1).activation_key,
                        'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                        'site': site,
                        'username': self.user1.first_name,
                        'invoice_total': PRO_SMS_MONTHLY_PRICING,
                        'period': '1 month'}
            self.assertEqual(render_to_string('registration/pro_sms_activation_email_in_fr.html', ctx_dict), sent_email.body)

            payment_detail = PaymentDetails.objects.filter(organization=self.paid_organization)
            self.assertTrue(is_not_empty(payment_detail))
            payment_detail.delete()

    def test_should_process_registration_data_for_trial_acccount_in_french(self):
        processor = self.processor.get_registration_processor(self.trial_organization)

        site = Site(domain='test', name='test_site')
        kwargs = dict(invoice_period='', preferred_payment='')

        processor.process(self.user2, site, 'fr', kwargs)

        emails = [mail.outbox.pop() for i in range(len(mail.outbox))]

        self.assertEqual(1, len(emails))
        sent_email = emails[0]

        self.assertEqual("html", sent_email.content_subtype)
        self.assertEqual(settings.EMAIL_HOST_USER, sent_email.from_email)
        self.assertEqual(['trial_account@mail.com'], sent_email.to)
        self.assertEqual([settings.HNI_SUPPORT_EMAIL_ID], sent_email.bcc)

        ctx_dict = {'activation_key': RegistrationProfile.objects.get(user=self.user2).activation_key,
                    'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                    'site': site,
                    'username': self.user2.first_name}
        self.assertEqual(render_to_string('registration/activation_email_subject_for_trial_account_in_fr.txt'), sent_email.subject)
        self.assertEqual(render_to_string('registration/activation_email_for_trial_account_in_fr.html', ctx_dict), sent_email.body)
