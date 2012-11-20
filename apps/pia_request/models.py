from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from apps.vocabulary.models import AuthorityProfile


class PIARequestDraft(models.Model):
    """
    A draft of PIA request.

    Being deleted right after the request is sent.
    """
    authority_slug= models.CharField(max_length=1000,
                                     verbose_name=_(u'Recipients (slugs)'))
    user= models.ForeignKey(User, help_text=_(u'Request from user'))
    subject= models.CharField(max_length=1000, null=True, blank=True,
                              verbose_name=_(u'Subject'))
    body= models.TextField(null=True, blank=True,
                           verbose_name=_(u'Your message here'))
    created= models.DateTimeField(auto_now_add=True, verbose_name=_(u'Created'))
    lastchanged= models.DateTimeField(auto_now=True,
                                      verbose_name=_(u'Last time changed'))

# class PIARequest(models.Model):
#     """
#     Public Information Access (PIA) request.

#     Although it is possible to choose several Authorities when making a
#     Public Information Request, the relation should always remain 1-N for
#     getting statistics.

#     Sending bulk of requests means looping through the selected Authorities
#     and repeating a request for each of them.
#     """
#     authority= models.ForeignKey(AuthorityProfile,
#                                  verbose_name=_(u'Recipient'))
#     subject= models.CharField(max_length=1000, verbose_name=_(u'Subject'))
#     pia_request_datetime= models.DateTimeField(auto_now_add=True,
#                                                verbose_name=_(u'Created'))
