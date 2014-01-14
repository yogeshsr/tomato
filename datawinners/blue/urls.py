from django.conf.urls.defaults import patterns, url
from datawinners.blue.view import ProjectUpload

urlpatterns = patterns('',
                       url(r'^xlsform/upload/$', ProjectUpload.as_view(), name="import_project"),
)
