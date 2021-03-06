from pages.broadcastSMSpage.broadcast_sms_locator import *
from pages.page import Page

class BroadcastSmsPage(Page):
    def __init__(self, driver):
        Page.__init__(self, driver)

    def write_sms_content(self, sms_data):
        self.driver.find_text_box(SMS_CONTENT_TB).enter_text(sms_data)

    def click_send(self):
         self.driver.find(SEND_BROADCAST_SMS_BTN).click()

    def get_sms_content(self):
        return self.driver.find_text_box(SMS_CONTENT_TB).get_attribute("value")

    def choose_type_other_people(self, other_numbers=None):
        self.driver.find(SEND_TO_DDCL).click()
        self.driver.find(OTHER_PEOPLE_OPTION_DDCL).click()
        if other_numbers is not None:
            self.driver.find_text_box(SEND_TO_TB).enter_text(other_numbers)

    def is_other_people_help_text_visible(self):
        return self.driver.find(OTHER_PEOPLE_HELP_TEXT).is_displayed()

    def get_other_people_number_error(self):
        return self.driver.find(OTHER_PEOPLE_ERROR_TEXT_BY_CSS).text

    def is_warning_shown(self):
        return self.driver.find(by_id("more_people_warning")).is_displayed()