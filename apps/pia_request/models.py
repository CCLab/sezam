from django.db.models import *
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from apps.vocabulary.models import AuthorityProfile
from apps.backend.utils import increment_id

PIA_REQUEST_STATUS= (
    ('in_progress', _(u'In progress')),
    ('successful', _(u'Successful')),
    ('part_successful', _(u'Partially successful')),
    ('refused', _(u'Refused')),
    ('overdue', _(u'Overdue')),
    ('long_overdue', _(u'Long overdue')),
    ('no_info', _(u'Information not held')),
    )


class PIARequestDraft(Model):
    """
    A draft of PIA request.

    Being deleted right after the request is sent.
    """
    authority_slug= CharField(max_length=1000,
                              verbose_name=_(u'Recipients (slugs)'))
    user= ForeignKey(User, help_text=_(u'Request from user'))
    subject= CharField(max_length=1000, null=True, blank=True,
                       verbose_name=_(u'Subject'))
    body= TextField(null=True, blank=True, verbose_name=_(u'Your message here'))
    created= DateTimeField(auto_now_add=True, verbose_name=_(u'Created'))
    lastchanged= DateTimeField(auto_now=True,
                               verbose_name=_(u'Last time changed'))

    def __unicode__(self):
        return self.subject


class PIARequest(Model):
    """
    Public Information Access (PIA) request.

    *
    Although it is possible to choose several Authorities when making a Public
    Information Request, the relation should always remain 1-N for getting
    statistics and maintaining the threads.

    Sending bulk of requests means looping through the selected Authorities and
    repeating a request for each of them.

    *
    The model is a main container for both Requests and Responses. The original
    message is simply the latest one with `is_response` is False. New request
    receives a new `request_id` (its max value incremented by 1). To build a
    thread of messages means extracting all the records with given request_id
    ordering the results by the field `created`. To build a list of requests
    means filtering by `orig`.
    """
    orig= BooleanField(verbose_name=_(u'Original request'))
    is_response= BooleanField(verbose_name=_(u'It is a response'))
    request_id= IntegerField(verbose_name=_(u'Request id'),
                             help_text=_(u'Unique for a thread'))
    user= ForeignKey(User, verbose_name=_(u'User'))
    authority= ForeignKey(AuthorityProfile, related_name='authority_requests',
                          verbose_name=_(u'Authority'))
    email_to= EmailField(max_length=254, verbose_name=_(u'To e-mail'))
    email_from= EmailField(max_length=254, verbose_name=_(u'From e-mail'))
    subject= CharField(max_length=1000, null=True, blank=True,
                       verbose_name=_(u'Subject'))
    body= TextField(null=True, blank=True, verbose_name=_(u'Message content'))
    created= DateTimeField(auto_now_add=True, verbose_name=_(u'Created'))
    status= CharField(max_length=50, choices=PIA_REQUEST_STATUS,
        default=PIA_REQUEST_STATUS[0][0], verbose_name=_(u'Request status'))

    def __unicode__(self):
        return self.subject

    def save(self, *args, **kwargs):
	"""
        Override save: generate request autoincrement id, but only if
        self.request_id is absent, which means that it is a new request.
	"""
        if self.request_id is None:
            self.request_id= increment_id(self.__class__, 'request_id')
        if self.orig:
            self.is_response=False
        super(self.__class__, self).save(*args, **kwargs)
