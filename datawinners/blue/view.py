import json
from tempfile import NamedTemporaryFile

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_view_exempt, csrf_response_exempt
from django.views.generic.base import View
from pyxform import create_survey_from_path, create_survey_from_xls, create_survey_element_from_dict
from pyxform.xls2json import SurveyReader, workbook_to_json
from pyxform.xls2json_backends import xls_to_dict
import xlrd

from datawinners.accountmanagement.decorators import session_not_expired, is_not_expired
from datawinners.blue.xfom_bridge import XfromToJson, MangroveService, XlsFormToJson
from datawinners.entity.import_data import get_filename_and_contents


class ProjectUpload(View):

    @method_decorator(csrf_view_exempt)
    @method_decorator(csrf_response_exempt)
    @method_decorator(login_required)
    @method_decorator(session_not_expired)
    @method_decorator(is_not_expired)
    def dispatch(self, *args, **kwargs):
        return super(ProjectUpload, self).dispatch(*args, **kwargs)

    def post(self, request):

        file_name = request.GET.get('qqfile')
        file = request.raw_post_data

        xform_as_string, json_xform_data = XlsFormToJson(file).parse()

        # mangrove code
        mangroveService = MangroveService(xform_as_string, json_xform_data)
        id, name = mangroveService.create_project()


        return HttpResponse(
            json.dumps(
                {
                    "project_name": name
                }),
            content_type='application/json')
