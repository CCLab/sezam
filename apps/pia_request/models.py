from django.db.models import *
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from apps.vocabulary.models import AuthorityProfile

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

class PIARequest(Model):
    """
    Public Information Access (PIA) request.

    Although it is possible to choose several Authorities when making a
    Public Information Request, the relation should always remain 1-N for
    getting statistics.

    Sending bulk of requests means looping through the selected Authorities
    and repeating a request for each of them.
    """
    user= ForeignKey(User, help_text=_(u'Request from user'))
    authority= ForeignKey(AuthorityProfile, related_name='authority_requests',
        verbose_name=_(u'Recipient'))
    authority_email= EmailField(max_length=254, verbose_name=_(u'E-mail'))
    subject= CharField(max_length=1000, verbose_name=_(u'Subject'))
    body= TextField(null=True, blank=True, verbose_name=_(u'Your message here'))
    created= DateTimeField(auto_now_add=True, verbose_name=_(u'Created'))
    status= CharField(max_length=50, choices=PIA_REQUEST_STATUS,
        default=PIA_REQUEST_STATUS[0][0], verbose_name=_(u'Request status'))
