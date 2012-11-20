from django.conf import settings
from django.conf.urls import patterns, include, url

urlpatterns = patterns('apps.pia_request.views',
    # Preview request with no id (create draft).
    url(r'^preview/$', 'preview_request',
        {'template': 'request.html'}, name='preview_request'),

    # POST request with the list of Authority list (slugs).
    # or GET with no slug (Authority to be selected in the form).
    url(r'^(?P<slug>[-\w]+)/$', 'new_request',
        {'template': 'request.html'}, name='new_request'),

    # GET request with a specified Authority slug.
    url(r'^(?P<slug>[-\w]+)/$', 'new_request',
        {'template': 'request.html'}, name='new_request_authority'),

    # Preview already created draft.
    url(r'^(?P<id>[-\w]+)/preview/$', 'preview_request',
        {'template': 'request.html'}, name='preview_request_id'),

    # View request message thread.
    url(r'^(?P<id>[-\w]+)/$', 'view_request',
        {'template': 'base.html'}, name='view_request_id'),
)
