from celery.task.schedules import crontab
from celery.decorators import task, periodic_task
from django.utils.timezone import utc
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from datetime import datetime, timedelta
import re, sys

from sezam.settings import MAILBOXES, ATTACHMENT_DIR, OVERDUE_DAYS,\
    DEFAULT_FROM_EMAIL
from apps.pia_request.models import PIARequest, PIAThread, PIAAttachment,\
    PIA_REQUEST_STATUS, get_request_status
from apps.backend import MailImporter, AppMessage
from apps.backend.html2text import html2text
from apps.backend.utils import get_domain_name, email_from_name

@periodic_task(run_every=crontab(day_of_week="*", hour="*", minute="*/10"))
def check_mail(mailbox_settings=None):
    """
    Checks mail for responses.
    If there is any response, creates a Message and adds it to the Thread.
    Also processes attachments in the emails and adds them to newly
    created messages.
    """

    # Pattern to look for in `to` fields: delimiters include dash and dot.
    addr_template= r'(\-|\.){1}\d+\@%s' % get_domain_name()
    addr_pattern= re.compile(addr_template+'$') # End of line is required only locally.

    # Collect mailboxes to check. NB: Mailbox should always be a list.
    messages_total= 0
    mailboxes= collect_mailboxes(mailbox_settings)
    for mailbox in mailboxes:
        imp= MailImporter(mailbox,
                          attachment_dir=ATTACHMENT_DIR,
                          addr_template=addr_template)
        unread_messages= imp.process_mails(imp.imap_connect(), header_only=False)
        for msg in unread_messages:
            messages_total += 1
            # Extract only the first(!) meaningful e-mail address.
            try:
                field_to= [t.strip() for t in msg['header']['to'].split(',') if addr_pattern.search(t)][0]
            except:
                # There are no such address in it - is it a spam?
                # TO-DO: log it or to add the `from` address to the blacklist?
                # Should the message be deleted?
                print AppMessage('ResponseNotFound', value=msg['header']).message
                continue
            # Extracting request id.
            try:
                request_id= int(field_to.split('@')[0].rsplit('.', 1)[-1])
            except:
                try:
                    request_id= int(field_to.split('@')[0].rsplit('-', 1)[-1])
                except:
                    print AppMessage('ResponseNotFound', value=msg['header']).message
                    continue
            new_message= new_message_in_thread(request_id, msg)
            if new_message:
                report_to_user_sent= send_report(new_message.request,
                    status='response_received',
                    template='emails/response_received.txt')
    return AppMessage('CheckMailComplete', value=messages_total).message \
        % messages_total


@periodic_task(run_every=crontab(minute=0, hour=0))
def check_overdue():
    """
    Check in the db for overdue requests.
    Executed daily at midnight.
    Returns status of completion.
    """
    total_overdue_requests= 0

    # Process overdue requests (those remain unanswered for OVERDUE_DAYS).
    when= datetime.utcnow().replace(tzinfo=utc) - timedelta(days=OVERDUE_DAYS)
    in_progress= 'in_progress'
    for pia_request in PIARequest.objects.filter(created__lt=when,
                                                 status=in_progress):
        if PIAThread.objects.filter(request=pia_request,
                                    is_response=True).count() == 0:
            total_overdue_requests += 1
            
            # Send a reminder to the Authority.
            send_reminder(pia_request)
            # Send an overdue report to user.
            send_report(pia_request,
                        status='overdue',
                        template='emails/report_overdue_to_user.txt')

            # Set 'overdue' status to the request:
            # this doesn't depend on sending messages - even if there are errors
            # the request should be marked as `overdue`.
            pia_request.status= get_request_status('overdue')
            try:
                pia_request.save()
            except Exception as e:
                pass

    # Process long_overdue requests (those that remain unanswered for twice OVERDUE_DAYS).
    when= datetime.utcnow().replace(tzinfo=utc) - timedelta(days=OVERDUE_DAYS * 2)
    in_progress= ['in_progress', 'overdue']
    for pia_request in PIARequest.objects.filter(created__lt=when,
                                                 status__in=in_progress):
        if PIAThread.objects.filter(request=pia_request,
                                    is_response=True).count() == 0:
            total_overdue_requests += 1

            # Send a reminder to the Authority.
            send_reminder(pia_request,
                          email_template='emails/reminder_long_overdue.txt')
            # Send an overdue report to user.
            send_report(pia_request,
                        status='long_overdue',
                        template='emails/report_long_overdue_to_user.txt')
            # Set 'long_overdue' status to the request.
            pia_request.status= 'long_overdue'
            try:
                pia_request.save()
            except Exception as e:
                pass

    return AppMessage('CheckOverdueComplete').message % total_overdue_requests


