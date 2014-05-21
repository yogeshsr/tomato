import base64
from io import StringIO
import json
import logging
import mimetypes
import os
import re
from tempfile import NamedTemporaryFile

from django.contrib.auth.decorators import login_required

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_view_exempt, csrf_response_exempt, csrf_exempt
from django.views.generic.base import View
from django_digest.decorators import httpdigest
import xlwt
from datawinners import settings

from datawinners.accountmanagement.decorators import session_not_expired, is_not_expired, is_datasender_allowed, project_has_web_device, is_datasender
from datawinners.blue.auth import logged_in_or_basicauth, enable_cors
from datawinners.blue.xform_bridge import MangroveService, XlsFormParser, XFormTransformer, XFormSubmissionProcessor, XlsProjectParser
from datawinners.blue.xform_web_submission_handler import XFormWebSubmissionHandler
from datawinners.main.database import get_database_manager
from datawinners.project.helper import generate_questionnaire_code, is_project_exist
from datawinners.project.models import Project
from datawinners.project.utils import is_quota_reached
from datawinners.project.views.utils import get_form_context
from datawinners.project.views.views import SurveyWebQuestionnaireRequest
from datawinners.project.wizard_view import update_associated_submissions, \
    _get_deleted_question_codes
from datawinners.questionnaire.questionnaire_builder import QuestionnaireBuilder
from datawinners.utils import workbook_add_sheet
from mangrove.form_model.form_model import FormModel, get_form_model_by_code
from mangrove.transport.repository.survey_responses import get_survey_response_by_id, survey_responses_by_form_code
from mangrove.utils.dates import py_datetime_to_js_datestring

logger = logging.getLogger("datawinners.blue")

class ProjectUpload(View):

    @method_decorator(csrf_view_exempt)
    @method_decorator(csrf_response_exempt)
    @method_decorator(login_required)
    @method_decorator(session_not_expired)
    @method_decorator(is_not_expired)
    def dispatch(self, *args, **kwargs):
        return super(ProjectUpload, self).dispatch(*args, **kwargs)

    def post(self, request):
        try:
            file_name = request.GET.get('qqfile').split('.')[0]
            file_content = request.raw_post_data
            tmp_file = NamedTemporaryFile(delete=True, suffix=".xls")
            tmp_file.write(file_content)
            tmp_file.seek(0)

            manager = get_database_manager(request.user)
            questionnaire_code =  generate_questionnaire_code(manager)
            project_name = file_name + '-' + questionnaire_code

            xform_as_string, json_xform_data = XlsFormParser(tmp_file, project_name=project_name).parse()

            mangroveService = MangroveService(request.user, xform_as_string, json_xform_data, questionnaire_code=questionnaire_code, project_name=project_name, xls_form=file_content)
            id, name = mangroveService.create_project()
        except Exception as e:
            return HttpResponse(content_type='application/json', content=json.dumps({'error_msg':e.message}))

        return HttpResponse(
            json.dumps(
                {
                    "project_name": name,
                    "project_id": id,
                    "xls_dict":XlsProjectParser().parse(file_content)
                }),
            content_type='application/json')


class ProjectUpdate(View):

    @method_decorator(csrf_view_exempt)
    @method_decorator(csrf_response_exempt)
    @method_decorator(login_required)
    @method_decorator(session_not_expired)
    @method_decorator(is_not_expired)
    def dispatch(self, *args, **kwargs):
        return super(ProjectUpdate, self).dispatch(*args, **kwargs)

    def post(self, request, project_id):
        manager = get_database_manager(request.user)
        questionnaire = Project.get(manager, project_id)
        try:
            file_name = request.GET.get('qqfile').split('.')[0]
            file_content = request.raw_post_data
            tmp_file = NamedTemporaryFile(delete=True, suffix=".xls")
            tmp_file.write(file_content)
            tmp_file.seek(0)
            is_project_name_changed = file_name != questionnaire.name
            xform_as_string, json_xform_data = XlsFormParser(tmp_file, project_name=questionnaire.name).parse()
            mangroveService = MangroveService(request.user, xform_as_string, json_xform_data, questionnaire_code=questionnaire.form_code, project_name=questionnaire.name)

            old_fields = questionnaire.fields
            old_form_code = questionnaire.form_code
            old_field_codes = questionnaire.field_codes()

            QuestionnaireBuilder(questionnaire, manager).update_questionnaire_with_questions(json_xform_data)
            questionnaire.xform = mangroveService.xform_with_form_code

            # questionnaire.qid = questionnaire.save()
            questionnaire.update_attachments(file_content,attachment_name='questionnaire.xls')
            deleted_question_codes = _get_deleted_question_codes(old_codes=old_field_codes,
                                                                 new_codes=questionnaire.field_codes())
            update_associated_submissions(manager.database_name, old_form_code,
                                                questionnaire.form_code,
                                                deleted_question_codes)

            questionnaire.save()
        except Exception as e:
            return HttpResponse(content_type='application/json', content=json.dumps({'error_msg':e.message}))

        return HttpResponse(
            json.dumps(
                {
                    "project_name": questionnaire.name,
                    "project_id": questionnaire.id,
                    "xls_dict":XlsProjectParser().parse(file_content)
                }),
            content_type='application/json')

