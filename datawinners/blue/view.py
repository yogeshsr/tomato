import json
import re
from tempfile import NamedTemporaryFile

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_view_exempt, csrf_response_exempt, csrf_exempt
from django.views.generic.base import View
from datawinners import settings

from datawinners.accountmanagement.decorators import session_not_expired, is_not_expired, is_datasender_allowed, project_has_web_device
from datawinners.blue.xform_bridge import MangroveService, XlsFormParser, XFormTransformer, XFormSubmissionProcessor
from datawinners.main.database import get_database_manager
from datawinners.project.helper import generate_questionnaire_code, is_project_exist
from datawinners.project.models import Project
from datawinners.project.utils import is_quota_reached
from datawinners.project.views.utils import get_form_context
from datawinners.project.views.views import SurveyWebQuestionnaireRequest
from mangrove.form_model.form_model import FormModel
from mangrove.transport.repository.survey_responses import get_survey_response_by_id


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

            mangroveService = MangroveService(request.user, xform_as_string, json_xform_data, questionnaire_code=questionnaire_code, project_name=project_name)
            id, name = mangroveService.create_project()
        except Exception as e:
            return HttpResponse(content_type='application/json', content=json.dumps({'error_msg':e.message}))

        return HttpResponse(
            json.dumps(
                {
                    "project_name": name,
                    "project_id": id
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
        if self.project.is_deleted():
            return HttpResponseRedirect(dashboard_page)
        questionnaire_form = self.form(initial_data=initial_data)
        form_context = get_form_context(self.form_model.form_code, self.project, questionnaire_form,
                                        self.manager, self.hide_link_class, self.disable_link_class, is_update)
        if self.form_model.xform:
            form_context.update({'xform_xml':re.sub(r"\n", " ", XFormTransformer(self.form_model.xform).transform())})
        form_context.update({'is_quota_reached': is_quota_reached(self.request)})
        return render_to_response(self.template, form_context, context_instance=RequestContext(self.request))

    def _model_str_of(self, survey_response_id, project_name):
        survey_response = get_survey_response_by_id(self.manager, survey_response_id)
        xform_instance_xml = self.submissionProcessor.\
            get_model_edit_str(self.form_model.fields, survey_response.values, project_name)
        return xform_instance_xml

    def response_for_xform_edit_get_request(self, survey_response_id):

        #todo delete/refactor this block
        dashboard_page = settings.HOME_PAGE + "?deleted=true"
        if self.project.is_deleted():
            return HttpResponseRedirect(dashboard_page)
        questionnaire_form = self.form(initial_data=None)
        form_context = get_form_context(self.form_model.form_code, self.project, questionnaire_form,
                                        self.manager, self.hide_link_class, self.disable_link_class, False)

        if self.form_model.xform:
            form_context.update({'survey_response_id': survey_response_id })
            form_context.update({'xform_xml':re.sub(r"\n", " ", XFormTransformer(self.form_model.xform).transform())})
            form_context.update({'edit_model_str': self._model_str_of(survey_response_id, self.project.name)})

        form_context.update({'is_quota_reached': is_quota_reached(self.request)})
        return render_to_response(self.template, form_context, context_instance=RequestContext(self.request))