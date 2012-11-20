from django.conf import settings
from django.conf.urls import patterns, include, url

urlpatterns = patterns('apps.authority.views',
    url(r'^$', 'display_authority', {'template': 'authorities.html'},
        name='display_authorities'),

    url(r'^tree/$', 'get_authority_tree'),

    url(r'^list/$', 'get_authority_list',
        {'template': 'includes/authority_list'}, name='get_authority_list'),

    url(r'^list/(?P<id>[-\w]+)/$', 'get_authority_list',
        {'template': 'includes/authority_list'}, name='get_authority_list_id'),

    url(r'^(?P<slug>[-\w]+)/$', 'get_authority_info',
        {'template': 'authority.html'}, name='get_authority_info'),

    url(r'^(?P<id>[-\w]+)/$', 'display_authority',
        {'template': 'authorities.html'}, name='display_authority'),
)
