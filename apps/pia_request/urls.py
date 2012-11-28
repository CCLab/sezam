from django.conf import settings
from django.conf.urls import patterns, include, url

urlpatterns = patterns('apps.pia_request.views',
    # Preview request with no id (create draft).
    url(r'^preview/$', 'preview_request',
        {'template': 'request.html'}, name='preview_request'),

    # View request message thread.
    url(r'^(?P<request_id>\d+)/$', 'view_thread',
        {'template': 'thread.html'}, name='view_thread'),

    # POST request with the list of Authority list (slugs).
    # or GET with no slug (Authority to be selected in the form).
    url(r'^(?P<slug>[-\w]+)/$', 'new_request',
        {'template': 'request.html'}, name='new_request'),

    # Preview already created draft.
    url(r'^(?P<id>[-\w]+)/preview/$', 'preview_request',
        {'template': 'request.html'}, name='preview_request_id'),

    # Preview already created draft.
    url(r'^(?P<id>[-\w]+)/send/$', 'send_request',
        {'template': 'request_email.txt'}, name='send_request_id'),
)
