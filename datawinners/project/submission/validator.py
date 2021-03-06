from collections import OrderedDict
from datawinners.entity.import_data import translate_errors
from mangrove.utils.types import is_empty


class SubmissionWorkbookRowValidator():

    def __init__(self, manager, form_model, project):
        self.manager = manager
        self.form_model = form_model
        self.project = project

    def validate_rows(self, parsed_rows):
        field_code_label_dict = self.form_model.get_field_code_label_dict()
        valid_rows, invalid_row_details = [], []
        row_count = 1
        for row in parsed_rows:
            row_count += 1
            if len([value for value in dict(row).values() if not is_empty(value)]) == 1:
                continue
            entity_key = self._get_entity_key()
            entity_answer = row.get(entity_key)

            errors = self._verify_uploaded_id(entity_key, entity_answer)
            cleaned_data, field_errors = self.form_model.validate_submission(values=row)
            errors.update(field_errors)
            errors_translated = translate_errors(items=errors.items(), question_dict=field_code_label_dict, question_answer_dict=row)
            invalid_row_details.append({"errors":errors_translated,"row_count":row_count}) if len(errors) > 0 else valid_rows.append(row)
        return valid_rows, invalid_row_details

    def _get_entity_key(self):
        for field in self.form_model.fields:
            if field.is_entity_field:
                return field.code

        return None

    def _verify_uploaded_id(self, q_code, imported_id):
        subject_ids, datasender_ids = self._get_subject_or_datasender_ids()
        errors = OrderedDict()
        if self.project.is_summary_project():
            if imported_id not in datasender_ids:
                errors.update({q_code: "The unique ID of the Data Sender does not match any existing Data Sender ID. Please correct and import again."})
        else:
            if imported_id not in subject_ids:
                errors.update({q_code: "The unique ID of the Subject does not match any existing Subject ID. Please correct and import again."})
        return errors

    def _get_subject_or_datasender_ids(self):
        subject_ids, datasender_ids = None, None
        if self.project.is_summary_project():
            datasender_ids = [ds['short_code'] for ds in self.project.get_data_senders(self.manager)]
        else:
            entity_type = self.project.entity_type
            start_key = [[entity_type]]
            end_key = [[entity_type], {}, {}]
            rows = self.manager.database.view("entity_name_by_short_code/entity_name_by_short_code", startkey=start_key,endkey=end_key).rows
            subject_ids = [item["key"][1] for item in rows]
        return subject_ids, datasender_ids




