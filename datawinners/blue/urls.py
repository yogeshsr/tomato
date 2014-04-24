from django.conf.urls.defaults import patterns, url
from datawinners.blue import view
from datawinners.blue.view import new_web_submission, update_web_submission, get_attachment, attachment_download
from datawinners.blue.view import ProjectUpload, upload_project, ProjectUpdate, get_projects, get_questionnaire
from datawinners.project.views import submission_views
from datawinners.blue.view import xform_questionnaire, xform_survey_web_questionnaire

urlpatterns = patterns('',
                       #todo remove this after enketo is embedded to DW
                       # called by php; kept for debugging
                       url(r'^project/xformsurvey/(?P<project_id>\w+?)/$', xform_survey_web_questionnaire,
                           name="xform_web_questionnaire"),
                       # dw url of standalone enketto; kept for debugging
                       url(r'^project/(?P<project_id>.+?)/submissions/edit_xform_old/(?P<survey_response_id>[^\\/]+?)/$',
                           submission_views.edit_xform_submission_old, name="edit_xform_submission_old"),


                       url(r'^project_upload/$', upload_project, name="upload_project"),
                       url(r'^project/xformquestionnaire/(?P<project_id>\w+?)/$', xform_questionnaire,
                           name="xform_questionnaire"),
                       url(r'^project/(?P<project_id>.+?)/submissions/edit_xform/(?P<survey_response_id>[^\\/]+?)/$',
                           submission_views.edit_xform_submission, name="edit_xform_submission"),
                       url(r'^xlsform/upload/$', ProjectUpload.as_view(), name="import_project"),
                       url(r'^xlsform/upload/update/(?P<project_id>\w+?)/$', ProjectUpdate.as_view(), name="update_project"),
                       url(r'^xlsform/download/$', view.project_download),
                       url(r'^blue/web_submission/$', new_web_submission, name="new_web_submission"),
                       url(r'^blue/web_submission/(?P<survey_response_id>.+?)/$', update_web_submission, name="update_web_submission"),
                       url(r'^projects_temp/$', get_projects),
                       url(r'^questionnaire_temp/(?P<project_id>\w+?)/$', get_questionnaire),
                       url(r'^attachment/(?P<document_id>.+?)/(?P<attachment_name>[^\\/]+?)/$', get_attachment),
                       url(r'^download/attachment/(?P<document_id>.+?)/(?P<attachment_name>[^\\/]+?)/$', attachment_download)
)
