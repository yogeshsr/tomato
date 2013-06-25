from copy import copy
import traceback
from mangrove.datastore.entity import by_short_code
from mangrove.feeds.enriched_survey_response import EnrichedSurveyResponseBuilder, get_feed_document_by_id
from mangrove.form_model.forms import EditSurveyResponseForm
from mangrove.form_model.form_submission import DataFormSubmission
from mangrove.errors.MangroveException import MangroveException
from mangrove.errors.MangroveException import InactiveFormModelException
from mangrove.form_model.form_model import get_form_model_by_code
from mangrove.transport.contract.submission import Submission
from mangrove.transport.contract.response import Response
from mangrove.transport.repository.reporters import REPORTER_ENTITY_TYPE
from mangrove.transport.repository.survey_responses import SurveyResponse


class SurveyResponseService(object):
    def __init__(self, dbm, logger=None, feeds_dbm=None, admin_id=None):
        self.dbm = dbm
        self.logger = logger
        self.feeds_dbm = feeds_dbm
        self.admin_id = admin_id

    def _create_submission_log(self, transport_info, form_code, values):
        submission = Submission(self.dbm, transport_info, form_code, values=copy(values))
        submission.save()
        return submission

    def save_survey(self, form_code, values, reporter_names, transport_info, message, reporter_id=None,
                    additional_feed_dictionary=None):
        reporter = by_short_code(self.dbm, reporter_id, REPORTER_ENTITY_TYPE)
        submission = self._create_submission_log(transport_info, form_code, copy(values))
        survey_response = SurveyResponse(self.dbm, transport_info, form_code, copy(values), owner_uid=reporter.id,
                                         admin_id=self.admin_id or reporter_id)

        form_model = get_form_model_by_code(self.dbm, form_code)
        submission.update_form_model_revision(form_model.revision)
        survey_response.set_form(form_model)

        if form_model.is_inactive():
            raise InactiveFormModelException(form_model.form_code)

        #TODO : validate_submission should use form_model's bound values
        form_model.bind(values)
        cleaned_data, errors = form_model.validate_submission(values=values)

        form_submission = DataFormSubmission(form_model, cleaned_data, errors)
        feed_create_errors = None
        try:
            survey_response.set_answers(form_submission.short_code, values)
            if form_submission.is_valid:
                form_submission.save(self.dbm)

            submission.update(form_submission.saved, form_submission.errors, form_model.entity_question.code,
                              form_submission.short_code, form_submission.data_record_id, form_model.is_in_test_mode())
        except MangroveException as exception:
            submission.update(status=False, errors=exception.message, is_test_mode=form_model.is_in_test_mode())
            errors = exception.message
            raise
        finally:
            survey_response.set_status(errors)
            survey_response.create(form_submission.data_record_id)
            self.log_request(form_submission.saved, transport_info.source, message)
            try:
                if self.feeds_dbm:
                    builder = EnrichedSurveyResponseBuilder(self.dbm, survey_response, form_model, reporter_id,
                                                            additional_feed_dictionary)
                    event_document = builder.feed_document()
                    self.feeds_dbm._save_document(event_document)
            except Exception as e:
                feed_create_errors = 'error while creating feed doc for %s \n' % survey_response.id
                feed_create_errors += e.message + '\n'
                feed_create_errors += traceback.format_exc()
        return Response(reporter_names, submission.uuid, survey_response.uuid, form_submission.saved,
                        form_submission.errors, form_submission.data_record_id, form_submission.short_code,
                        form_submission.cleaned_data, form_submission.is_registration, form_submission.entity_type,
                        form_submission.form_model.form_code, feed_create_errors)


    def edit_survey(self, form_code, values, reporter_names, transport_info, message, survey_response,
                    additional_feed_dictionary=None, reporter_id=None):
        submission = self._create_submission_log(transport_info, form_code, copy(values))
        form_model = get_form_model_by_code(self.dbm, form_code)
        submission.update_form_model_revision(form_model.revision)

        if form_model.is_inactive():
            raise InactiveFormModelException(form_model.form_code)

        form = EditSurveyResponseForm(self.dbm, survey_response, form_model, values)
        try:
            if form.is_valid:
                reporter = by_short_code(self.dbm, reporter_id, REPORTER_ENTITY_TYPE)
                survey_response.owner_uid = reporter.id
                survey_response.modified_by = self.admin_id or reporter_id
                survey_response = form.save()
            submission.update(form.saved, form.errors, form.entity_question_code,
                              form.short_code, form.data_record_id, form_model.is_in_test_mode())
            try:
                feed_create_errors = None
                if self.feeds_dbm:
                    builder = EnrichedSurveyResponseBuilder(self.dbm, survey_response, form_model, reporter_id,
                                                            additional_feed_dictionary)
                    event_document = builder.update_event_document(self.feeds_dbm)
                    self.feeds_dbm._save_document(event_document)
            except Exception as e:
                feed_create_errors = 'error while editing feed doc for %s \n' % survey_response.id
                feed_create_errors += e.message + '\n'
                feed_create_errors += traceback.format_exc()

        except MangroveException as exception:
            submission.update(status=False, errors=exception.message, is_test_mode=form_model.is_in_test_mode())
            raise
        finally:
            self.log_request(form.saved, transport_info.source, message)
        return Response(reporter_names, submission.uuid, survey_response.uuid, form.saved,
                        form.errors, form.data_record_id, form.short_code,
                        form._cleaned_data, form.is_registration, form.entity_type,
                        form.form_model.form_code, feed_create_errors)

    def delete_survey(self, survey_response, reporter_id, additional_details):
        feed_delete_errors = None
        try:
            survey_response.void()
            form_model = get_form_model_by_code(self.dbm, survey_response.form_code)
            if self.feeds_dbm:
                feed_delete_errors = EnrichedSurveyResponseBuilder(self.dbm, survey_response, form_model, reporter_id,
                                                                   additional_details).delete_feed_document(
                    self.feeds_dbm)
        except MangroveException as e:
            return Response(errors=e.message, feed_error_message=feed_delete_errors)
        return Response(success=True, feed_error_message=feed_delete_errors)

    def log_request(self, status, source, message):
        if self.logger is not None:
            log_entry = "message: " + str(message) + "|source: " + source + "|"
            log_entry += "status: True" if status else "status: False"
            self.logger.info(log_entry)