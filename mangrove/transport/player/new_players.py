import base64
import inspect
from mangrove.form_model.form_model import NAME_FIELD
from mangrove.transport.player.parser import WebParser, SMSParserFactory, XFormParser
from mangrove.transport.repository.survey_responses import get_survey_response_document
from mangrove.transport.services.survey_response_service import SurveyResponseService
from mangrove.transport.repository import reporters


class WebPlayerV2(object):
    def __init__(self, dbm, feeds_dbm=None, admin_id=None):
        self.dbm = dbm
        self.feeds_dbm = feeds_dbm
        self.admin_id = admin_id

    def add_survey_response(self, request, reporter_id, additional_feed_dictionary=None, logger=None):
        assert request is not None
        form_code, values = self._parse(request.message)
        service = SurveyResponseService(self.dbm, logger, self.feeds_dbm, self.admin_id)
        return service.save_survey(form_code, values, [], request.transport, request.message,
                                   reporter_id, additional_feed_dictionary)

    def _parse(self, message):
        return WebParser().parse(message)

    def edit_survey_response(self, request, survey_response, owner_id, additional_feed_dictionary=None, logger=None):
        assert request is not None
        form_code, values = self._parse(request.message)
        service = SurveyResponseService(self.dbm, logger, feeds_dbm=self.feeds_dbm, admin_id=self.admin_id)
        return service.edit_survey(form_code, values, [], request.transport, request.message, survey_response,
                                   additional_feed_dictionary, owner_id)

    def delete_survey_response(self, survey_response, additional_details, logger=None):
        assert survey_response is not None
        service = SurveyResponseService(self.dbm, logger, self.feeds_dbm)
        return service.delete_survey(survey_response, additional_details)


class SMSPlayerV2(object):
    def __init__(self, dbm, post_sms_parser_processors, feeds_dbm=None):
        self.post_sms_parser_processor = post_sms_parser_processors if post_sms_parser_processors else []
        self.dbm = dbm
        self.feeds_dbm = feeds_dbm

    def _post_parse_processor(self, form_code, values, extra_elements=None):
        extra_elements = [] if extra_elements is None else extra_elements
        for post_sms_parser_processors in self.post_sms_parser_processor:
            if len(inspect.getargspec(post_sms_parser_processors.process)[0]) == 4:
                response = post_sms_parser_processors.process(form_code, values, extra_elements)
            else:
                response = post_sms_parser_processors.process(form_code, values)
            if response is not None:
                return response

    def add_survey_response(self, request, logger=None, additional_feed_dictionary=None):
        form_code, values, extra_elements = self._parse(request.message)
        post_sms_processor_response = self._post_parse_processor(form_code, values, extra_elements)

        if post_sms_processor_response is not None and not post_sms_processor_response.success:
            if logger is not None:
                log_entry = "message:message " + repr(request.message) + "|source: " + request.transport.source + "|"
                log_entry += "Status: False"
                logger.info(log_entry)
            return post_sms_processor_response

        reporter_entity = reporters.find_reporter_entity(self.dbm, request.transport.source)
        reporter_entity_names = [{NAME_FIELD: reporter_entity.value(NAME_FIELD)}]

        service = SurveyResponseService(self.dbm, logger, self.feeds_dbm, response=post_sms_processor_response)
        return service.save_survey(form_code, values, reporter_entity_names, request.transport, request.message,
                                   reporter_entity.short_code,
                                   additional_feed_dictionary=additional_feed_dictionary)

    def _parse(self, message):
        return SMSParserFactory().getSMSParser(message, self.dbm).parse(message)


class XFormPlayerV2(object):
    def __init__(self, dbm, feeds_dbm=None):
        self.dbm = dbm
        self.feeds_dbm = feeds_dbm

    def _parse(self, message):
        return XFormParser(self.dbm).parse(message)

    def add_survey_response(self, request, reporter_id, logger=None):
        assert request is not None
        form_code, values = self._parse(request.message)
        mediaFiles = request.media
        service = SurveyResponseService(self.dbm, logger, self.feeds_dbm)
        response = service.save_survey(form_code, values, [], request.transport, request.message, reporter_id)
        if mediaFiles:
            for mediaFile in mediaFiles:
                self.dbm.put_attachment(get_survey_response_document(self.dbm, response.survey_response_id), base64.decodestring(mediaFiles[mediaFile].split(',')[1]), attachment_name=mediaFile)
        return response

    def update_survey_response(self, request, reporter_id, logger=None, survey_response=None, additional_feed_dictionary=None):
        assert request is not None
        form_code, values = self._parse(request.message)
        service = SurveyResponseService(self.dbm, logger, self.feeds_dbm)
        return service.edit_survey(form_code, values, [], request.transport, request.message, survey_response,
                                   additional_feed_dictionary, reporter_id)
