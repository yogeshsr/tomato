# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import unittest
import time

from django.utils.unittest.case import SkipTest
from nose.plugins.attrib import attr

from framework.base_test import setup_driver, teardown_driver, BaseTest
from framework.utils.common_utils import by_css, by_id
from framework.utils.data_fetcher import fetch_, from_
from pages.adddatasenderspage.add_data_senders_page import AddDataSenderPage
from pages.alldatasenderspage.all_data_senders_locator import WEB_USER_BLOCK_EMAIL, GIVE_ACCESS_LINK
from pages.alluserspage.all_users_page import AllUsersPage
from pages.globalnavigationpage.global_navigation_page import GlobalNavigationPage
from pages.loginpage.login_page import LoginPage
from pages.warningdialog.delete_dialog import UserDeleteDialog, DataSenderDeleteDialog
from testdata.test_data import DATA_WINNER_LOGIN_PAGE, DATA_WINNER_SMS_TESTER_PAGE, DATA_WINNER_CREATE_DATA_SENDERS, DATA_WINNER_ALL_DATA_SENDERS_PAGE
from tests.logintests.login_data import VALID_CREDENTIALS
from tests.alldatasenderstests.all_data_sender_data import *
from pages.smstesterpage.sms_tester_page import SMSTesterPage
from pages.alldatasenderspage.all_data_senders_page import AllDataSendersPage
from tests.projects.datasenderstests.registered_datasenders_data import IMPORT_DATA_SENDER_TEMPLATE_FILENAME_EN, IMPORT_DATA_SENDER_TEMPLATE_FILENAME_FR
from pages.warningdialog.warning_dialog import WarningDialog
from tests.testsettings import UI_TEST_TIMEOUT


