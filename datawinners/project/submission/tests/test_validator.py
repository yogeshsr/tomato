from unittest import TestCase, SkipTest
from mock import Mock, patch, MagicMock
from datawinners.project.submission.validator import SubmissionWorkbookRowValidator


class TestImportSubmissionValidator(TestCase):

    @SkipTest
    def test_should_return_valid_rows(self):
        form_model_mock = Mock()
        form_model_mock.validate_submission.return_value = ([],[])
        validator = SubmissionWorkbookRowValidator(Mock(), form_model_mock)
        parsed_rows = [("form_code",{}), ("form_code",{})]

        valid_rows, invalid_rows = validator.validate_rows(parsed_rows)

        self.assertEqual(len(valid_rows), 2)
        self.assertEqual(len(invalid_rows), 0)

    @SkipTest
    def test_should_return_invalid_rows(self):
        form_model_mock, project_mock = MagicMock(), MagicMock()
        form_model_mock.form_fields = []

        form_model_mock.validate_submission.return_value = ([],[{"error":"error_msg"}])
        validator = SubmissionWorkbookRowValidator(Mock(), form_model_mock, project_mock)
        parsed_rows = [("form_code",{}), ("form_code",{})]

        valid_rows, invalid_rows = validator.validate_rows(parsed_rows)

        self.assertEqual(len(valid_rows), 0)
        self.assertEqual(len(invalid_rows), 2)