from django.conf import settings
from django.conf.urls import patterns, url

urlpatterns = patterns('apps.pia_request.views',
    # View requests, no filter.
    url(r'^$', 'request_list', {'template': 'requests.html'},
        name='request_list'),

    # Preview request with no id (create draft).
    url(r'^preview/$', 'preview_request',
        {'template': 'request.html'}, name='preview_request'),

    # Bulk discard of the request drafts.
    url(r'^discard/$', 'discard_request_draft',
        name='discard_request_drafts'),

    # Discard single request draft.
    url(r'^discard/(?P<id>\d+)/$', 'discard_request_draft',
        name='discard_request_draft'),

    # View request message thread.
    url(r'^(?P<id>\d+)/$', 'view_thread',
        {'template': 'thread.html'}, name='view_thread'),

    # GET request with the list of Authority list (slugs).
    url(r'^(?P<slug>[-\w]+)/$', 'new_request',
        {'template': 'request.html'}, name='new_request'),

    # Or POST with no slug (Authority to be selected in the form).
    url(r'^multiple/$', 'new_request',
        {'template': 'request.html'}, name='new_request_multiple'),

   # View/filter requests.
   url(r'^(?P<status>[-\w]+)/$', 'request_list', {'template': 'requests.html'},
       name='request_list_status'),   

    # Preview already created draft.
    url(r'^(?P<id>\d+)/preview/$', 'preview_request',
        {'template': 'request.html'}, name='preview_request_id'),

    # Similar requests.
    url(r'^(?P<id>\d+)/similar/$', 'similar_requests',
        {'template': 'search/search.html'}, name='similar_requests'),

    # Send the request.
    url(r'^(?P<id>\d+)/send/$', 'send_request',
        {'template': 'request.html', 'email_template': 'emails/request_to_authority.txt'},
        name='send_request_id'),

    url(r'^(?P<id>\d+)/reply/$', 'reply_to_thread', {'template': 'thread.html'},
        name='reply_to_thread'),

   url(r'^(?P<id>\d+)/status/(?P<status_id>[-\w]+)/$', 'set_request_status',
       {'template': 'thread.html'}, name='set_request_status'),
                       
   url(r'^(?P<id>\d+)/annotate/$', 'annotate_request',
       {'template': 'thread.html'}, name='annotate_request'),
)
