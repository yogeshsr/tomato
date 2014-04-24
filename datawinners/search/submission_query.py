import elasticutils
from datawinners.search.filters import SubmissionDateRangeFilter, ReportingDateRangeFilter
from datawinners.search.submission_headers import HeaderFactory
from datawinners.settings import ELASTIC_SEARCH_URL
from datawinners.search.query import QueryBuilder, Query
from mangrove.form_model.field import ImageField
from mangrove.form_model.form_model import get_field_by_attribute_value


class SubmissionQueryBuilder(QueryBuilder):
    def __init__(self, form_model=None):
        QueryBuilder.__init__(self)
        self.form_model = form_model

    def get_query(self, database_name, *doc_type):
        return elasticutils.S().es(urls=ELASTIC_SEARCH_URL).indexes(database_name).doctypes(*doc_type)

    def filter_by_submission_type(self, query, query_params):
        submission_type_filter = query_params.get('filter')
        if submission_type_filter == 'deleted':
            return query.filter(void=True)
        elif submission_type_filter == 'all':
            return query.filter(void=False)
        elif submission_type_filter == 'analysis':
            query = query.filter(status="success")
        else:
            query = query.filter(status=submission_type_filter)
        return query.filter(void=False)

    def create_paginated_query(self, query, query_params):
        query = super(SubmissionQueryBuilder, self).create_paginated_query(query, query_params)
        return self.filter_by_submission_type(query, query_params)

    def add_query_criteria(self, query_fields, query, query_text, query_params=None):
        query = super(SubmissionQueryBuilder, self).add_query_criteria(query_fields, query, query_text, query_params)
        search_filter_param = query_params.get('search_filters')
        if search_filter_param:
            submission_date_range = search_filter_param.get("submissionDatePicker")
            reporting_date_range = search_filter_param.get("reportingPeriodPicker")
            query = SubmissionDateRangeFilter(submission_date_range).build_filter_query(query)
            query = ReportingDateRangeFilter(reporting_date_range, self.form_model).build_filter_query(query)
            datasender_filter = search_filter_param.get("datasenderFilter")
            if datasender_filter:
                query = query.filter(ds_id=datasender_filter)
            subjectFilter = search_filter_param.get("subjectFilter")
            if subjectFilter:
                query = query.filter(entity_short_code=subjectFilter)
        return query

    def query_all(self, database_name, *doc_types, **filter_params):
        query = self.get_query(database_name, *doc_types)
        query_all_results = query[:query.count()]
        return query_all_results.filter(**filter_params)


class SubmissionQueryResponseCreator():
    def __init__(self, form_model):
        self.form_model = form_model

    def combine_name_and_id(self, short_code, entity_name, submission):
        return submission.append(
            ["%s<span class='small_grey'>  %s</span>" % (
                entity_name, short_code)]) if entity_name else submission.append(entity_name)

    def create_response(self, required_field_names, query):
        submissions = []
        for res in query.values_dict(tuple(required_field_names)):
            submission = [res._id]

            for key in required_field_names:
                meta_fields = ['ds_id', 'entity_short_code']
                if not key in meta_fields:
                    if key.lower().endswith(self.form_model.entity_question.code.lower()):
                        self.combine_name_and_id(res.get('entity_short_code'), res.get(key), submission)
                    elif key == 'ds_name':
                        self.combine_name_and_id(res.get('ds_id'), res.get('ds_name'), submission)
                    else:
                        submission.append(self.append_if_attachments_are_present(res, key))
            submissions.append(submission)
        return submissions

    def _get_key(self, key):
        if '_' in key:
            return key[key.index('_') + 1:]
        else:
            return key

    def append_if_attachments_are_present(self,res,  key):
        if type(get_field_by_attribute_value(self.form_model, 'code', self._get_key(key))) is ImageField:
            value = res.get(key)
            if value:
                return  "<span style=\"display:inline-block;width:70px; height: 70px;border:1px solid #CCC; margin-right:5px;display: table-cell;vertical-align: middle;\"><img style=\"width:70px;\" src='/attachment/%s/%s'/></span>" \
                        "<span style=\"display: table-cell;vertical-align: middle;padding: 5px;\"><a href='/download/attachment/%s/%s'>%s</a></span>" % (res._id, value, res._id, value, value)
        else:
            return res.get(key)


class SubmissionQuery(Query):
    def __init__(self, form_model, query_params):
        Query.__init__(self, SubmissionQueryResponseCreator(form_model), SubmissionQueryBuilder(form_model),
                       query_params)
        self.form_model = form_model

    def get_headers(self, user=None, entity_type=None):
        submission_type = self.query_params.get('filter')
        header = HeaderFactory(self.form_model).create_header(submission_type)
        return header.get_header_field_names()

    def query(self, database_name):
        query_all_results = self.query_builder.query_all(database_name, self.form_model.id)
        submission_type = self.query_params.get('filter')

        header = HeaderFactory(self.form_model).create_header(submission_type)
        submission_headers = header.get_header_field_names()
        query_by_submission_type = self.query_builder.filter_by_submission_type(query_all_results, self.query_params)
        filtered_query = self.query_builder.add_query_criteria(submission_headers, query_by_submission_type,
                                                               self.query_params.get('search_filters').get(
                                                                   'search_text'),
                                                               query_params=self.query_params)
        submissions = self.response_creator.create_response(submission_headers, filtered_query)
        return submissions


