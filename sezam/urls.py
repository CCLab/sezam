from django.conf import settings
from django.conf.urls import patterns, include, url
from django.utils.translation import ugettext_lazy as _

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns= patterns('',
    url(r'^$', 'apps.browser.views.display_index', {'template': 'index.html'}),
    # url(r'^search/', include('haystack.urls')),
    url(r'^search/', include('apps.browser.urls')),
    url(r'^authority/', include('apps.authority.urls')),
    url(r'^request/', include('apps.pia_request.urls')),
    url(r'^user/', include('apps.userprofile.urls')),
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