@login_required
@session_not_expired
@csrf_exempt
@is_not_expired
def upload_project(request):

    return render_to_response('project/xform_project.html')

@login_required(login_url='/login')
@session_not_expired
@is_project_exist
@is_datasender_allowed
@project_has_web_device
@is_not_expired
def xform_survey_web_questionnaire(request, project_id=None):
    survey_request = SurveyWebXformQuestionnaireRequest(request, project_id,  XFormSubmissionProcessor())
    if request.method == 'GET':
        return survey_request.response_for_get_request()

#@login_required(login_url='/login')
#@session_not_expired
#@is_datasender_allowed
#@project_has_web_device
#@is_not_expired
#@is_project_exist
def xform_questionnaire(request, project_id=None):

    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    form_model = FormModel.get(manager, project.qid)
    response = HttpResponse(content_type='application/xml')
    response['Content-Disposition'] = 'attachment; filename=form.xml'
    response.write(form_model.xform)
    response['Content-Length'] = len(response.content)
    assert len(form_model.xform) == len(response.content)
    return response


class SurveyWebXformQuestionnaireRequest(SurveyWebQuestionnaireRequest):

    def __init__(self, request, project_id=None, submissionProcessor=None):
        SurveyWebQuestionnaireRequest.__init__(self, request, project_id)
        self.submissionProcessor = submissionProcessor

    @property
    def template(self):
        return 'project/xform_web_questionnaire.html'

    def response_for_get_request(self, initial_data=None, is_update=False):
        dashboard_page = settings.HOME_PAGE + "?deleted=true"
        if self.questionnaire.is_void():
            return HttpResponseRedirect(dashboard_page)
        questionnaire_form = self.form(initial_data=initial_data)
        form_context = get_form_context(self.questionnaire, questionnaire_form,
                                        self.manager, self.hide_link_class, self.disable_link_class,is_update)
        if self.questionnaire.xform:
            form_context.update({'xform_xml':re.sub(r"\n", " ", XFormTransformer(self.questionnaire.xform).transform())})
            form_context.update({'is_advance_questionnaire': True})
            form_context.update({'submission_create_url': reverse('new_web_submission')})
        form_context.update({'is_quota_reached': is_quota_reached(self.request)})
        return render_to_response(self.template, form_context, context_instance=RequestContext(self.request))

    def _model_str_of(self, survey_response_id, project_name):
        survey_response = get_survey_response_by_id(self.manager, survey_response_id)
        xform_instance_xml = self.submissionProcessor.\
            get_model_edit_str(self.questionnaire.fields, survey_response.values, project_name, self.questionnaire.form_code,)
        return xform_instance_xml

    def response_for_xform_edit_get_request(self, survey_response_id):

        #todo delete/refactor this block
        dashboard_page = settings.HOME_PAGE + "?deleted=true"
        if self.questionnaire.is_void():
            return HttpResponseRedirect(dashboard_page)
        questionnaire_form = self.form(initial_data=None)
        form_context = get_form_context(self.questionnaire, questionnaire_form,
                                        self.manager, self.hide_link_class, self.disable_link_class, False)

        if self.questionnaire.xform:
            form_context.update({'survey_response_id': survey_response_id })
            form_context.update({'xform_xml':re.sub(r"\n", " ", XFormTransformer(self.questionnaire.xform).transform())})
            form_context.update({'edit_model_str': self._model_str_of(survey_response_id, self.questionnaire.name)})
            form_context.update({'submission_update_url': reverse('update_web_submission', kwargs={'survey_response_id':survey_response_id})})
            form_context.update({'is_advance_questionnaire': True})

        form_context.update({'is_quota_reached': is_quota_reached(self.request)})
        return render_to_response(self.template, form_context, context_instance=RequestContext(self.request))

    def get_submissions(self):
        submission_list = []
        questionnaire = FormModel.get(self.manager, self.questionnaire.qid)
        submissions = survey_responses_by_form_code(self.manager,questionnaire.form_code)
        for submission in submissions:
            submission_list.append({'id': submission.id,
                                    'form_code': self.questionnaire.id,
                                    'type': "surveyResponse",
                                    'created': py_datetime_to_js_datestring(submission.created),
                                    'xml': self._model_str_of(submission.id, self.questionnaire.name)
                                  })
        return submission_list

