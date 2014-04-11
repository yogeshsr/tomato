# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import json

import unittest

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from mock import Mock, patch, call, MagicMock
from mangrove.transport import Response

from mangrove.datastore.database import DatabaseManager
from mangrove.form_model.field import TextField, DateField
from datawinners.entity.forms import ReporterRegistrationForm
from datawinners.project.models import Reminder, RemindTo, ReminderMode, Project
from datawinners.project.views.views import _format_reminders, SubjectWebQuestionnaireRequest
from datawinners.project.preview_views import get_sms_preview_context, get_questions, get_web_preview_context_from_project_data
from datawinners.project.utils import make_subject_links
from datawinners.project.views.views import get_preview_and_instruction_links_for_questionnaire, append_success_to_context, formatted_data
from datawinners.project.web_questionnaire_form import SubjectRegistrationForm
from datawinners.project.wizard_view import get_preview_and_instruction_links, get_reporting_period_field, _get_changed_data
from datawinners.questionnaire.questionnaire_builder import get_max_code
from mangrove.form_model.form_model import FormModel


class TestProjectViews(unittest.TestCase):
    def test_should_return_reminders_in_the_required_format(self):
        reminder1 = Mock(spec=Reminder)
        reminder1.message = ''
        reminder1.id = '1'
        reminder1.remind_to = RemindTo.DATASENDERS_WITHOUT_SUBMISSIONS
        reminder1.reminder_mode = ReminderMode.ON_DEADLINE
        reminder1.day = 0

        reminder2 = Mock(spec=Reminder)
        reminder2.message = ''
        reminder2.id = '2'
        reminder2.remind_to = RemindTo.ALL_DATASENDERS
        reminder2.reminder_mode = ReminderMode.BEFORE_DEADLINE
        reminder2.day = 2

        reminders = [reminder1, reminder2]
        formated_reminders = _format_reminders(reminders, 'test_project')

        self.assertEqual(2, len(formated_reminders))
        # self.assertEqnual('/project/delete_reminder/test_project/1/', formated_reminders[0]['delete_link'])

        self.assertEqual('On Deadline', formated_reminders[0]['when'])
        self.assertEqual('Datasenders Without Submissions', formated_reminders[0]['to'])

        self.assertEqual('2 days Before Deadline', formated_reminders[1]['when'])
        self.assertEqual('All Datasenders', formated_reminders[1]['to'])

    def test_should_return_subject_project_links(self):
        project_id = "1"
        entity_type = "entity_type"
        subject_links = make_subject_links(project_id, entity_type)
        self.assertEqual(reverse('registered_subjects', args=[project_id, entity_type]), subject_links['subjects_link'])
        self.assertEqual(reverse('edit_my_subject_questionnaire', args=[project_id, entity_type]), subject_links['subjects_edit_link'])
        self.assertEqual(reverse('subject_registration_form_preview', args=[project_id, entity_type]),
                         subject_links['subject_registration_preview_link'])
        self.assertEqual(reverse('registered_subjects', args=[project_id, entity_type]),
                         subject_links['registered_subjects_link'])
        self.assertEqual(reverse('subject_questionnaire', args=[project_id, entity_type]),
                         subject_links['register_subjects_link'])
        self.assertEqual(reverse('subject_questionnaire', args=[project_id, entity_type]) + "?web_view=True",
                         subject_links['register_subjects_link_web_view'])

    def test_should_get_preview_and_instruction_links(self):
        with patch("datawinners.project.wizard_view.reverse") as reverse:
            reverse.side_effect = lambda *args, **kw: "/project/%s" % args[0]
            links = get_preview_and_instruction_links()
            self.assertEqual(links["sms_preview"], "/project/sms_preview")
            self.assertEqual(links["web_preview"], "/project/web_preview")
            self.assertEqual(links["smart_phone_preview"], "/project/smart_phone_preview")

    def test_should_get_correct_context_for_sms_preview(self):
        questions = {}
        manager = {}
        form_model = Mock()
        form_model.fields = [{}]
        form_model.form_code = "form code"
        form_model.name="project_name"
        project_form = Mock()
        project_form.cleaned_data = {
            "name": "project_name", "entity_type": "clinic", "language": "en"
        }

        post = {"questionnaire-code": "q01",
                "question-set": "",
                "profile_form": '{"name":"project_name", "entity_type":"clinic", "language":"en"}'}

        project_info = json.loads(post['profile_form'])
        with patch("datawinners.project.preview_views.create_questionnaire") as questionnaire:
            questionnaire.return_value = form_model
            with patch("datawinners.project.preview_views.get_questions") as get_questions:
                get_questions.return_value = questions
                preview_context = get_sms_preview_context(manager, post, project_info)

                self.assertEquals(preview_context['questionnaire_code'], 'q01')
                self.assertEquals(preview_context['questions'], questions)
                self.assertEquals(preview_context['project_name'], "project_name")
                self.assertEquals(preview_context['example_sms'], "form code answer1")


    def test_should_get_question_list(self):
        form_model = Mock()
        form_model.fields = [{}]

        with patch("datawinners.project.preview_views.get_preview_for_field") as preview_of_field:
            preview_of_field.return_value = {"description": "description"}
            questions = get_questions(form_model)
            self.assertEquals(questions[0]["description"], "description")

    def test_should_get_correct_context_for_web_preview(self):
        manager = {}
        form_model = {}

        project_info = {"name": "project_name", "goals": "des", "entity_type": "clinic",
                        "language": "en"}
        with patch("datawinners.project.preview_views.get_questionnaire_form_model") as questionnaire_form_model:
            questionnaire_form_model.return_value = form_model
            with patch("datawinners.project.preview_views.SurveyResponseForm") as SurveyResponseForm:
                mock_form = Mock(spec=SurveyResponseForm)
                SurveyResponseForm.return_value = mock_form
                web_preview_context = get_web_preview_context_from_project_data(manager, {}, project_info)
                project = web_preview_context['project']
                questionnaire_form = web_preview_context['questionnaire_form']
                self.assertEquals(questionnaire_form, mock_form)


    def test_should_get_correct_instruction_and_preview_links_for_questionnaire(self):
        with patch("datawinners.project.views.views.reverse") as reverse:
            reverse.side_effect = lambda *args, **kw: "/project/%s" % args[0]
            links = get_preview_and_instruction_links_for_questionnaire()
            self.assertEqual(links["sms_preview"], "/project/questionnaire_sms_preview")
            self.assertEqual(links["web_preview"], "/project/questionnaire_web_preview")
            self.assertEqual(links["smart_phone_preview"], "/project/smart_phone_preview")


    def test_should_append_success_status_to_context_when_no_error(self):
        context = {}
        form = Mock(spec=ReporterRegistrationForm)
        form.errors = []
        new_context = append_success_to_context(context, form)
        self.assertTrue(new_context['success'])


    def test_should_append_failed_status_to_context_when_has_error(self):
        context = {}
        form = Mock(spec=ReporterRegistrationForm)
        form.errors = ['']
        new_context = append_success_to_context(context, form)
        self.assertFalse(new_context['success'])


    def test_should_return_max_code_in_questionnaire(self):
        fields = [TextField(name="f1", code="q1", label="f1"),
                  TextField(name="f2", code="q2", label="f2"),
                  TextField(name="f3", code="q3", label="f3"),
                  TextField(name="f3", code="q4", label="f4"),
                  TextField(name="f5", code="q5", label="f5")]
        self.assertEqual(5, get_max_code(fields))


    def test_should_return_one_in_questionnaire_without_start_with_q(self):
        fields = [TextField(name="f1", code="c1", label="f1"),
                  TextField(name="f2", code="c2", label="f2"),
                  TextField(name="f3", code="c3", label="f3"),
                  TextField(name="f3", code="c4", label="f4"),
                  TextField(name="f5", code="c5", label="f5")]
        self.assertEqual(1, get_max_code(fields))


    def test_should_return_reporting_period_field_if_questionnaire_contains(self):
        dateField = DateField(name="f2", code="c2", label="f2", date_format="dd.mm.yyyy",
                              event_time_field_flag=True)
        fields = [
            TextField(name="f1", code="c1", label="f1"),
            dateField]
        self.assertEqual(fields[1], get_reporting_period_field(fields))


    def test_should_return_none_if_questionnaire_dose_not_contains(self):
        dateField = DateField(name="f2", code="c2", label="f2", date_format="dd.mm.yyyy",
                              event_time_field_flag=False)
        fields = [
            TextField(name="f1", code="c1", label="f1"),
            dateField]
        self.assertEqual(None, get_reporting_period_field(fields))


    def test_should_return_origin_value_for_item_is_non_tuple_data(self):
        field_values = [['string']]
        data = formatted_data(field_values)
        self.assertEqual(data, [['string']])
        self.assertEqual(field_values, [['string']])


    def test_should_return_formatted_value_for_item_is_tuple_data_and_origin_not_changed(self):
        field_values = [[('key', 'value'), 'string']]
        data = formatted_data(field_values)
        self.assertEqual(data, [['key</br>(value)', 'string']])
        self.assertEqual(field_values, [[('key', 'value'), 'string']])

    def test_should_get_changed_data_when_project_is_edited(self):
        project_info = {'name':'changed name','language':'en'}
        project = Project(dbm=Mock(spec= DatabaseManager), name='old name', language='en',
                            form_code="change_form", fields=[])
        changed_dict = _get_changed_data(project,project_info)
        self.assertDictEqual({'Name':'changed name'},changed_dict)

