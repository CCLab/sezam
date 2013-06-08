""" authority urls
"""
#from django.conf import settings
from django.conf.urls import patterns, url
from haystack.query import SearchQuerySet
from haystack.views import SearchView
from apps.browser.forms import ModelSearchForm

urlpatterns = patterns('apps.authority.views',

    # Both `display_authorities` and `search_authority` launch the same process.
    # `display_authorities` is for the Authorities page with the tree and list.
    url(r'^$', 'display_authority', {'template': 'authorities.html',
        'search_only': False}, name='display_authorities'),

    # `search_authority` is for the empty Authorities page
    # with the search form only.
    url(r'^find/$', 'display_authority', {'template': 'authorities.html',
        'search_only': True}, name='search_authority_blank'),

    url(r'^(?P<slug>[-\w]+)/follow/$', 'follow_authority',
        name='follow_authority'),

    url(r'^(?P<slug>[-\w]+)/unfollow/$', 'unfollow_authority',
        name='unfollow_authority'),

    url(r'^search/$', SearchView(template='authorities.html',
        searchqueryset=SearchQuerySet().all(), form_class=ModelSearchForm),
        name='search_authority'),

    url(r'^search/autocomplete/$', 'autocomplete', name='autocomplete'),

    url(r'^tree/$', 'get_authority_tree', name='authority-tree'),

    url(r'^add/$', 'add_authority', {'template': 'add_record.html'},
        name='add_authority'),

    url(r'^download/(?P<ext>[-\w]+)/$', 'download_authority_list',
        name='download_authority_list'),

    url(r'^list/$', 'get_authority_list',
        {'template': 'includes/authority_list.html'},
        name='get_authority_list'),

    url(r'^list/(?P<a_id>\d+)/$', 'get_authority_list',
        {'template': 'includes/authority_list.html'},
        name='get_authority_list_id'),

    url(r'^(?P<slug>[-\w]+)/$', 'get_authority_info',
        {'template': 'authority.html'}, name='get_authority_info'),

    url(r'^(?P<id>\d+)/$', 'display_authority',
        {'template': 'authorities.html'}, name='display_authority'),
)
