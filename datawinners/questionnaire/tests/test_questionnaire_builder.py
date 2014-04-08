import unittest
from unittest.case import SkipTest
from mangrove.utils.test_utils.database_utils import safe_define_type, uniq

from mock import Mock, patch

from mangrove.bootstrap import initializer
from mangrove.datastore.database import DatabaseManager, get_db_manager, _delete_db_and_remove_db_manager
from mangrove.datastore.entity_type import define_type
from mangrove.errors.MangroveException import EntityTypeAlreadyDefined
from mangrove.form_model.field import TextField, IntegerField, SelectField, GeoCodeField, TelephoneNumberField, FieldSet
from mangrove.form_model.form_model import FormModel, LOCATION_TYPE_FIELD_NAME, get_form_model_by_code
from datawinners.questionnaire.questionnaire_builder import QuestionnaireBuilder, QuestionBuilder
from mangrove.form_model.validation import TextLengthConstraint, RegexConstraint, NumericRangeConstraint


FORM_CODE_2 = uniq("2")

FORM_CODE_1 = uniq("1")


class TestQuestionnaireBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = get_db_manager('http://localhost:5984/', uniq('mangrove-test'))
        initializer._create_views(cls.manager)
        cls.entity_type = ["HealthFacility", "Clinic"]
        safe_define_type(cls.manager, ["HealthFacility", "Clinic"])
        cls._create_form_model()

    @classmethod
    def tearDownClass(cls):
        _delete_db_and_remove_db_manager(cls.manager)

    @classmethod
    def _create_form_model(cls):
        question1 = TextField(name="entity_question", code="ID", label="What is associated entity",
                              entity_question_flag=True)
        question2 = TextField(name="question1_Name", code="Q1", label="What is your name",
                              defaultValue="some default value",
                              constraints=[TextLengthConstraint(5, 10), RegexConstraint("\w+")])
        cls.form_model = FormModel(cls.manager, entity_type=cls.entity_type, name="aids", label="Aids form_model",
                                   form_code=FORM_CODE_1, type='survey', fields=[question1, question2])
        cls.form_model__id = cls.form_model.save()

    def _create_summary_form_model(self):
        question1 = TextField(name="question1_Name", code="Q1", label="What is your name",
                              defaultValue="some default value",
                              constraints=[TextLengthConstraint(5, 10), RegexConstraint("\w+")],
        )
        question2 = IntegerField(name="Father's age", code="Q2", label="What is your Father's Age",
                                 constraints=[NumericRangeConstraint(min=15, max=120)])
        question3 = SelectField(name="Color", code="Q3", label="What is your favourite color",
                                options=[("RED", 1), ("YELLOW", 2)])
        self.summary_form_model = FormModel(self.manager, entity_type=["reporter"], name="aids",
                                            label="Aids form_model",
                                            form_code=FORM_CODE_2, type="survey",
                                            fields=[question1, question2, question3])
        self.summary_form_model__id = self.summary_form_model.save()

    def test_should_update_questionnaire_when_entity_type_is_not_reporter(self):
        #self._create_form_model()
        form_model = self.manager.get(self.form_model__id, FormModel)
        post = [{"title": "What is your age", "code": "age", "type": "integer", "choices": [],
                 "is_entity_question": False,
                 "range_min": 0, "range_max": 100}]

        QuestionnaireBuilder(form_model, self.manager).update_questionnaire_with_questions(post)
        self.assertEquals(1, len(form_model.fields))


    def test_should_update_questionnaire_when_entity_type_is_reporter(self):
        self._create_summary_form_model()
        post = [{"title": "q1", "type": "text", "choices": [], "is_entity_question": False, "code": "q1",
                 "min_length": 1, "max_length": ""},
                {"title": "q2", "type": "integer", "choices": [], "is_entity_question": False, "code": "code",
                 "range_min": 0, "range_max": 100},
                {"title": "q3", "type": "select", "code": "code", "choices": [{"value": {"val": "c1"}}, {"value": {"val": "c2"}}],
                 "is_entity_question": False},
                {"title": "q4", "type": "field_set", "code": "q4", "is_entity_question": False, "is_entity": True,
                 "fields": []},
                {"title": "q5", "type": "field_set", "code": "q5", "is_entity_question": False, "is_entity": False,
                 "fields": []}
        ]
        summary_form_model = self.manager.get(self.summary_form_model__id, FormModel)
        QuestionnaireBuilder(summary_form_model, self.manager).update_questionnaire_with_questions(post)
        self.assertEqual(6, len(summary_form_model.fields))
        self.assertEqual('eid', summary_form_model.fields[0].code)
        self.assertEqual('q1', summary_form_model.fields[1].code)
        self.assertEqual('q2', summary_form_model.fields[2].code)
        self.assertEqual('q3', summary_form_model.fields[3].code)
        self.assertEqual('q4', summary_form_model.fields[4].code)
        self.assertEqual(True, summary_form_model.fields[4].is_entity)
        self.assertEqual(None, summary_form_model.fields[5].is_entity)
        entity_id_question = summary_form_model.entity_question
        self.assertEqual('eid', entity_id_question.code)
        self.assertEqual('I am submitting this data on behalf of', entity_id_question.name)
        self.assertEqual("Choose Data Sender from the list.", entity_id_question.instruction)

    def test_should_no_snapshot_when_questionnaire_first_created(self):
        #self._create_form_model()
        form_model = self.manager.get(self.form_model__id, FormModel)
        self.assertEqual(0, len(form_model.snapshots))

    def test_should_save_snapshots_when_questionnaires_field_modified(self):
        #self._create_form_model()
        form_model = get_form_model_by_code(self.manager, FORM_CODE_1)
        original_fields = form_model._doc.json_fields
        revision = form_model._doc['_rev']

        post = [
            {"title": "q1", "type": "text", "choices": [], "is_entity_question": False, "code": "q1", "min_length": 1,
             "max_length": ""},
            {"title": "q2", "type": "integer", "choices": [], "is_entity_question": False, "code": "q2", "range_min": 0,
             "range_max": 100}]
        QuestionnaireBuilder(form_model, self.manager).update_questionnaire_with_questions(post)
        form_model.save()
        form_model = get_form_model_by_code(self.manager, FORM_CODE_1)

        self.assertEqual(1, len(form_model.snapshots))
        self.assertEqual(revision, form_model.snapshots.keys()[-1])
        expect = [(each['code'], each['label']) for each in original_fields]
        self.assertListEqual(expect, [(each.code, each.label) for each in form_model.snapshots[revision]])

    @SkipTest #todo Should check for changed fields before creating snapshot
    def test_should_not_save_snapshots_when_questionnaires_field_not_changed(self):
        form_model = get_form_model_by_code(self.manager, FORM_CODE_1)
        snapshots_before_modification = len(form_model.snapshots)

        post = [
            {"title": "What is associated entity", "type": "text",
             "is_entity_question": True, "code": "ID", "name": "entity_question"},
            {"title": "What is your name", "type": "text",
             "is_entity_question": False, "code": "Q1", "range_min": 5, "range_max": 10}]
        QuestionnaireBuilder(form_model, self.manager).update_questionnaire_with_questions(post)
        form_model.save()
        form_model = get_form_model_by_code(self.manager, FORM_CODE_1)

        self.assertEqual(snapshots_before_modification, len(form_model.snapshots))


