from django.conf.urls.defaults import patterns, url
from datawinners.blue.views.xfom_handlers import xfom_handle_upload

urlpatterns = patterns('',
                       url(r'^upload/$', xfom_handle_upload),
)
