from django.conf import settings
from django.conf.urls import patterns, url

urlpatterns = patterns('apps.userprofile.views',

    # Only user's requests.
    url(r'^(?P<id>\d+)/$', 'user_profile',
        {'template': 'user.html', 'profile': False}, name='user_requests'),

    # Show user's full profile (private if this user is logged on,
    # otherwise public).
    url(r'^(?P<id>\d+)/profile/$', 'user_profile',
        {'template': 'user.html', 'profile': True}, name='user_profile'),

    # Show user's full profile (private if this user is logged on,
    # otherwise public).
    url(r'^(?P<id>\d+)/profile/update/$', 'user_profile_update',
        {'template': 'user.html'}, name='user_profile_update'),

    # Change userpic.
    url(r'^(?P<id>\d+)/userpic/$', 'user_set_userpic',
        {'template': 'user.html'}, name='user_set_userpic'),
)