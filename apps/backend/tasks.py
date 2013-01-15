from celery.task.schedules import crontab
from celery.decorators import periodic_task
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings

from apps.backend.utils import get_domain_name
from apps.backend.models import EventNotification
from apps.backend import AppMessage

@periodic_task(run_every=crontab(day_of_week="*", hour="*", minute="*/2"))
def process_notifications():
    """
    Checks for notifications about events.
    """
    notification_processed= 0
    for notification in EventNotification.objects.filter(awaiting=True):
        if notification.action == 'save':
            pass
        elif notification.action == 'delete':
            pass
        elif notification.action == 'update':
            pass
        elif notification.action == 'active':
            is_active= False
            try:
                is_active= notification.item.content_object.active
            except:
                pass
            if is_active:
                if send_notification(notification):
                    notification.awaiting= False
                    notification.save()
                    notification_processed += 1
                else:
                    print "Cannot send notification!"
    return "Completed processing notifications: %d sent." % notification_processed


def send_notification(notification):
    """
    Sending user a notification about the event
    as described in EventNotification.

    Returns True if message successfully sent.
    """
    template= 'emails/notification_%s.txt' % notification.action
    message_subject= '%s: %s' % (notification.get_action_display(),
                                 notification.item.content_object.name)
    message_content= render_to_string(template, {'notification': notification,
                                                 'domain': get_domain_name()})
    message_notification= EmailMessage(message_subject, message_content,
        settings.SERVER_EMAIL, [notification.receiver_email])
    try: # sending the message to the receiver, check if it doesn't fail.
        message_notification.send(fail_silently=False)
    except Exception as e:
        print e
        print AppMessage('MailSendFailed', value=(
            'notification', notification,)).message
        return False
    return True
    