class TestSubjectWebQuestionnaireRequest(unittest.TestCase):
    def test_form_should_not_have_initial_values_when_subject_creation_successful(self):
        request = HttpRequest()
        request.POST = {}
        request.user = User(username="atest")
        form = Mock(spec=SubjectRegistrationForm)
        form.is_valid.return_value = True
        with patch("datawinners.project.views.views.get_organization") as get_org:
            with patch("datawinners.project.views.views.ReportRouter") as router:
                with patch("datawinners.project.views.views.SubjectRegistrationForm") as subject_form:
                    with patch("datawinners.project.views.views.get_form_context"):
                        with patch("datawinners.project.views.views.RequestContext"):
                            with patch("datawinners.project.views.views.render_to_response"):
                                organization = Mock()
                                organization.country_name.return_value = "country"
                                get_org.return_value = organization
                                subject_form.return_value = Mock()
                                router.return_value = Mock()
                                subject_web_request = self.StubSubjectWebQuestionnaireRequest(request, "project_id","entity_type",
                                                                                              form)
                                subject_web_request.post()

                                self.assertTrue(subject_form.call_args_list == [call(None, data={}, country="country"),
                                                                                call(None, data=None,
                                                                                     country="country")]
                                    , msg="this should be called twice with the arguments as listed above")

    def test_form_should_have_initial_values_when_subject_edit_successful(self):
        request = HttpRequest()
        request.POST = {}
        request.user = User(username="atest")
        form = Mock(spec=SubjectRegistrationForm)
        form.is_valid.return_value = True
        with patch("datawinners.project.views.views.get_organization") as get_org:
            with patch("datawinners.project.views.views.ReportRouter") as router:
                with patch("datawinners.project.views.views.SubjectRegistrationForm") as subject_form:
                    with patch("datawinners.project.views.views.get_form_context"):
                        with patch("datawinners.project.views.views.RequestContext"):
                            with patch("datawinners.project.views.views.render_to_response"):
                                organization = Mock()
                                organization.country_name.return_value = "country"
                                get_org.return_value = organization
                                subject_form.return_value = Mock()
                                router.return_value = Mock()
                                subject_web_request = self.StubSubjectWebQuestionnaireRequest(request, "project_id","entity_type",
                                                                                              form)
                                subject_web_request.post(is_update=True)

                                self.assertTrue(subject_form.call_args_list == [call(None, data={}, country="country")]
                                    , msg="this should be called only once with the arguments as listed above")


    class StubSubjectWebQuestionnaireRequest(SubjectWebQuestionnaireRequest):
        def __init__(self, request, project_id, entity_type,form_list):
            self.form_list = form_list
            SubjectWebQuestionnaireRequest.__init__(self, request, project_id,entity_type)
            self.form_model = None


        def _initialize(self, project_id, entity_type):
            self.manager = None
            self.questionnaire = Mock(spec=FormModel)
            self.is_data_sender = True
            self.disable_link_class, self.hide_link_class = None, None
            self.form_code = None
            self.form_model = None
            self.entity_type = entity_type


        def player_response(self, created_request):
            return Response(success=True)

        def success_message(self, response_short_code):
            return ""

        def _update_form_context(self, form_context, questionnaire_form, web_view_enabled=True):
            return form_context