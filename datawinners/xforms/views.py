import logging
import xml
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django_digest.decorators import httpdigest
from datawinners.feeds.database import get_feeds_database
from datawinners.feeds.mail_client import mail_feed_errors
from datawinners.main.database import get_database_manager
from mangrove.transport.contract.request import Request
from mangrove.transport.contract.transport_info import TransportInfo
from mangrove.transport.player.new_players import XFormPlayerV2
from mangrove.transport.xforms.xform import list_all_forms, xform_for
from datawinners.accountmanagement.models import Organization, NGOUserProfile
from datawinners.alldata.helper import get_all_project_for_user
from django.contrib.gis.utils import GeoIP
from datawinners.messageprovider.messages import SMART_PHONE
from datawinners.project.utils import is_quota_reached
from datawinners.submission.views import check_quotas_and_update_users

logger = logging.getLogger("datawinners.xform")
sp_submission_logger = logging.getLogger("sp-submission")


def is_not_local_address(remote_address):
    return remote_address not in ["127.0.0.1", "localhost"]


def restrict_request_country(f):
    def wrapper(*args, **kw):
        # request = args[0]
        # user = request.user
        #
        # org = Organization.objects.get(org_id=user.get_profile().org_id)
        # try:
        #     remote_address = request.META.get('REMOTE_ADDR')
        #     if is_not_local_address(remote_address):
        #         country_code = GeoIP().country_code(remote_address)
        #         log_message = 'User: %s, IP: %s resolved in %s, for Oragnization id: %s located in country: %s ' %\
        #               (user, request.META.get('REMOTE_ADDR'), country_code, org.org_id, org.country)
        #     else:
        #         log_message = "Skipping resolving ip to country for local address %s" % remote_address
        #     logger.info(log_message)
        # except Exception as e:
        #     logger.exception("Error resolving country from IP : \n%s" % e)
        #     raise

        return f(*args, **kw)

    return wrapper


@csrf_exempt
@httpdigest
@restrict_request_country
def formList(request):
    rows = get_all_project_for_user(request.user)
    form_tuples = [(row['value']['name'], row['id']) for row in rows]
    xform_base_url = request.build_absolute_uri('/xforms')
    response = HttpResponse(content=list_all_forms(form_tuples, xform_base_url), mimetype="text/xml")
    response['X-OpenRosa-Version'] = '1.0'
    return response


def get_errors(errors):
    return '\n'.join(['{0} : {1}'.format(key, val) for key, val in errors.items()])


def __authorized_to_make_submission_on_requested_form(request_user, submission_file):
    rows = get_all_project_for_user(request_user)
    form_code_list = [(row['value']['form_code']) for row in rows]
    dom = xml.dom.minidom.parseString(submission_file)
    requested_form_code = dom.getElementsByTagName('form_code')[0].firstChild.data
    return requested_form_code in form_code_list


@csrf_exempt
@httpdigest
@restrict_request_country
def submission(request):
    if request.method != 'POST':
        response = HttpResponse(status=204)
        response['Location'] = request.build_absolute_uri()
        return response

    request_user = request.user
    submission_file = request.FILES.get("xml_submission_file").read()

    if not __authorized_to_make_submission_on_requested_form(request_user, submission_file) \
        or is_quota_reached(request):
        response = HttpResponse(status=403)
        return response

    manager = get_database_manager(request_user)
    player = XFormPlayerV2(manager, get_feeds_database(request_user))
    try:
        user_profile = NGOUserProfile.objects.get(user=request_user)
        mangrove_request = Request(message=submission_file,
            transportInfo=
            TransportInfo(transport=SMART_PHONE,
                source=request_user.email,
                destination=''
            ), media=request.FILES if len(request.FILES)>1 else [])

        response = player.add_survey_response(mangrove_request, user_profile.reporter_id ,logger=sp_submission_logger)
        mail_feed_errors(response, manager.database_name)
        if response.errors:
            logger.error("Error in submission : \n%s" % get_errors(response.errors))
            return HttpResponseBadRequest()

    except Exception as e:
        logger.exception("Exception in submission : \n%s" % e)
        return HttpResponseBadRequest()

    organization = Organization.objects.get(org_id=user_profile.org_id)
    organization.increment_message_count_for(incoming_sp_count=1)

    check_quotas_and_update_users(organization)
    response = HttpResponse(status=201)
    response['Location'] = request.build_absolute_uri(request.path)
    return response


@csrf_exempt
@httpdigest
def xform(request, questionnaire_code=None):
    request_user = request.user
    form = xform_for(get_database_manager(request_user), questionnaire_code, request_user.get_profile().reporter_id)
    return HttpResponse(content=form, mimetype="text/xml")