class TestAllDataSenders(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver = setup_driver(browser="phantom")
        LoginPage(cls.driver).load().do_successful_login_with(VALID_CREDENTIALS)
        cls.all_datasenders_page = AllDataSendersPage(TestAllDataSenders.driver)
        cls.datasender_id_with_web_access = cls.register_datasender(VALID_DATASENDER_WITH_WEB_ACCESS,
                                                                    id=TestAllDataSenders._create_id_for_data_sender())
        cls.datasender_id_without_web_access = cls.register_datasender(VALID_DATASENDER_WITHOUT_WEB_ACCESS,
                                                                       id=TestAllDataSenders._create_id_for_data_sender())
        cls.user_mobile_number = TestAllDataSenders.add_new_user(NEW_USER_DATA)
        cls.driver.go_to(DATA_WINNER_ALL_DATA_SENDERS_PAGE)
        cls.all_datasenders_page.wait_for_table_to_load()
        cls.all_datasenders_page.search_with(cls.user_mobile_number)
        cls.user_ID = cls.all_datasenders_page.get_cell_value(1, 3)

    @classmethod
    def tearDownClass(cls):
        teardown_driver(cls.driver)

    def setUp(self):
        self.all_datasenders_page.load()

    @classmethod
    def _create_id_for_data_sender(cls):
        return "allds" + random_number(4)


    @classmethod
    def register_datasender(cls, datasender_details, id=None):
        cls.driver.go_to(DATA_WINNER_ALL_DATA_SENDERS_PAGE)
        add_data_sender_page = cls.all_datasenders_page.navigate_to_add_a_data_sender_page()
        add_data_sender_page.enter_data_sender_details_from(datasender_details, unique_id=id)
        return add_data_sender_page.get_registered_datasender_id() if id is None else id

    @attr('functional_tests')
    def test_links(self):
        self.all_datasenders_page.check_links()

    @attr('functional_test')
    def test_successful_association_and_dissociation_of_data_sender(self):
        self.all_datasenders_page.search_with(self.datasender_id_without_web_access)
        self.assertEqual("", self.all_datasenders_page.get_project_names(self.datasender_id_without_web_access))
        self.all_datasenders_page.associate_datasender_to_projects(self.datasender_id_without_web_access,
                                                                   ["clinic test project1", "clinic test project"])
        self.driver.wait_until_element_is_not_present(UI_TEST_TIMEOUT, by_id("datasender_table_processing"))

        self.assertEqual("clinic test project, clinic test project1",
                         self.all_datasenders_page.get_project_names(self.datasender_id_without_web_access))
        self.all_datasenders_page.dissociate_datasender_from_project(self.datasender_id_without_web_access,
                                                                     "clinic test project1")
        self.driver.wait_until_element_is_not_present(UI_TEST_TIMEOUT, by_id("datasender_table_processing"))
        self.assertEqual("clinic test project",
                         self.all_datasenders_page.get_project_names(self.datasender_id_without_web_access))
        self.all_datasenders_page.dissociate_datasender_from_project(self.datasender_id_without_web_access,
                                                                     "clinic test project")
        self.driver.wait_until_element_is_not_present(UI_TEST_TIMEOUT, by_id("datasender_table_processing"))
        self.assertEqual("", self.all_datasenders_page.get_project_names(self.datasender_id_without_web_access))

    @attr('functional_test')
    def test_dissociate_ds_without_selecting_project(self):
        self.all_datasenders_page.search_with(self.datasender_id_without_web_access)
        self.all_datasenders_page.select_a_data_sender_by_id(self.datasender_id_without_web_access)
        self.all_datasenders_page.perform_datasender_action(DISSOCIATE)
        self.all_datasenders_page.click_confirm()
        self.assertEqual(self.all_datasenders_page.get_error_message(), ERROR_MSG_FOR_NOT_SELECTING_PROJECT)

    @attr('functional_test')
    def test_associate_ds_without_selecting_project(self):
        self.all_datasenders_page.search_with(self.datasender_id_without_web_access)
        self.all_datasenders_page.select_a_data_sender_by_id(self.datasender_id_without_web_access)
        self.all_datasenders_page.perform_datasender_action(ASSOCIATE)
        self.all_datasenders_page.click_confirm()
        self.assertEqual(self.all_datasenders_page.get_error_message(), ERROR_MSG_FOR_NOT_SELECTING_PROJECT)

    @attr('functional_test')
    def test_delete_data_sender(self):
        delete_datasender_id = TestAllDataSenders.register_datasender(DATA_SENDER_TO_DELETE,
                                                                      id=TestAllDataSenders._create_id_for_data_sender())
        self.all_datasenders_page.load()
        self.all_datasenders_page.search_with(delete_datasender_id)
        self.all_datasenders_page.delete_datasender(delete_datasender_id)
        DataSenderDeleteDialog(self.driver).ok()
        self.assertEqual(self.all_datasenders_page.get_delete_success_message(), DELETE_SUCCESS_TEXT)
        self.all_datasenders_page.search_with(delete_datasender_id)
        self.assertFalse(
            self.driver.is_element_present(self.all_datasenders_page.get_checkbox_selector_for_datasender_row(1)))
        self.assertEqual("No matching records found", self.all_datasenders_page.get_empty_table_result())

    @attr('functional_test')
    def test_search(self):
        self.all_datasenders_page.search_with("non_existent_DS")
        self.assertFalse(
            self.driver.is_element_present(self.all_datasenders_page.get_checkbox_selector_for_datasender_row(1)))
        self.assertEqual("No matching records found", self.all_datasenders_page.get_empty_table_result())
        self.assertEqual("0 to 0 of 0 Data Sender", self.all_datasenders_page.get_pagination_text())
        self.all_datasenders_page.search_with(self.datasender_id_without_web_access)
        self.assertEqual(self.datasender_id_without_web_access,
                         self.all_datasenders_page.get_cell_value(row=1, column=3),
                         msg="matching row does not have specified ID")
        self.assertFalse(
            self.driver.is_element_present(self.all_datasenders_page.get_checkbox_selector_for_datasender_row(2)),
            msg="More than expected number of rows present")
        self.assertEqual("1 to 1 of 1 Data Sender(s)", self.all_datasenders_page.get_pagination_text())

    @attr('functional_test')
    def test_the_datasender_template_file_downloaded(self):
        import_lightbox = self.all_datasenders_page.open_import_lightbox()
        self.assertEqual(IMPORT_DATA_SENDER_TEMPLATE_FILENAME_EN, import_lightbox.get_template_filename())
        import_lightbox.close_light_box()
        self.all_datasenders_page.switch_language("fr")
        self.all_datasenders_page.open_import_lightbox()
        self.assertEqual(IMPORT_DATA_SENDER_TEMPLATE_FILENAME_FR, import_lightbox.get_template_filename())


    @classmethod
    def add_new_user(cls, user_data):
        cls.driver.go_to(ALL_USERS_URL)
        all_users_page = AllUsersPage(cls.driver)
        add_user_page = all_users_page.navigate_to_add_user()
        add_user_page.add_user_with(user_data)
        cls.driver.wait_for_element(UI_TEST_TIMEOUT, by_css("div.success-message-box"), True)
        user_mobile_number = fetch_(MOBILE_PHONE, user_data)
        return user_mobile_number


    @attr('functional_test')
    def test_should_warn_and_not_delete_if_all_ds_selected_are_users(self):
        self.all_datasenders_page.search_with(self.user_ID)
        self.all_datasenders_page.delete_datasender(self.user_ID)
        delete_dialog = UserDeleteDialog(self.driver)
        self.assertRegexpMatches(delete_dialog.get_message(), ALL_DS_TO_DELETE_ARE_USER_MSG)
        delete_dialog.ok()

    @attr('functional_test')
    def test_should_warn_and_delete_only_DS_if_selected_are_users_and_DS(self):
        delete_datasender_id = TestAllDataSenders.register_datasender(DATA_SENDER_TO_DELETE)
        self.driver.go_to(DATA_WINNER_ALL_DATA_SENDERS_PAGE)
        self.all_datasenders_page.load()
        self.all_datasenders_page.search_with(fetch_(FIRST_NAME, NEW_USER_DATA))
        self.all_datasenders_page.click_checkall_checkbox()
        self.all_datasenders_page.perform_datasender_action(DELETE)
        DataSenderDeleteDialog(self.driver).ok()
        self.assertEqual(self.all_datasenders_page.get_delete_success_message(), DELETE_SUCCESS_TEXT)
        self.all_datasenders_page.search_with(delete_datasender_id)
        self.assertFalse(
            self.driver.is_element_present(self.all_datasenders_page.get_checkbox_selector_for_datasender_row(1)))
        self.all_datasenders_page.search_with(self.user_ID)

        self.assertTrue(
             self.driver.is_element_present(self.all_datasenders_page.get_checkbox_selector_for_datasender_row(1)))

    @attr('functional_test')
    def test_should_check_all_checkboxes_when_checking_checkall(self):
        self.all_datasenders_page.click_checkall_checkbox()
        all_ds_count = self.all_datasenders_page.get_datasenders_count()
        all_checked_ds_count = self.all_datasenders_page.get_checked_datasenders_count()
        self.assertEqual(all_ds_count, all_checked_ds_count)

        self.all_datasenders_page.click_checkall_checkbox()
        all_checked_ds_count = self.all_datasenders_page.get_checked_datasenders_count()
        self.assertEqual(all_checked_ds_count, 0)

    @attr("functional_test")
    def test_actions_menu(self):
        self.all_datasenders_page.click_action_button()
        self.assert_action_menu_when_no_datasender_selected()

        self.driver.find(self.all_datasenders_page.get_checkbox_selector_for_datasender_row(1)).click()
        self.all_datasenders_page.click_action_button()
        self.assert_action_menu_shown()
        self.assertFalse(self.all_datasenders_page.is_edit_disabled())
        self.assert_action_menu_when_datasender_selected()

        self.driver.find(self.all_datasenders_page.get_checkbox_selector_for_datasender_row(2)).click()
        self.all_datasenders_page.click_action_button()
        self.assert_action_menu_shown()
        self.assertTrue(self.all_datasenders_page.is_edit_disabled())
        self.assert_action_menu_when_datasender_selected()

    def assert_action_menu_when_datasender_selected(self):
        self.assertFalse(self.all_datasenders_page.is_make_web_user_disabled())
        self.assertFalse(self.all_datasenders_page.is_associate_disabled())
        self.assertFalse(self.all_datasenders_page.is_dissociate_disabled())
        self.assertFalse(self.all_datasenders_page.is_delete_disabled())

    def assert_action_menu_when_no_datasender_selected(self):
        self.assertTrue(self.all_datasenders_page.is_none_selected_shown())
        self.assertEquals("Select a Data Sender", self.all_datasenders_page.get_none_selected_text())

    def assert_action_menu_shown(self):
        self.assertFalse(self.all_datasenders_page.is_none_selected_shown())

    @attr("functional_test")
    def test_should_check_checkall_when_all_cb_are_checked(self):
        self.all_datasenders_page.click_checkall_checkbox()
        self.assertTrue(self.all_datasenders_page.is_checkall_checked())
        first_row_datasender = self.all_datasenders_page.get_checkbox_selector_for_datasender_row(1)
        self.driver.find(first_row_datasender).click()
        self.assertFalse(self.all_datasenders_page.is_checkall_checked())
        self.driver.find(first_row_datasender).click()
        self.assertTrue(self.all_datasenders_page.is_checkall_checked())

    @attr("functional_test")
    def test_should_show_updated_datasender_details_after_edit(self):
        self.all_datasenders_page.search_with(self.datasender_id_with_web_access)
        self.all_datasenders_page.select_a_data_sender_by_id(self.datasender_id_with_web_access)
        self.all_datasenders_page.select_edit_action()
        AddDataSenderPage(self.driver).enter_data_sender_details_from(EDITED_DATA_SENDER).navigate_to_datasender_page()
        self.all_datasenders_page.wait_for_table_to_load()
        self.all_datasenders_page.search_with(self.datasender_id_with_web_access)
        self.assertEqual(fetch_(NAME, EDITED_DATA_SENDER), self.all_datasenders_page.get_cell_value(1, 2))
        self.assertEqual(self.datasender_id_with_web_access, self.all_datasenders_page.get_cell_value(1, 3))
        location_appended_with_account_location = fetch_(COMMUNE, EDITED_DATA_SENDER) + ",Madagascar"
        self.assertEqual(location_appended_with_account_location, self.all_datasenders_page.get_cell_value(1, 4))
        self.assertEqual(fetch_(GPS, EDITED_DATA_SENDER), self.all_datasenders_page.get_cell_value(1, 5))
        self.assertEqual(fetch_(MOBILE_NUMBER, EDITED_DATA_SENDER), self.all_datasenders_page.get_cell_value(1, 6))


    @attr("functional_test")
    def test_should_give_web_and_smartphone_access(self):
        self.all_datasenders_page.search_with(self.datasender_id_without_web_access)
        self.assertFalse(self.all_datasenders_page.is_web_and_smartphone_device_checkmarks_present(
            self.datasender_id_without_web_access))
        self.all_datasenders_page.select_a_data_sender_by_id(self.datasender_id_without_web_access)
        email_address = fetch_(EMAIL_ADDRESS, VALID_DATASENDER_WITHOUT_WEB_ACCESS)
        self.all_datasenders_page.give_web_and_smartphone_access(email_address)
        self.all_datasenders_page.wait_for_table_to_load()
        self.assertEqual("Access to Web Submission has been given to your DataSenders.",
                         self.all_datasenders_page.get_success_message())
        self.all_datasenders_page.search_with(self.datasender_id_without_web_access)
        self.assertTrue(self.all_datasenders_page.is_web_and_smartphone_device_checkmarks_present(
            self.datasender_id_without_web_access))
        self.assertEqual(email_address, self.all_datasenders_page.get_cell_value(1, 7))

    @attr('functional_test')
    def test_should_not_able_to_use_other_datasender_mobile_number(self):
        self.all_datasenders_page.search_with('rep10')
        self.all_datasenders_page.select_a_data_sender_by_id('rep10')
        self.all_datasenders_page.select_edit_action()
        page = AddDataSenderPage(self.driver)
        page.enter_datasender_mobile_number("1234567890")
        page.click_submit_button()
        time.sleep(2)
        self.assertEqual(page.get_error_message(),
            u'Mobile Number Sorry, the telephone number 1234567890 has already been registered.')