class TestQuestionBuilder(unittest.TestCase):
    def setUp(self):
        self.dbm = Mock(spec=DatabaseManager)
        self.question_builder = QuestionBuilder(self.dbm)

    def test_creates_questions_from_dict(self):
        post = [{"title": "q1", "description": "desc1", "type": "text", "choices": [],
                 "is_entity_question": True, "min_length": 1, "max_length": 15},
                {"title": "q2", "description": "desc2", "type": "integer", "choices": [],
                 "is_entity_question": False, "range_min": 0, "range_max": 100},
                {"title": "q3", "description": "desc3", "type": "select",
                 "choices": [{"value": {"text": "value", "val": "c1"}}, {"value": {"text": "value", "val": "c2"}}],
                 "is_entity_question": False},
                {"title": "q4", "description": "desc4", "type": "select1",
                 "choices": [{"value": {"text": "value", "val": "c1"}}, {"value": {"text": "value", "val": "c2"}}],
                 "is_entity_question": False},
                {"title": "q5", "description": "desc4", "type": "text"},
                {"title": "q6", "description": "desc6", "type": "field_set", "fields": []},
                {"title": "q7", "description": "desc7", "type": "field_set", "is_entity": True, "fields":[]}
        ]
        q1 = self.question_builder.create_question(post[0], "q1")
        q2 = self.question_builder.create_question(post[1], "q1")
        q3 = self.question_builder.create_question(post[2], "q1")
        q4 = self.question_builder.create_question(post[3], "q1")
        q5 = self.question_builder.create_question(post[4], "q1")
        q6 = self.question_builder.create_question(post[5], "q1")
        q7 = self.question_builder.create_question(post[6], "q1")
        self.assertIsInstance(q1, TextField)
        self.assertIsInstance(q2, IntegerField)
        self.assertIsInstance(q3, SelectField)
        self.assertIsInstance(q4, SelectField)
        self.assertIsInstance(q5, TextField)
        self.assertIsInstance(q6, FieldSet)
        self.assertIsInstance(q7, FieldSet)
        self.assertEquals(q1._to_json_view()["length"], {"min": 1, "max": 15})
        self.assertEquals(q2._to_json_view()["range"], {"min": 0, "max": 100})
        self.assertEquals(q3._to_json_view()["type"], "select")
        self.assertEquals(q4._to_json_view()["type"], "select1")
        self.assertEquals(q5._to_json_view()["type"], "text")
        self.assertEquals(q6._to_json_view()["type"], "field_set")
        self.assertEquals(q6.is_entity, None)
        self.assertEquals(q7._to_json_view()["type"], "field_set")
        self.assertEquals(q7.is_entity, True)

    def test_should_populate_name_as_title_if_name_is_not_present(self):
        post = {"title": "q2", "type": "text"}
        q1 = self.question_builder.create_question(post, code="q1")
        self.assertEqual('q2', q1.name)

    def test_should_honour_name(self):
        post = {"name": "name", "title": 'q2', "type": "text"}
        q1 = self.question_builder.create_question(post, code="q1")
        self.assertEqual('name', q1.name)

    def test_should_create_integer_question_with_no_max_constraint(self):
        post = [{"title": "q2", "type": "integer", "choices": [], "is_entity_question": False,
                 "range_min": 0, "range_max": ""}]
        q1 = self.question_builder.create_question(post[0], code="q1")
        self.assertEqual(None, q1.constraints[0].max)
        self.assertEqual(0, q1.constraints[0].min)

    def test_should_create_geo_code_question(self):
        CODE = "lc3"
        LABEL = "what is your location"
        TYPE = "geocode"
        post = {"title": LABEL, "type": TYPE}

        geo_code_field = self.question_builder.create_question(post, code=CODE)

        self.assertIsInstance(geo_code_field, GeoCodeField)
        self.assertEqual(CODE, geo_code_field.code)

    def test_should_create_select1_question(self):
        LABEL = "q3"
        TYPE = "select1"
        choices = [{"value": {"text": "first", "val": "c1"}}, {"value": {"text": "second", "val": "c2"}}]

        post = {"title": LABEL, "type": TYPE, "choices": choices}

        select1_question = self.question_builder.create_question(post, code="q1")

        self.assertEqual(LABEL, select1_question.label)
        self.assertEqual(2, len(select1_question.options))
        self.assertEqual("c1", select1_question.options[0]['val'])
        self.assertEqual("c2", select1_question.options[1]['val'])

    def test_should_create_select_question(self):
        LABEL = "q3"
        TYPE = "select"
        choices = [{"value":{"text": "first", "val": "c1"}}, {"value":{"text": "second", "val": "c2"}}]

        post = {"title": LABEL, "type": TYPE, "choices": choices}

        select_question = self.question_builder.create_question(post, code="q1")

        self.assertEqual(LABEL, select_question.label)
        self.assertEqual(2, len(select_question.options))
        self.assertEqual("c1", select_question.options[0]['val'])
        self.assertEqual("c2", select_question.options[1]['val'])

    def test_should_create_date_question(self):
        LABEL = "q3"
        TYPE = "date"

        date_format = "dd.mm.yyyy"
        post = {"title": LABEL, "type": TYPE, "date_format": date_format}

        date_question = self.question_builder.create_question(post, "q1")

        self.assertEqual(LABEL, date_question.label)
        self.assertEqual(date_format, date_question.date_format)

    def test_should_create_text_question_with_no_max_length_and_min_length(self):
        post = [{"title": "q1", "type": "text", "choices": [], "is_entity_question": True,
                },
                {"title": "q2", "type": "integer", "choices": [], "is_entity_question": False,
                 "range_min": 0, "range_max": 100},
                {"title": "q3", "type": "select", "choices": [{"value": "c1"}, {"value": "c2"}],
                 "is_entity_question": False}
        ]
        q1 = self.question_builder.create_question(post[0], "q1")
        self.assertEqual(q1.constraints, [])
        self.assertEqual(q1.label, 'q1')

    def test_should_create_text_question_for_french_language(self):
        post = [{"title": "q1", "type": "text", "choices": [], "is_entity_question": True,
                },
                {"title": "q2", "type": "integer", "choices": [], "is_entity_question": False,
                 "range_min": 0, "range_max": 100},
                {"title": "q3", "type": "select", "choices": [{"value": "c1"}, {"value": "c2"}],
                 "is_entity_question": False}
        ]
        q1 = self.question_builder.create_question(post[0], code="q1")
        self.assertEqual(q1.constraints, [])
        self.assertEqual(q1.label, 'q1')

    def test_should_create_telephone_number_question(self):
        LABEL = "q3"
        TYPE = "telephone_number"

        post = {"title": LABEL, "type": TYPE}

        select_question = self.question_builder.create_question(post, code="q1")

        self.assertIsInstance(select_question, TelephoneNumberField)

    def test_should_create_location_question(self):
        LABEL = "q3"
        TYPE = "list"

        post = {"title": LABEL, "type": TYPE}

        select_question = self.question_builder.create_question(post, code="q1")
        self.assertEqual(LOCATION_TYPE_FIELD_NAME, select_question.name)