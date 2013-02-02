"""
Models for project-wide generic classes and
classes connected to the management (such as Notifier).
"""

from django.db.models import *
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from apps.vocabulary.models import Vocabulary, SlugVocabulary


ACTION= (
    ('active', _(u'Record has become active')),
    ('request_to', _(u'Request to the Authority')),
    ('response_from', _(u'Response from the Authority')),
    ('update', _(u'Record updated')),
    )


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
    """
    Meta-class for any Post-based model such as Message draft, Annotation,
    Request, Thread.
    """
    created= DateTimeField(auto_now_add=True, verbose_name=_(u'Created'))
    subject= CharField(max_length=255, null=True, blank=True,
                       verbose_name=_(u'Subject'))
    class Meta:
        abstract= True


class GenericMessage(GenericPost):
    """
    Meta-class for any kind of a message such as Request and Thread.
    """
    email_to= EmailField(max_length=254, verbose_name=_(u'To e-mail'))
    email_from= EmailField(max_length=254, verbose_name=_(u'From e-mail'))

    class Meta:
        abstract= True


class GenericFile(Model):
    """
    Attachment to a message.
    """
    filetype= CharField(max_length=10, verbose_name=_(u'File type'))
    filename= CharField(max_length=1000, verbose_name=_(u'File name'))
    filesize= IntegerField(default=125, verbose_name=_(u'File size'))
    path= CharField(max_length=1000,
                    verbose_name=_(u'Path to file (relative to site_media)'))

    class Meta:
        abstract= True


class TaggedItem(Vocabulary, SlugVocabulary):
    """
    Item tagged in Event Notification or wherever else.
    """
    content_type= ForeignKey(ContentType)
    object_id= PositiveIntegerField()
    content_object= generic.GenericForeignKey('content_type', 'object_id')

    def is_followed_by(self, usr):
        """
        Returns True if `usr` is subscribed to the updates of the Item.
        """
        if self.notification.filter(receiver=usr).count() > 0:
            return True
        return False

    def __unicode__(self):
        return self.slug


class EventNotification(GenericEvent):
    """
    Notification about changes in the db.
    """
    item= ForeignKey(TaggedItem, null=True, blank=True,
                     related_name='notification', verbose_name=_(u'Item'))
    action= CharField(max_length=50, choices=ACTION,
                      verbose_name=_(u'Notify about action'))
    awaiting= BooleanField(default=True, verbose_name=_(u'Awaiting'))

    # Should not depend on the registration in the system!
    # Notifications to the emails outside the system are possible.
    receiver= ForeignKey(User, null=True, blank=True,
        related_name='notification', verbose_name=_(u'Registered User'))
    receiver_email= EmailField(max_length=254, verbose_name=_(u'To e-mail'))

    def save(self, *args, **kwargs):
	"""
        Override save: fill user's email.
        """
        if self.receiver and (not self.receiver_email):
            self.receiver_email= self.receiver.email

        super(GenericEvent, self).save(*args, **kwargs)
