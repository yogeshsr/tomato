#vim: ai ts=4 sts=4 et sw=4 encoding=utf-8


#  This is an integration test.
# Send sms, parse and save.
import random
from string import upper
from time import mktime
import unittest
import datetime
from couchdb.design import ViewDefinition
from mangrove.bootstrap import initializer
from mangrove.bootstrap.views import view_js
from mangrove.datastore.database import get_db_manager, _delete_db_and_remove_db_manager
from mangrove.datastore.documents import SubmissionLogDocument, DataRecordDocument
from mangrove.datastore.entity import get_by_short_code, create_entity
from mangrove.errors.MangroveException import  DataObjectAlreadyExists, EntityTypeDoesNotExistsException,\
 DataObjectNotFound, FormModelDoesNotExistsException
from mangrove.form_model.field import TextField, IntegerField, SelectField, ShortCodeField
from mangrove.form_model.form_model import FormModel, NAME_FIELD, MOBILE_NUMBER_FIELD, MOBILE_NUMBER_FIELD_CODE,\
SHORT_CODE, ENTITY_TYPE_FIELD_CODE, get_form_model_by_code,EntityFormModel
from mangrove.form_model.validation import NumericRangeConstraint, TextLengthConstraint
from mangrove.utils.test_utils.database_utils import safe_define_type, uniq, ut_reporter_id
from mangrove.transport.player.player import SMSPlayer
from mangrove.transport.contract.transport_info import TransportInfo
from mangrove.transport.contract.request import Request
from mangrove.datastore.cache_manager import get_cache_manager

class LocationTree(object):
    def get_location_hierarchy_for_geocode(self, lat, long ):
        return ['madagascar']

    def get_centroid(self, location_name, level):
        return 60, -12

    def get_location_hierarchy(self, lowest_level_location_name):
        return [u'arantany']

FORM_CODE = "abc"


def create_db(name):
    dbm = get_db_manager('http://localhost:5984/', name)
    views = []
    for v in view_js.keys():
        funcs = view_js[v]
        map = (funcs['map'] if 'map' in funcs else None)
        reduce = (funcs['reduce'] if 'reduce' in funcs else None)
        views.append(ViewDefinition(v, v, map, reduce))

    ViewDefinition.sync_many(dbm.database, views)
    return dbm


