# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import logging
import re
from datetime import datetime

from babel.dates import format_date
from django.http import Http404
from django.utils.translation import gettext as _
from django.utils.translation import ugettext

from datawinners.accountmanagement.models import NGOUserProfile
from datawinners.scheduler.smsclient import SMSClient
from mangrove.errors.MangroveException import FormModelDoesNotExistsException
from mangrove.form_model.field import TextField, IntegerField, DateField, GeoCodeField
from mangrove.form_model.form_model import FormModel, get_form_model_by_code
from mangrove.form_model.validation import  TextLengthConstraint
from mangrove.utils.types import  is_sequence, sequence_to_str
from datawinners.sms.models import MSG_TYPE_USER_MSG
import models
from models import Reminder
from mangrove.transport.repository.survey_responses import get_survey_responses
from mangrove.transport.contract.transport_info import TransportInfo
from mangrove.transport.contract.request import Request


SUBMISSION_DATE_FORMAT_FOR_SUBMISSION = "%b. %d, %Y, %I:%M %p"

DEFAULT_DATE_FORMAT = 'dd.MM.yyyy'

NOT_AVAILABLE = "N/A"
NOT_AVAILABLE_DS = "Unknown"

logger = logging.getLogger("datawinners.reminders")

def _create_entity_id_question(dbm, entity_id_question_code):
    name = ugettext("Which subject are you reporting on?")
    entity_id_question = TextField(name=name, code=entity_id_question_code,
        label=name,
        entity_question_flag=True ,
        constraints=[TextLengthConstraint(min=1, max=20)],
        instruction=(ugettext('Answer must be a word %d characters maximum') % 20))
    return entity_id_question


def hide_entity_question(fields):
    return [each for each in fields if not each.is_entity_field]

def get_according_value(value_dict, question):
    value = value_dict.get(question.code.lower(), '--')
    if value != '--' and question.type in ['select1', 'select']:
        value_list = question.get_option_value_list(value)
        return ", ".join(value_list)
    return value


def generate_questionnaire_code(dbm):
    all_projects_count = models.count_projects(dbm)
    code = all_projects_count + 1
    code = "%03d" % (code,)
    while True:
        try:
            get_form_model_by_code(dbm, code)
            code = int(code) + 1
            code = "%03d" % (code,)
        except FormModelDoesNotExistsException:
            break
    return code

def get_org_id_by_user(user):
    return NGOUserProfile.objects.get(user=user).org_id

def case_insensitive_lookup(search_key, dictionary):
    assert isinstance(dictionary, dict)
    for key, value in dictionary.items():
        if key.lower() == search_key.lower():
            return value
    return None

def get_values_from_dict(dictionary):
    for key, value in dictionary.items():
        return value

def _to_str(value, form_field=None):
    if value is None:
        return u"--"
    if is_sequence(value):
        return sequence_to_str(value)
    if isinstance(value, datetime):
        date_format = DateField.FORMAT_DATE_DICTIONARY.get(
            form_field.date_format) if form_field else DEFAULT_DATE_FORMAT
        return format_date(value, date_format)
    return value

def format_dt_for_submission_log_page(survey_response):
    return survey_response.submitted_on.strftime(SUBMISSION_DATE_FORMAT_FOR_SUBMISSION)

def get_formatted_time_string(time_val):
    try:
        time_val = datetime.strptime(time_val, '%d-%m-%Y %H:%M:%S')
    except Exception:
        return None
    return time_val.strftime('%d-%m-%Y %H:%M:%S')

def remove_reporter(entity_type_list):
    removable = None
    for each in entity_type_list:
        if each[0].lower() == 'reporter':
            removable = each
    entity_type_list.remove(removable)
    entity_type_list.sort()
    return entity_type_list


def get_preview_for_field(field):
    preview = {"description": field.name, "code": field.code, "type": field.type, "instruction": field.instruction}
    constraints = field.get_constraint_text() if field.type not in ["select", "select1"] else\
    [(option["text"], option["val"]) for option in field.options]
    preview.update({"constraints": constraints})
    return preview

def delete_project(manager, project, void=True):
    project_id, qid = project.id, project.qid
    [reminder.void(void) for reminder in (Reminder.objects.filter(project_id=project_id))]
    questionnaire = FormModel.get(manager, qid)
    questionnaire.void(void)
    [survey_response.void(void) for survey_response in get_survey_responses(manager, questionnaire.form_code, None, None)]
    project.set_void(manager, void)

