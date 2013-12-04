from datawinners.accountmanagement.helper import is_org_user


def submission_stats(dbm, form_code):

    rows = dbm.load_all_rows_in_view('undeleted_survey_response', startkey=[form_code], endkey=[form_code, {}],
                                     group=True, group_level=1, reduce=True)
    submission_success,submission_errors = 0, 0
    for row in rows:
        submission_success = row["value"]["success"]
        submission_errors = row["value"]["count"] - row["value"]["success"]
    return submission_success,submission_errors


def get_submission_form_fields_for_user(form_model, request):
    form_fields = form_model.form_fields
    if form_model.entity_defaults_to_reporter():
        if not is_org_user(request.user):
            return filter(lambda field: field['code']!= form_model.entity_question.code, form_fields)
    return form_fields