class TestShouldSaveSMSSubmission(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dbm = create_db(uniq('mangrove-test'))
        initializer.initial_data_setup(cls.dbm)

        safe_define_type(cls.dbm, ["dog"])
        cls.entity_type = ["healthfacility", "clinic"]
        safe_define_type(cls.dbm, cls.entity_type)

        cls.entity_short_code = "cli" + str(int(random.random()*10000))
        cls.entity = create_entity(cls.dbm, entity_type=cls.entity_type,
            location=["India", "Pune"], aggregation_paths=None, short_code=cls.entity_short_code,
        )
        cls.entity.save()

        cls.data_record_id = cls.entity.add_data(data=[("Name", "Ruby")],
            submission=dict(submission_id="1"))

        cls.reporter_id = "rep" + str(int(random.random()*10000))
        cls.reporter = create_entity(cls.dbm, entity_type=["reporter"],
            location=["India", "Pune"], aggregation_paths=None, short_code=cls.reporter_id,
        )
        cls.reporter.save()

        cls.phone_number = str(int(random.random() * 10000000))
        cls.reporter.add_data(data=[(MOBILE_NUMBER_FIELD, cls.phone_number),
            (NAME_FIELD, "Test_reporter")], submission=dict(submission_id="2"))

        question1 = ShortCodeField(name="entity_question", code="EID", label="What is associated entity",constraints=[TextLengthConstraint(min=1, max=20)])
        question2 = TextField(name="Name", code="NAME", label="Clinic Name",
            defaultValue="some default value",
            constraints=[TextLengthConstraint(4, 15)], required=False)
        question3 = IntegerField(name="Arv stock", code="ARV", label="ARV Stock",
            constraints=[NumericRangeConstraint(min=15, max=120)], required=False)
        question4 = SelectField(name="Color", code="COL", label="Color",
            options=[("RED", 'a'), ("YELLOW", 'a')], required=False)

        try:
            cls.form_model = get_form_model_by_code(cls.dbm, "clinic")
        except FormModelDoesNotExistsException:
            cls.form_model = EntityFormModel(cls.dbm, entity_type=cls.entity_type, name="aids", label="Aids form_model",
                form_code="clinic",  fields=[question1, question2, question3], is_registration_model=True)
            cls.form_model.add_field(question4)
            cls.form_model.save()
        cls.submission_handler = None
        cls.sms_player = SMSPlayer(cls.dbm, LocationTree())
        cls.sms_ordered_message_player = SMSPlayer(cls.dbm, LocationTree())

    @classmethod
    def tearDownClass(cls):
        _delete_db_and_remove_db_manager(cls.dbm)
        get_cache_manager().flush_all()

    def send_sms(self,text, player = None):
        player = player or self.sms_player
        transport_info = TransportInfo(transport="sms", source=self.phone_number, destination="5678")
        response = player.accept(Request(message=text, transportInfo=transport_info))
        return response



    def test_should_give_error_for_wrong_integer_value(self):
        text = "clinic .EID %s .ARV 150 " % self.entity.short_code
        response = self.send_sms(text)
        self.assertFalse(response.success)
        self.assertEqual(len(response.errors), 1)

    def test_should_give_error_for_wrong_text_value(self):
        text = "clinic .EID %s .NAME ABC" % self.entity.short_code

        response = self.send_sms(text)
        self.assertFalse(response.success)
        self.assertEqual(len(response.errors), 1)


    def test_should_register_new_entity(self):
        message1 = """reg .t  dog .n  Diégo–Suarez .l  Diégo–Suarez .g  -12.35  49.3  .d This is a Clinic in
        Diégo–Suarez .m 87654325
        """
        response = self.send_sms(message1)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.datarecord_id)
        expected_short_code = response.short_code
        self.assertTrue(response.short_code.startswith("dog"))
        self.assertEqual(response.short_code, expected_short_code)
        a = get_by_short_code(self.dbm, expected_short_code, ["dog"])
        self.assertEqual(a.short_code, expected_short_code)

        short_code = "bud" + str(int(random.random()*1000))
        text = "reg .N buddy .S %s .T dog .G 80 80 .D its a dog! .M 45557" % short_code

        response = self.send_sms(text)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.datarecord_id)
        self.assertEqual(response.short_code, short_code, ["dog"])
        dog1 = get_by_short_code(self.dbm, short_code, ["dog"])
        self.assertIsNotNone(dog1)
        dog1.delete()

        text = "reg .N buddy2 .T dog .L 80 80 .D its another dog! .M 78541"

        response = self.send_sms(text)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.datarecord_id)
        expected_short_code = response.short_code
        self.assertTrue(response.short_code.startswith("dog"))
        dog2 = get_by_short_code(self.dbm, expected_short_code, ["dog"])
        self.assertIsNotNone(dog2)
        self.assertEquals(dog2.value(MOBILE_NUMBER_FIELD), "78541")
        dog2.delete()

    def test_should_return_error_for_registration_having_invalid_geo_data(self):
        INVALID_LATITUDE = 380
        text = "reg .N buddy2 .T dog .G %s 80 .D its another dog! .M 78541" % (INVALID_LATITUDE,)

        response = self.send_sms(text)
        self.assertFalse(response.success)
        self.assertEqual({'g': 'Invalid GPS value.'}, response.errors)

        INVALID_LONGITUDE = -184
        text = "reg .N buddy2 .T dog .G 80 %s .D its another dog! .M 78541" % (INVALID_LONGITUDE,)

        response = self.send_sms(text)
        self.assertFalse(response.success)
        self.assertEqual({'g': 'Invalid GPS value.'}, response.errors)

    def test_should_throw_error_if_entity_with_same_short_code_exists(self):
        text = "reg .N buddy2 .S %s .T dog .L 80 80 .D its a dog! .M 123456" %self.reporter_id
        self.send_sms(text)
        with self.assertRaises(DataObjectAlreadyExists):
            self.send_sms(text)

    def test_should_throw_error_if_reporter_with_same_phone_number_exists(self):
        text = "reg .N buddy2 .T reporter .L 80 80 .M %s" % self.phone_number
        response = self.send_sms(text)
        self.assertFalse(response.success)
        self.assertIn('m', response.errors)

    def test_should_throw_error_if_mobile_phone_is_in_weird_pattern(self):
        text = "reg .N buddy .T reporter .G 80 80 .M 1234@5678"
        response = self.send_sms(text)
        self.assertFalse(response.success)
        self.assertTrue(response.errors.get('m') is not None)

    def test_should_throw_error_if_mobile_phone_is_too_long(self):
        text = "reg .N buddy .T reporter .G 80 80 .M 1234567889898989898989812312"
        response = self.send_sms(text)
        assert(response.success is False)
        self.assertTrue(response.errors.get('m') is not None)

    def test_should_throw_error_if_reporter_registration_submission_has_no_mobile_number(self):
        text = "reg .N buddy2 .T reporter .L 80 80"
        response = self.send_sms(text)
        self.assertFalse(response.success)
        self.assertTrue(MOBILE_NUMBER_FIELD_CODE in response.errors)

    def test_should_throw_error_if_entityType_doesnt_exist(self):
        with self.assertRaises(EntityTypeDoesNotExistsException):
            text = "reg .N buddy1 .S DOG3 .T cat .L 80 80 .D its another dog! .M 1234567"
            self.send_sms(text)

    def test_entity_type_is_case_insensitive_in_registration(self):
        text = "reg .n buddy .T DOG .G 80 80 .M 123456"
        response = self.send_sms(text)
        self.assertTrue(response.success)
        self.assertEquals(["dog"], response.entity_type)

    def test_should_accept_unicode_submissions(self):
        text = "reg .s agra .n Agra .m 080456 .t clinic .g 45 56"
        with self.assertRaises(EntityTypeDoesNotExistsException):
            self.send_sms(text)

    def test_should_accept_unicode_submissions_and_invalidate_wrong_GPS(self):
        text = "reg .s Agra .n Agra .m 080 .t clinic .g 45O 56"
        self.assertEqual(False, self.send_sms(text).success)

    def test_should_reject_registration_sms_if_type_not_provided(self):
        text = "reg .s Agra .n Agra .m 080 .g 45 56"
        response = self.send_sms(text)
        self.assertFalse(response.success)
        self.assertTrue('t' in response.errors)

    def test_should_register_entity_with_geo_code(self):
        message1 = """reg .t dog .n Dog in Diégo–Suarez .g -12.35  49.3  .d This is a Dog in
        Diégo–Suarez .m 87654325
        """
        response = self.send_sms(message1)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.datarecord_id)
        expected_short_code = response.short_code
        self.assertTrue(response.short_code.startswith("dog"))
        dog = get_by_short_code(self.dbm, expected_short_code, ["dog"])
        self.assertEqual([-12.35, 49.3], dog.geometry.get("coordinates"))

    def test_should_register_entity_with_geocode_if_only_location_provided(self):
        message1 = """reg .t dog .n Dog in AMPIZARANTANY .l AMPIZARANTANY .d This is a Dog in
        AMPIZARANTANY . m 87654325
        """
        response = self.send_sms(message1)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.datarecord_id)
        self.assertTrue(response.short_code.startswith("dog"))
        dog = get_by_short_code(self.dbm, response.short_code, ["dog"])
        self.assertEqual([-12, 60], dog.geometry.get("coordinates"))

    def test_should_register_entity_with_geocode_and_location_provided(self):
        message1 = """reg .t dog .n Dog in AMPIZARANTANY .l ARANTANY .g 10 10 .d This is a Dog in
        AMPIZARANTANY .m 87654325
        """
        response = self.send_sms(message1)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.datarecord_id)
        expected_short_code = response.short_code
        self.assertTrue(response.short_code.startswith("dog"))
        dog = get_by_short_code(self.dbm, expected_short_code, ["dog"])
        self.assertEqual([10, 10], dog.geometry.get("coordinates"))
        self.assertEqual([u'arantany'], dog.location_path)

    def test_should_delete_entity_instance_by_sms(self):
        text = "reg .n buddy .T DOG .G 80 80 .M 123456"
        response = self.send_sms(text)
        rep_id = response.short_code
        entity = get_by_short_code(self.dbm, rep_id, ["dog"])
        self.assertFalse(entity.is_void())
        message = 'delete dog %s' %rep_id
        response = self.send_sms(message, self.sms_ordered_message_player)
        self.assertTrue(response.success)
        with self.assertRaises(DataObjectNotFound):
            get_by_short_code(self.dbm, rep_id, ["dog"])

    def test_should_throw_error_if_deleting_entity_that_does_not_exist(self):
        with self.assertRaises(DataObjectNotFound):
            get_by_short_code(self.dbm, 'nonexistingreporter', ["reporter"])
        message = 'delete reporter nonexistingreporter'
        response = self.send_sms(message, self.sms_ordered_message_player)
        self.assertFalse(response.success)
        self.assertTrue(SHORT_CODE in response.errors)
        self.assertTrue(ENTITY_TYPE_FIELD_CODE in response.errors)

    def _tomorrow(self):
        oneDay = datetime.timedelta(days=1)
        tomorrow = datetime.datetime.now() + oneDay
        return int(mktime(tomorrow.timetuple())) * 1000

    def test_entity_id_with_more_than_20_chars_for_submission(self):
        response = self.send_sms("clinic 012345678901234567891", self.sms_ordered_message_player)
        self.assertEqual("Answer 012345678901234567891 for question EID is longer than allowed.",
                         response.errors['EID'])
