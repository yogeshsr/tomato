from django.conf.urls.defaults import patterns, url
from datawinners.blue import view
from datawinners.blue.view import new_web_submission, update_web_submission, \
    get_questionnaires, submit_submission, get_submissions
from datawinners.blue.view import ProjectUpload, upload_project, ProjectUpdate
from datawinners.project.views import submission_views
from datawinners.blue.view import xform_survey_web_questionnaire

urlpatterns = patterns('',

   # GET prj upload page
   url(r'^project_upload/$', upload_project, name="upload_project"),
   url(r'^xlsform/upload/$', ProjectUpload.as_view(), name="import_project"),
   url(r'^xlsform/download/$', view.project_download),
   url(r'^xlsform/upload/update/(?P<project_id>\w+?)/$', ProjectUpdate.as_view(), name="update_project"),

   # GET new submissions
   url(r'^project/xformsurvey/(?P<project_id>\w+?)/$', xform_survey_web_questionnaire, name="xform_web_questionnaire"),
   url(r'^blue/web_submission/$', new_web_submission, name="new_web_submission"),
   # GET edit submission
   url(r'^project/(?P<project_id>.+?)/submissions/edit_xform/(?P<survey_response_id>[^\\/]+?)/$', submission_views.edit_xform_submission, name="edit_xform_submission"),
   url(r'^blue/web_submission/(?P<survey_response_id>.+?)/$', update_web_submission, name="update_web_submission"),

   url(r'^client/questionnaires/$', get_questionnaires),
   url(r'^client/submissions/(?P<submission_uuid>\w+?)/$', get_submissions),
   url(r'^client/submissions/', submit_submission),

)