def get_activity_report_questions(dbm):
    activity_report_question = DateField(name=ugettext("What is the reporting period for the activity?"), code='q1',
        label="Period being reported on" ,
        date_format="dd.mm.yyyy", event_time_field_flag=True)

    return [activity_report_question]

def get_subject_report_questions(dbm):
    entity_id_question = _create_entity_id_question(dbm, 'q1')
    activity_report_question = DateField(name=ugettext("What is the reporting period for the activity?"), code='q2',
        label="Period being reported on" ,
        date_format="dd.mm.yyyy", event_time_field_flag=True)
    return [entity_id_question, activity_report_question]

def broadcast_message(data_senders, message, organization_tel_number, other_numbers, message_tracker, country_code=None):
    """

    :param data_senders:
    :param message:
    :param organization_tel_number:
    :param other_numbers:
    :param message_tracker:
    :param country_code:
    :return:
    """
    sms_client = SMSClient()
    sms_sent = None
    failed_numbers = []
    for data_sender in data_senders:
        phone_number = data_sender.get(
            'mobile_number') #This should not be a dictionary but the API in import_data should be fixed to return entity
        if phone_number is not None:
            logger.info(("Sending broadcast message to %s from %s") % (phone_number, organization_tel_number))
            sms_sent = sms_client.send_sms(organization_tel_number, phone_number, message, MSG_TYPE_USER_MSG)
        if sms_sent:
            message_tracker.increment_message_count_for(send_message_count=1)
        else:
            failed_numbers.append(phone_number)

    for number in other_numbers:
        number = number.strip()
        number_with_country_prefix = number
        if country_code:
            number_with_country_prefix = "%s%s" % (country_code, re.sub(r"^[ 0]+", "", number))

        logger.info(("Sending broadcast message to %s from %s") % (number_with_country_prefix, organization_tel_number))
        sms_sent = sms_client.send_sms(organization_tel_number, number_with_country_prefix, message, MSG_TYPE_USER_MSG)
        if sms_sent:
            message_tracker.increment_message_count_for(send_message_count=1)
        else:
            failed_numbers.append(number)

    return failed_numbers


def create_request(questionnaire_form, username, is_update=None):
    return Request(message=questionnaire_form.cleaned_data, media=[],
        transportInfo=get_web_transport_info(username), is_update=is_update)


def _translate_messages(error_dict, fields):
    errors = dict()

    for field in fields:
        if field.code in error_dict:
            error = error_dict[field.code][0]
            if type(field) == TextField:
                text, code = error.split(' ')[1], field.code
                errors[code] = [ugettext("Answer %s for question %s is longer than allowed.") % (text, code)]
            if type(field) == IntegerField:
                number, error_context = error.split(' ')[1], error.split(' ')[6]
                errors[field.code] = [
                    ugettext("Answer %s for question %s is %s than allowed.") % (number, field.code, _(error_context),)]
            if type(field) == GeoCodeField:
                errors[field.code] = [ugettext(
                    "Incorrect GPS format. The GPS coordinates must be in the following format: xx.xxxx,yy.yyyy. Example -18.8665,47.5315.")]
            if type(field) == DateField:
                answer, format = error.split(' ')[1], field.date_format
                errors[field.code] = [ugettext("Answer %s for question %s is invalid. Expected date in %s format") % (
                    answer, field.code, format)]

    return errors


def errors_to_list(errors, fields):
    error_dict = dict()
    for key, value in errors.items():
        field_index = int(key[1:]) -1
        error_dict.update({fields[field_index].code: [value] if not isinstance(value, list) else value})
    return _translate_messages(error_dict, fields)


def is_project_exist(f):
    def wrapper(*args, **kw):
        try:
            ret = f(*args, **kw)
        except AttributeError, e:
            if e[0] == "'NoneType' object has no attribute 'qid'":
                raise Http404
            raise e
        return ret

    return wrapper


def get_feed_dictionary(project):
        additional_feed_dictionary = {}
        project_dict = {
            'id': project.id,
            'name': project.name,
            'type': project.entity_type,
        }
        additional_feed_dictionary.update({'project': project_dict})
        return additional_feed_dictionary


def get_web_transport_info(username):
        return TransportInfo(transport="web", source=username, destination="")