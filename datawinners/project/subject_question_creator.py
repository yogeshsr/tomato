from django import forms
from django.forms.fields import ChoiceField
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext
from datawinners.entity.import_data import load_all_subjects_of_type
from datawinners.utils import translate, get_text_language_by_instruction


class SubjectQuestionFieldCreator(object):
    def __init__(self, dbm, project, project_subject_loader=None):
        #for testing
        self.project_subject_loader = load_all_subjects_of_type if project_subject_loader is None else project_subject_loader
        self.project = project
        self.dbm = dbm

    def create(self, subject_field):
        reporter_entity_type = 'reporter'
        if self.project.is_on_type(reporter_entity_type):
            return self._data_sender_choice_fields(subject_field)
        return self._subjects_choice_fields(subject_field)

    def create_code_hidden_field(self, subject_field):
        return {'entity_question_code': forms.CharField(required=False, widget=HiddenInput, label=subject_field.code)}

    def _get_choice_field(self, data_sender_choices, subject_field, help_text):
        subject_choice_field = ChoiceField(required=subject_field.is_required(), choices=data_sender_choices,
                                           label=subject_field.name,
                                           initial=subject_field.value, help_text=help_text)
        subject_choice_field.widget.attrs['class'] = 'subject_field'
        return subject_choice_field

    def _data_sender_choice_fields(self, subject_field):
        data_senders = self.project.get_data_senders(self.dbm)
        data_sender_choices = self._get_all_choices(data_senders)
        return self._get_choice_field(data_sender_choices, subject_field, help_text=subject_field.instruction)

    def _build_subject_choice_data(self, subjects, key_list):
        values = map(lambda x: x["cols"] + [x["short_code"]], subjects)
        key_list.append('unique_id')

        return [dict(zip(key_list, value_list)) for value_list in values]

    def _subjects_choice_fields(self, subject_field):
        subjects, fields, label = self.project_subject_loader(self.dbm, type=self.project.entity_type)
        subject_data = self._build_subject_choice_data(subjects, fields)
        all_subject_choices = map(self._data_to_choice, subject_data)
        language = get_text_language_by_instruction(subject_field.instruction)
        instruction_for_subject_field = translate("Choose Subject from this list.", func=ugettext, language=language)
        return self._get_choice_field(all_subject_choices, subject_field, help_text=instruction_for_subject_field)

    def get_key(self, subject):
        return subject['unique_id']

    def get_value(self, subject):
        return subject['name'] + '  (' + subject['short_code'] + ')'

    def _data_to_choice(self, subject):
        return self.get_key(subject), self.get_value(subject)

    def _get_all_choices(self, entities):
        return [(entity['short_code'], entity['name'] + '  (' + entity['short_code'] + ')') for entity in entities]