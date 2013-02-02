from celery.task.schedules import crontab
from celery.decorators import periodic_task
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings

# from haystack.management.commands import update_index
import subprocess

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
        # Different cases possible.
        if notification.action == 'request_to':
            pass
        elif notification.action == 'response_from':
            pass
        elif notification.action == 'update':
            pass
        elif notification.action == 'active':
            # Process the notification of an element become 'active'.
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
    


@periodic_task(run_every=crontab(day_of_week="*", hour="*/2", minute=0))
def haystack_update_index():
    """"""
    try:
        p= subprocess.Popen(['python', 'manage.py', 'update_index'])
    except Exception as e:
        return "ERROR! Subprocess can't be started, system message is:\n%s" % (
            ' '.join(params), e)
    return "Index updated successfully."
