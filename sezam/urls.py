""" main urls
"""
from django.conf import settings
from django.conf.urls import patterns, include, url
#from django.views.generic.simple import direct_to_template
#from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

from apps.userprofile.cbv import RegistrationTosView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'apps.browser.views.display_index', {'template': 'index.html'}),
    url(r'^pomoc/', TemplateView.as_view(template_name='help.html'), name="main-help"), # pylint: disable=E1120
    url(r'^regulamin/', TemplateView.as_view(template_name='regulamin.html'), name="main-regulamin"), # pylint: disable=E1120
    url(r'^szukaj/', include('apps.browser.urls')),
    url(r'^instytucje/', include('apps.authority.urls')),
    url(r'^request/', include('apps.pia_request.urls')),
    url(r'^user/', include('apps.userprofile.urls')),
    url(r'^accounts/register', RegistrationTosView.as_view(),name="main-register"),
    url(r'^accounts/', include('registration.backends.default.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),

        url(r'^static/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.STATIC_ROOT})
    )
