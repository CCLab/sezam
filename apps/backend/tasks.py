from celery.task.schedules import crontab
from celery.decorators import periodic_task
from django.utils.translation import ugettext as _
from django.core.mail import EmailMessage
from django.conf import settings

# from haystack.management.commands import update_index
import subprocess

from apps.backend.utils import send_notification
from apps.backend.models import EventNotification
from apps.backend import AppMessage

@periodic_task(run_every=crontab(day_of_week="*", hour="*", minute="*/2"))
def process_notifications():
    """
    Checks for notifications about events.
    """
    notification_processed= 0
    for notification in EventNotification.objects.filter(awaiting=True):
        if notification.action == 'active':
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
                    print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(),
                        AppMessage('NotificFailed').message % notification.__unicode__())
    return "Completed processing notifications: %d sent." % notification_processed


@periodic_task(run_every=crontab(day_of_week="*", hour="*/2", minute=0))
def haystack_update_index():
    """"""
    try:
        p= subprocess.Popen(['python', 'manage.py', 'update_index'])
    except Exception as e:
        return "ERROR starting subprocess. System message is:\n%s" % e
    return "Index updated successfully."
