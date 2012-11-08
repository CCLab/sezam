from django.conf import settings
from django.conf.urls import patterns, include, url

urlpatterns = patterns('apps.browser.views',
    url(r'^$', 'display_authority', {'template': 'authority.html'},
        name='display_authorities'),

    url(r'^tree/$', 'get_authority_tree'),

    url(r'^list/$', 'get_authority_list', {'template': 'includes/authority_list'},
        name='get_authority_list'),

    url(r'^(?P<id>[-\w]+)/$', 'display_authority',
        {'template': 'authority.html'}, name='display_authority'),
)
