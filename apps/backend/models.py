""" Models for project-wide abstract classes.
    Warning! Only abstract classes here, or those that don't store app-specific
    information.
    """

from django.db.models import *
from django.utils.translation import ugettext_lazy as _


class GenericEvent(Model):
    """
    Meta-class for any kind of event, such as creation of the Request or
    changing the structure of Authority.
        
    Events produce effects in time, stored in connected models (such as
    Request <-> Thread), but it is crusial for ordering to have information
    about the last updates - hence the `lastchanged`.
    """
    created= DateTimeField(auto_now_add=True, verbose_name=_(u'Created'))
    lastchanged= DateTimeField(auto_now=True, verbose_name=_(u'Last changed'))
    summary= CharField(max_length=255, null=True, blank=True,
                       verbose_name=_(u'Summary'))
    class Meta:
        abstract= True
        ordering= ('-lastchanged',)


class GenericText(Model):
    """
    An abstract text for all text based models: Messages, Comments,
    Annotations, etc.
    """
    body= TextField(null=True, blank=True, verbose_name=_(u'Body'))
    
    class Meta:
        abstract= True


class GenericPost(GenericText):
    """ Meta-class for any Post-based model such as Message draft, Annotation,
        Request, Thread.
        """
    created= DateTimeField(auto_now_add=True, verbose_name=_(u'Created'))
    subject= CharField(max_length=255, null=True, blank=True,
                       verbose_name=_(u'Subject'))
    class Meta:
        abstract= True


class GenericMessage(GenericPost):
    """ Meta-class for any kind of a message such as Request and Thread.
        """
    email_to= EmailField(max_length=254, verbose_name=_(u'To e-mail'))
    email_from= EmailField(max_length=254, verbose_name=_(u'From e-mail'))

    class Meta:
        abstract= True


class GenericFile(Model):
    """ Attachment to PIAMessage.
        """
    filetype= CharField(max_length=10, verbose_name=_(u'File type'))
    filename= CharField(max_length=1000, verbose_name=_(u'File name'))
    filesize= IntegerField(default=125, verbose_name=_(u'File size'))
    path= CharField(max_length=1000,
                    verbose_name=_(u'Path to file (relative to site_media)'))

    class Meta:
        abstract= True

