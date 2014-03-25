from collections import OrderedDict
import unittest
from datawinners.blue.xform_submission_exporter import AdvanceSubmissionFormatter


class TestXFormSubmissionExporter(unittest.TestCase):

    def test_should_tabulate_header_and_submissions_rows(self):
        family_dict = OrderedDict({'name': {'type': 'text', 'label': 'Name'}})
        family_dict.update({'age': {'type': 'text', 'label': 'Age'}})

        columns = OrderedDict([('ds_id', {'label': 'Datasender Id'}),
                               ('uuid1_family',
                                {'fields': family_dict, 'type': 'field_set', 'label': 'Family'}),
                               ('uuid1_city', {'type': 'text', 'label': 'City'})])
        # correct the question to represent correct hierarchy
        submission_list = [{'uuid1_family': '[{"name": "ram", "age":"20"}, {"name": "shyam", "age":"25"}]',
                            'ds_id': 'rep276', 'uuid1_city': 'Pune'},
                           {'uuid1_family': '[{"name": "maya", "age":"20"}, {"name": "rita", "age":"25"}]',
                            'ds_id': 'rep277', 'uuid1_city': 'Bangalore'}]

        expected_header = ['Datasender Id', 'City', '_index', '_parent_index']
        expected_family_header = ['Name', 'Age', '_index', '_parent_index']

        main_submission_rows = [['rep276', 'Pune', 1],
                                ['rep277', 'Bangalore', 2]]
        repeat_family_rows = [['ram', '20', '', 1], ['shyam', '25', '', 1], ['maya', '20', '', 2],
                              ['rita', '25', '', 2]]

        # headers = {'main':[h1,h2...], 'repeat_1': [r1,r2,...]...}
        # data = {'main':[[row_1],[row_2]...], 'repeat': [[row_1],[row_2]...]}
        # row = ['name','age',...]


        headers, data_rows_dict = AdvanceSubmissionFormatter(columns).format_tabular_data(submission_list)

        self.assertEqual(expected_header, headers['main'])
        self.assertEqual(expected_family_header, headers['family'])

        self.assertEqual(main_submission_rows, data_rows_dict['main'])
        self.assertEqual(repeat_family_rows, data_rows_dict['family'])

        # wb = xlwt.Workbook()
        # for book_name, header_row in headers.items():
        #     workbook_add_sheet(wb, [header_row] + data_rows_dict[book_name], book_name)
        # wb.save('exported.xls')

    def test_repeat_inside_repeat_submission_data_should_be_tabulated(self):
            pass