@csrf_exempt
def new_web_submission(request):
    try:
        response = XFormWebSubmissionHandler(request.user, request=request).\
            create_new_submission_response()
        response['Location'] = request.build_absolute_uri(request.path)
        return response
    except Exception as e:
        logger.exception("Exception in submission : \n%s" % e)
        return HttpResponseBadRequest()


@csrf_exempt
@logged_in_or_basicauth()
def upload_submission(request):
    try:
        response = XFormWebSubmissionHandler(request.user, request=request).\
            create_new_submission_response()
        response['Location'] = request.build_absolute_uri(request.path)
        return enable_cors(response)
    except Exception as e:
        logger.exception("Exception in submission : \n%s" % e)
        return HttpResponseBadRequest()

@csrf_exempt
def update_web_submission(request, survey_response_id):
    try:
        return XFormWebSubmissionHandler(request.user, request=request).\
            update_submission_response(survey_response_id)
    except Exception as e:
        logger.exception("Exception in submission : \n%s" % e)
        return HttpResponseBadRequest()

@csrf_exempt
@logged_in_or_basicauth()
def get_questionnaires(request):
    manager =  get_database_manager(request.user)
    project_list = []
    rows = manager.load_all_rows_in_view('all_projects', descending=True)
    for row in rows:
        project =  Project.load(manager.database, row['id']);
        questionnaire = FormModel.get(manager, project.qid)
        if questionnaire.xform:
            project_temp = dict(name=project.name, id=project.id, xform=re.sub(r"\n", " ", XFormTransformer(questionnaire.xform).transform()))
            project_list.append(project_temp)
    content = json.dumps(project_list)
    if request.GET.get('callback'):
        content= request.GET['callback'] + '('+ content + ')'
    response = HttpResponse(content, status=200, content_type='application/json')

    return enable_cors(response)

@csrf_exempt
@logged_in_or_basicauth()
def get_submissions(request, survey_id):
    survey_request = SurveyWebXformQuestionnaireRequest(request, survey_id, XFormSubmissionProcessor())
    content = json.dumps(survey_request.get_submissions())
    if request.GET.get('callback'):
       content= request.GET['callback'] + '('+ content + ')'
    response = HttpResponse(content, status=200, content_type='application/json')
    return enable_cors(response)

def get_attachment(request, document_id, attachment_name):
     manager = get_database_manager(User.objects.get(username='tester150411@gmail.com'))
     return HttpResponse(manager.get_attachments(document_id, attachment_name=attachment_name))

def attachment_download(request, document_id, attachment_name):
     manager = get_database_manager(User.objects.get(username='tester150411@gmail.com'))
     raw_file = manager.get_attachments(document_id, attachment_name=attachment_name)
     mime_type = mimetypes.guess_type(os.path.basename(attachment_name))[0]
     response = HttpResponse(raw_file, mimetype=mime_type)
     response['Content-Disposition'] = 'attachment; filename="%s"' % attachment_name
     return response

@login_required
@session_not_expired
@is_datasender
@is_not_expired
def project_download(request):
    project_name = request.POST.get(u"project_name")
    questionnaire_code = request.POST.get(u'questionnaire_code')

    manager = get_database_manager(request.user)
    questionnaire = get_form_model_by_code(manager, questionnaire_code)
    raw_excel = questionnaire.get_attachments('questionnaire.xls')
    excel_transformed = XlsProjectParser().parse(raw_excel);

    response = HttpResponse(mimetype="application/vnd.ms-excel")
    response['Content-Disposition'] = 'attachment; filename="%s.xls"' % project_name

    wb = xlwt.Workbook()
    for sheet in excel_transformed:
        workbook_add_sheet(wb, excel_transformed[sheet], sheet)
    wb.save(response)
    return response
