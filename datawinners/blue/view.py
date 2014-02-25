import json
from tempfile import NamedTemporaryFile

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_view_exempt, csrf_response_exempt
from django.views.generic.base import View

from datawinners.accountmanagement.decorators import session_not_expired, is_not_expired
from datawinners.blue.xform_bridge import MangroveService, XlsFormParser
from datawinners.main.database import get_database_manager
from datawinners.project.helper import generate_questionnaire_code


class ProjectUpload(View):

    @method_decorator(csrf_view_exempt)
    @method_decorator(csrf_response_exempt)
    @method_decorator(login_required)
    @method_decorator(session_not_expired)
    @method_decorator(is_not_expired)
    def dispatch(self, *args, **kwargs):
        return super(ProjectUpload, self).dispatch(*args, **kwargs)

    def post(self, request):

        file_name = request.GET.get('qqfile').split('.')[0]
        file_content = request.raw_post_data
        tmp_file = NamedTemporaryFile(delete=True, suffix=".xls")
        tmp_file.write(file_content)
        tmp_file.seek(0)

        manager = get_database_manager(request.user)
        questionnaire_code =  generate_questionnaire_code(manager)
        project_name = file_name + '-' + questionnaire_code

        xform_as_string, json_xform_data = XlsFormParser(tmp_file, project_name=project_name).parse()

        mangroveService = MangroveService(xform_as_string, json_xform_data, questionnaire_code=questionnaire_code, project_name=project_name)
        id, name = mangroveService.create_project()

        return HttpResponse(
            json.dumps(
                {
                    "project_name": name,
                    "project_id": id
                }),
            content_type='application/json')