def new_message_in_thread(request_id, msg):
    """
    Pick up the request and create a new PIAMessage in its PIAThread.
    """
    try:
        request= PIARequest.objects.get(pk=request_id)
    except Exception as e:
        print AppMessage('RequestNotFound', value=(request_id, e,)).message
        return None
    # Collect and prepare data from the message.
    data= {'request': request, 'is_response': True,
           'email_from': msg['header']['from'],
           'email_to': msg['header']['to'],
           'subject': msg['header']['subject'],
           'body': msg['content']}
    # Creating a new message in the Request's Thread.
    new_message= PIAThread(**data)
    try:
        new_message.save()
    except Exception as e:
        new_message= None
        print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(),
                                          AppMessage('MsgCreateFailed').message % e)
    if new_message:
        # Change the status of the Request to 'awaiting classification'.
        request.status= get_request_status('awaiting')
        try:
            request.save()
        except Exception as e:
            pass
        # Process attachments.
        if msg['attachments']:
            for attachment in msg['attachments']:
                filesize= attachment['filesize']
                path= attachment['filename']
                filename= path.rsplit('/')[-1]
                filetype= path.rsplit('.')[-1]
                try:
                    PIAAttachment.objects.create(message=new_message, path=path,
                        filename=filename, filetype=filetype, filesize=filesize)
                except Exception as e:
                    print AppMessage('AttachFailed', value=(
                        filename, request_id, e,)).message
    return new_message


def collect_mailboxes(mailbox_settings):
    """
    Create a list of mailboxes to check.
    """
    def _append_mailbox(mb_key):
        try:
            mailboxes.append(MAILBOXES[mb_key])
        except KeyError:
            print AppMessage('MailboxNotFound', value=mb_key).message
    mailboxes= []
    if mailbox_settings is None:
        _append_mailbox('default')
    else:
        if isinstance(mailbox_settings, basestring):
            # Single mailbox.
            _append_mailbox(mailbox_settings)
        elif isinstance(mailbox_settings, list) or isinstance(mailbox_settings, tuple):
            # Several mailboxes.
            for mailbox_name in mailbox_settings:
                _append_mailbox(mailbox_name)
    return mailboxes


def send_reminder(pia_request, overdue_date=None, **kwargs):
    """
    Send a reminder message to the Authority.
    """
    template= kwargs.get('email_template', 'emails/reminder_overdue.txt')
    if overdue_date is None:
        overdue_date= datetime.strftime(pia_request.created, '%d.%m.%Y')
    authority= pia_request.authority
    try:
        email_to= authority.email
    except:
        print AppMessage('AuthEmailNotFound', value=(authority.slug, authority.name,)).message
        return None
    email_from= email_from_name(pia_request.user.get_full_name(),
                                id=pia_request.id,
                                delimiter='.')
    message_subject= get_message_subject('overdue',
                                         number=pia_request.pk,
                                         date=overdue_date)
    message_content= render_to_string(template, { 'email_to': email_to,
        'request_id': str(pia_request.pk), 'request_date': overdue_date,
        'authority': authority, 'info_email': 'info@%s' % get_domain_name()})
    message_request= EmailMessage(message_subject, message_content,
        DEFAULT_FROM_EMAIL, [email_to], headers = {'Reply-To': email_from})
    try: # sending the message to the Authority, check if it doesn't fail.
        message_request.send(fail_silently=False)
    except Exception as e:
        print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(),
            AppMessage('MailSendFailed').message % e)
        return None
    return True # Success. 


def send_report(pia_request, status, **kwargs):
    """
    Send a report message to the User.
    """
    template= kwargs.get('template', 'emails/report_overdue_to_user.txt')
    message_subject= kwargs.get('subject', None)
    report_date= kwargs.get('report_date', None)
    if report_date is None:
        report_date= datetime.strftime(pia_request.created, '%d.%m.%Y')
    authority= pia_request.authority
    user= pia_request.user
    try:
        email_to= user.email
    except:
        print AppMessage('UserEmailNotFound', value=(user.username,)).message
        return None
    email_from= DEFAULT_FROM_EMAIL
    message_subject= get_message_subject(status, number=pia_request.pk,
                                         date=report_date)
    message_content= render_to_string(template, {'email_to': email_to,
        'request_id': str(pia_request.pk), 'request_date': report_date,
        'authority': authority, 'user': user, 'domain': get_domain_name()})
    message_request= EmailMessage(message_subject, message_content,
        DEFAULT_FROM_EMAIL, [email_to], headers = {'Reply-To': email_from})
    try: # sending the message to the User, check if it doesn't fail.
        message_request.send(fail_silently=False)
    except Exception as e:
        print AppMessage('MailSendFailed').message % e
        return None
    return True # Success.


def get_message_subject(status, **kwargs):
    """
    Construct message subject based on the request status or an event.
    If there's a date in kwargs, it should already be converted to string.
    """
    number= kwargs.get('id', '')
    date= kwargs.get('date', None)
    if date is None:
        date= datetime.strftime(
            datetime.utcnow().replace(tzinfo=utc), '%d.%m.%Y')
    subjects= {
        'overdue': _(u'Public Information Request ') + str(number) + _(u' is overdue from ') + date,
        'long_overdue': _(u'Public Information Request ') + str(number) + _(u' is long overdue - from ') + date,
        'response_received': _(u'The response received for the Public Information Request ') + \
            str(number) + _(u' from ') + date
        }
    return subjects[status]
