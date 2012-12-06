from django.conf import settings
from django.conf.urls import patterns, include, url

urlpatterns = patterns('apps.pia_request.views',
    # View/filter requests.
    url(r'^$', 'request_list', {'template': 'requests.html'},
        name='request_list'),

    # Preview request with no id (create draft).
    url(r'^preview/$', 'preview_request',
        {'template': 'request.html'}, name='preview_request'),

    # View request message thread.
    url(r'^(?P<id>\d+)/$', 'view_thread',
        {'template': 'thread.html'}, name='view_thread'),

    # POST request with the list of Authority list (slugs).
    # or GET with no slug (Authority to be selected in the form).
    url(r'^(?P<slug>[-\w]+)/$', 'new_request',
        {'template': 'request.html'}, name='new_request'),

    # Preview already created draft.
    url(r'^(?P<id>\d+)/preview/$', 'preview_request',
        {'template': 'request.html'}, name='preview_request_id'),

    # Send the request.
    url(r'^(?P<id>\d+)/send/$', 'send_request',
        {'template': 'request.html', 'email_template': 'request_email.txt'},
        name='send_request_id'),

    url(r'^(?P<id>\d+)/reply/$', 'reply_to_thread',
        {'template': 'thread.html', 'email_template': 'reply_email.txt'},
        name='reply_to_thread'),

   url(r'^(?P<id>\d+)/status/(?P<status_id>[-\w]+)/$', 'set_request_status',
       {'template': 'thread.html'}, name='set_request_status'),
                       
   url(r'^(?P<id>\d+)/annotate/$', 'annotate_request',
       {'template': 'thread.html'}, name='annotate_request'),
)
