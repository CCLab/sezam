"""
PIA views
"""

import cStringIO as StringIO
from datetime import datetime
from shutil import rmtree
from time import struct_time, strptime
import zipfile, cgi, os, sys

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template.loader import render_to_string
from django.template import RequestContext
#from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _

from haystack.query import SearchQuerySet

from apps.backend import AppMessage
from apps.backend.models import TaggedItem, EventNotification
from apps.backend.utils import re_subject, process_filter_request, \
    downcode, save_attached_file, update_user_message, id_generator,\
    get_domain_name, email_from_name, clean_text_for_search, render_to_pdf, \
    send_mail_managers
from apps.browser.forms import ModelSearchForm
from apps.pia_request.forms import MakeRequestForm, PIAFilterForm, ReplyDraftForm, CommentForm
from apps.pia_request.models import PIARequestDraft, PIARequest, PIAThread, PIAAnnotation, PIAAttachment, PIA_REQUEST_STATUS
from apps.vocabulary.models import AuthorityProfile

# Limiting request status list for user.
PIA_REQUEST_STATUS_VISIBLE = tuple(v for v in PIA_REQUEST_STATUS if v[0] not in ('overdue', 'long_overdue', 'withdrawn', 'awaiting',))

def request_list(request, status=None, **kwargs):
    """
    Display list of the latest PIA requests.
    """
    if request.method == 'POST':
        raise Http404
    user_message = request.session.pop('user_message', {})
    template = kwargs.get('template', 'requests.html')

    initial, query, urlparams = process_filter_request(
        request, PIA_REQUEST_STATUS)

    # Query db.
    if query:
        pia_requests = PIARequest.active_objects.filter(**query)
    else:
        pia_requests = PIARequest.active_objects.all()

    paginator = Paginator(pia_requests, settings.PAGINATE_BY)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        results = paginator.page(page)
    except (EmptyPage, InvalidPage):
        results = paginator.page(paginator.num_pages)

    return render_to_response(template,
                              {'page': results,
                               'form': PIAFilterForm(initial=initial),
                               'user_message': user_message,
                               'urlparams': urlparams,
                               'page_title': _(u'View and search requests')},
        context_instance=RequestContext(request))

@login_required
def new_request(request, slug=None, **kwargs):
    """
    Display the form for making a request to the Authority (slug).
    """
    template = kwargs.get('template', 'request.html')
    if request.method == 'GET':
        try:
            authority = AuthorityProfile.objects.get(slug=slug)
        except AuthorityProfile.DoesNotExist:
            raise Http404
        authority = [authority] # Result should always be a list.
    elif request.method == 'POST':
        # Multiple Authorities.
        authority_slug = dict(request.POST).get(u'authority_slug', None)
        authority = list()
        if authority_slug:
            for slug in authority_slug:
                try:
                    auth = AuthorityProfile.objects.get(slug=slug)
                except:
                    continue
                authority.append(auth)
        else: # Nothing selected.
            return redirect(request.META.get('HTTP_REFERER'))
    initial = {'authority': authority, 'user': request.user}
    return render_to_response(template,
        {'form': MakeRequestForm(initial=initial)},
        context_instance=RequestContext(request))

def process_attachments(msg, attachments, **kwargs):
    """
    Process attachments of a given message.
    Attachments should all be stored in a specific user's upload folder.
    **kwargs determine folders name:
    `dir_name`:
    .../<dir_name>_...      - if given (usually user name)
    .../undefined_..        - if None
    `dir_id`:
    .../<dir_name>_<dir_id> - if given (usually `request_id`)
    .../<dir_name>_upload   - if None
    """
    dir_name = kwargs.get('dir_name', 'undefined')
    dir_id = kwargs.get('dir_id', None)

    # Try to convert the last part of dir_name to time -
    # maybe we already have dir_id.
    dir_name_post_fix = dir_name.rsplit('/')
    if len(dir_name_post_fix) > 1:
        for substr in dir_name_post_fix[:2]:
            try:
                _dir_id = strptime(substr, '%d-%m-%Y_%H-%M')
            except ValueError:
                _dir_id = None
            if isinstance(_dir_id, struct_time):
                dir_id = substr
                break
    if dir_id: # If so, remove its part from dir_name.
        dir_name = dir_name.replace(dir_id, '').replace('//', '/')

    # attached_so_far= {f.filename: f.filesize for f in msg.attachments.all()}
    # This doesn't work in python 2.6, so:
    attached_so_far = {}
    for f in msg.attachments.all():
        attached_so_far.update({f.filename: f.filesize})

    attachment_failed = []
    for attachment in attachments:
        if attachment.name in attached_so_far.keys():
            if len(attachment) == attached_so_far[attachment.name]:
                # The file is already attached to the message,
                # and its size is the same - simply ignore it.
                continue
            else:
                # If the size has changed, it should be re-written
                # to the same location.
                if dir_id is None:
                    saved_path = msg.attachments.get(
                        message = msg, filename=attachment.filename).path
                    saved_path = saved_path.split('/')
                    dir_name, dir_id = saved_path[:2]

        f = save_attached_file(attachment, settings.MEDIA_ROOT,
            max_size=settings.ATTACHMENT_MAX_FILESIZE,
            dir_name=dir_name, dir_id=dir_id)
        if f['errors']:
            attachment_failed.extend(f['errors'])
            continue

        filename = f['path'].rsplit('/')[-1]
        filetype = f['path'].rsplit('.')[-1]
        try:
            pia_attachment, created = PIAAttachment.objects.get_or_create(
                message=msg, filename=filename, filetype=filetype, path=f['path'])
            pia_attachment.filesize = f['size']
            pia_attachment.save()
        except Exception as e:
            print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)

    if attachment_failed:
        return AppMessage('AttachSaveFailed').message % ', '.join(
            attachment_failed)
    else:
        return None # No news are good news.


def _do_remove_attachment(id_attachment):
    """
    Wipe out attachment file from the disk, and clean it from the draft record.
    """
    attachment_obj = PIAAttachment.objects.get(id=int(id_attachment))
    full_path = ('%s/attachments/%s' % (
        settings.MEDIA_ROOT, attachment_obj.path)).replace('//', '/')
    try:
        os.remove(full_path)
    except Exception as e:
        pass
    try:
        attachment_obj.delete()
    except:
        return e
    return None # No news are good news.


def remove_attachments(draft, id_list_remain=[], count_new=0):
    """
    Remove attachments unchecked by user.
    Return updated number of attachments allowed.
    In special case also return a directory name.
    """
    count_sofar = draft.attachments.count()
    count_remain = len(id_list_remain)

    # If there are attachments already, and more to be saved,
    # get the directory name. Do this before the removal,
    # because all attachments can be removed.
    dir_name = None
    if (count_sofar > 0) and (count_new > 0):
        dir_name = draft.attachments.all()[0].path.rsplit('/', 1)[0]

    # Number of allowed attachments is the difference
    # between what is allowed in settings and summary of new
    # and remained in the db.
    num_allowed = settings.ATTACHMENT_MAX_NUMBER - (count_new + count_remain)

    # Processing the only case when some attachments removed.
    # `count_remain == count_sofar` leaves everything as is.
    # `count_remain > count_sofar` is impossible.
    if count_remain < count_sofar:
        id_set_remain = set([int(i) for i in id_list_remain])
        id_set_sofar = set([int(a.id) for a in draft.attachments.all()])
        id_set_remove = id_set_sofar - id_set_remain
        for id_attach in id_set_remove:
            _do_remove_attachment(int(id_attach))
        
    return max(0, num_allowed), dir_name


def save_draft(data, **kwargs):
    """
    Saving a request or reply draft.
    `data` is a dict of values to be saved.

    Returns a dictionary of the structure:
    {
        'draft': <saved draft instance or None in case or errors>,
        'errors': <processing errors>,
        'attachments_allowed': <updated number of allowed attachments>
    }
    """
    d = data
    _r = ['body', 'subject', 'authority', 'attachments', 'attached']
    _u = ['body', 'subject']
    _id = d.pop('id', None)
    lookup_fields = dict((k, d[k]) for k in d.keys() if k not in _r)
    update_fields = dict((k, d[k]) for k in data.keys() if k in _u)

    # Update or create.
    if _id:
        try:
            draft = PIARequestDraft.objects.get(id=int(_id))
        except:
            print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)
    # All following exceptions are fatal, return with draft: None.
    else:
        try:
            draft = PIARequestDraft(**lookup_fields)
        except Exception as e:
            print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)
            return {'draft': None, 'errors': e}
    try:
        for k, v in update_fields.iteritems():
            setattr(draft, k, v)
    except Exception as e:
        print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)
        return {'draft': None, 'errors': e}
    try:
        draft.save()
    except Exception as e:
        print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)
        return {'draft': None, 'errors': e}

    # Maintain many-to-many link with Authority.
    draft.fill_authority(d['authority'])

    # Process attachments:
    # * delete from the db and disk those that are unchecked.
    attachments_allowed, dir_name = remove_attachments(draft,
        id_list_remain=d['attached'], count_new=len(d['attachments']))
    # * add to the db and save on disk newly attached.
    if dir_name is None:
        dir_name ='%s_%s' % (
            d['user'].get_full_name().strip().lower().replace(' ', '_'),
            'upload')
    attach_errors = process_attachments(draft, d['attachments'],
                                       dir_name=dir_name)
    if attach_errors:
        return {'draft': None, 'errors': attach_errors}
    return {'draft': draft, 'errors': attach_errors,
            'attachments_allowed': attachments_allowed}


def save_request_draft(request, draft_id=None, **kwargs):
    """
    Saving a draft whether it is a new request or an updated one.
    """
    draft_id = id
    draft = None
    similar_items = None
    template = kwargs.get('template', 'request.html')
    user_message = request.session.pop('user_message', {})
    form = MakeRequestForm(request.POST)
    attachments_allowed = settings.ATTACHMENT_MAX_NUMBER
    response = {'request_id': draft_id,
               'template': template,
               'attachments_allowed': attachments_allowed,
               'user_message': user_message}

    if form.is_valid():
        data = form.cleaned_data
        data.update({'attachments': dict(request.FILES).get('attachments', []),
                     'attached': dict(request.POST).get(u'attached_id', [])})
        if draft_id:
            data.update({'id': draft_id})

        result = save_draft(data)

        # Report.
        if result['errors']:
            user_message = update_user_message(user_message,
                                              result['errors'], 'fail')
        if result['draft']:
            draft = result['draft']
            draft_id = draft.id
            form = MakeRequestForm(instance=draft)
            attachments_allowed = result['attachments_allowed']
            if id: # Report only if it's draft save, not the first preview.
                user_message = update_user_message(user_message,
                    _(u'Draft saved successfully.'), 'success')
            # Try to find similar items.
            similar_items = retrieve_similar_items(draft, 20)
            # similar_items= more_like_this(result['draft'], 20)
    response.update({'form': form,
                     'draft': draft,
                     'request_id': draft_id,
                     'user_message': user_message,
                     'similar_items': similar_items,
                     'attachments_allowed': attachments_allowed})
    return response


def get_request_draft(request, r_id, **kwargs):
    """
    Return request draft data for display.
    """
    try:
        draft = PIARequestDraft.objects.get(pk=int(r_id))
    except:
        raise Http404
    if draft.thread_message:
        # This way would be "cleaner", but impossible to redirect
        # to #reply-draft, which is a draft form.
        #
        # return redirect(reverse('view_thread', args=(
        #     str(draft.thread_message.request.id),)))
        #
        return redirect('/request/%s/#form_reply' % str(
            draft.thread_message.request.id),)
    
    template = kwargs.get('template', 'request.html')
    user_message = request.session.pop('user_message', {})
    form = MakeRequestForm(instance=draft)
    return {'template': template, 'form': form,
            'request_id': r_id, 'user_message': user_message}


@login_required
def preview_request(request, r_id=None, **kwargs):
    """
    Preview request.
    If it's a new one, create a draft, otherwise (has ID) update it.
    """
    if request.method == 'POST':
        response_data = save_request_draft(request, r_id, **kwargs)
    elif request.method == 'GET':
        response_data = get_request_draft(request, r_id, **kwargs)
    if isinstance(response_data, dict):
        return render_to_response(response_data.pop('template'),
            response_data, context_instance=RequestContext(request))
    else:
        return response_data


def attach_files(message, draft):
    """
    Attaching files to EmailMessage from those specified in the Draft.
    """
    for attachment in draft.attachments.all():
        path = ('%s/attachments/%s' % (settings.MEDIA_ROOT,
                                      attachment.path)).replace('//', '/')
        try:
            message.attach_file(path)
        except Exception as e:
            print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)
            # TO-DO: register AppMessage('AttachFailed', value=(attachment.path, draft.id,).message
    return message

def ensure_attachments(message, draft):
    """
    Attaching files to PIARequestMessage from the Draft.
    """
    if draft.attachments.count() > 0:
        for attachment in draft.attachments.all():
            msg_attachmemnt = attachment
            msg_attachmemnt.id = None
            msg_attachmemnt.message = message
            try:
                msg_attachmemnt.save()
            except Exception as e:
                print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)
                # TO-DO: register AppMessage('AttachFailed', value=(attachment.path, draft.id,)).message
    return message


@login_required
def send_request(request, r_id=None, **kwargs):
    """ Processing the request to authority:

        * registers new request in the DB

        * sends the message to the selected Authorities (should always be a 
        list, even if it is a request to only one authority). The field `TO` 
        is being filled out according to the pattern:
        <user.name>.<user.last_name>.<request_id>@<domain>,
        where <request_id> is an ID of a newly created request.

        * successful e-mails are stored in `successful` dict, failed are in
        `failed` (if message sending failed, newly created request is deleted
        from the DB).

        * cleans the draft out, if everything went well.
        """
    if request.method != 'POST':
        raise Http404

    template = kwargs.get('template', 'request.html')

    # SCENARIO 1.
    # Discard the draft.
    if request.POST.get('discard_request_draft'):
        if r_id: # Saved draft (otherwise we just don't bother).
            if _do_discard_request_draft(int(r_id)):
                # result undefined
                user_message = update_user_message({}, AppMessage(
                    'DraftDiscardFailed', value=(r_id,)).message % result, 'fail')
                request.session['user_message'] = user_message
        # After discarding a draft redirect to User's Profile page.
        return redirect(reverse('user_profile', args=(request.user.id,)))

    # All the following scenarios require saving the draft first.
    data = save_request_draft(request, r_id, **kwargs)
    template = data.pop('template', template)

    # SCENARIO 2.
    # Only save the draft - it is in fact saved already, return the response.
    if request.POST.get('save_request_draft', None):
        return render_to_response(template, data,
                                  context_instance=RequestContext(request))

    # SCENARIO 3.
    # Send the message(s):
    # But first check if everything correct (data['draft'] is filled only
    # if the form is valid, and there are no other critical errors).
    if data['draft'] is None:
        return render_to_response(template, data,
                                  context_instance=RequestContext(request))

    # Initial list of authorities (can be changed after processing the draft).
    authorities = list(data['draft'].authority.all())

    # The process of sending a Request is looooong...

    # Prepare the message.
    # No newlines in Email subject!
    message_subject = ''.join(data['draft'].subject.splitlines())
    email_template = kwargs.get('email_template', 'emails/request_to_authority.txt')

    # Process draft - try to send message to every Authority in the Draft.
    successful, failed = list(), list()
    for authority in data['draft'].authority.all():
        email_to = authority.get_authority_email()
        if email_to is None:
            failed.append('%s: <a href="/authority/%s">%s</a>' % (
                AppMessage('AuthEmailNotFound').message, authority.name))
            continue

        pia_request = PIARequest.objects.create(
            summary=message_subject,
            authority=authority,
            user=request.user)
        reply_to = email_from_name(request.user.get_full_name(),
                                  id=pia_request.id, delimiter='.')
        email_from = settings.DEFAULT_FROM_EMAIL if settings.USE_DEFAULT_FROM_EMAIL else reply_to
        message_content = render_to_string(email_template, {
            'reply_to': reply_to,
            'content': data['draft'].body,
            'info_email': 'info@%s' % get_domain_name()})
        message_data = {'request': pia_request,
            'is_response': False,
            'email_to': email_to,
            'email_from': reply_to,
            'subject': message_subject,
            'body': message_content}
        message_request = EmailMessage(
            message_subject,
            message_content,
            email_from,
            [email_to],
            headers={'Reply-To': reply_to})

        # Attach files, if any.
        message_request = attach_files(message_request, data['draft'])

        try: # sending the message to the Authority, check if it doesn't fail.
            message_request.send(fail_silently=False)
        except Exception as e:
            try: # Wipe from the db, if it cannot be send.
                pia_request.delete()
            except:
                pass
            failed.append('<a href="/authority/%s">%s</a> (%s)' % (
                authority.slug, authority.name, e))
            continue

        # Create notifier - an author always follows its own request.
        create_request_notification(request.user,
                                    pia_request,
                                    pia_request.id,
                                    pia_request.summary[:50],
                                    request_events(pia_request))

        # Creating the 1st message in the thread.
        pia_msg = PIAThread.objects.create(**message_data)

        # Link the attachments from draft to the message created.
        pia_msg = ensure_attachments(pia_msg, data['draft'])

        successful.append('<a href="/authority/%s">%s</a>' % (
            authority.slug, authority.name))
        data['draft'].authority.remove(authority)

    # Update authorities - remove those that were successful,
    # or delete the draft if all successful.
    if len(failed) == 0:
        try: # Remove draft if nothing failed.
            data['draft'].delete()
        except Exception as e:
            failed.append(AppMessage('DraftRemoveFailed', value=(data['draft'].id,)).message % e)
    else:
        # Save updated Draft (unsuccessful Authorities already removed).
        try:
            data['draft'].save()
        except:
            pass
        # Update the form with updated instance of the Draft.
        form = MakeRequestForm(instance=data['draft'])

    # Report the results (ignore `save_draft` user messages).
    if successful:
        user_message = update_user_message({},
            _(u'Sent request(s) to: %s') % ', '.join(successful), 'success')
    if failed:
        user_message = update_user_message({},
            _(u'Request(s) sending failed: %s') % ', '.join(failed), 'fail')

    # Report the results to the user session.
    request.session['user_message'] = user_message
    data['user_message'] = user_message

    # Re-direct (depending on the Authorities and Failed status).
    if len(authorities) == len(successful): # All is good.
        if len(authorities) == 1:
            # Return to the Authority profile.
            return redirect(reverse('get_authority_info',
                                    args=(authorities[0].slug,)))
        else:
            # ... or to the list of Authorities in case of a mass message.
            return redirect(reverse('display_authorities'))
    else:
        # Some are not good - return to the draft page.
        return render_to_response(template, data,
            context_instance=RequestContext(request))


def retrieve_similar_items(obj, limit=None):
    """
    Retrieve items similar to the given one.
    """
    # WARNING!
    # This is a dirty way to get similar requests to the current one - via
    # search on its summary, but haystack doesn't properly process
    # elasticsearch `more_like_this` request.

    try: # Draft?
        text_for_search = obj.subject
    except:
        try: # Request?
            text_for_search = obj.summary
        except:
            try: # Thread?
                text_for_search = obj[0].request.summary
            except: # Give up...
                return []        

    text_for_search = downcode(clean_text_for_search(text_for_search.lower()))
    text_for_search = [d for d in text_for_search.split()]

    try:
        similar_items = SearchQuerySet().filter(summary__in=text_for_search)
    except:
        return []

    # If the search is performed on PIAThread, need to exclude the originator.
    _exclude_pk = None
    if isinstance(obj, PIARequest):
        _exclude_pk = obj.pk
    elif isinstance(obj, PIAThread):
        _exclude_pk = obj.request.pk
    if _exclude_pk:
        similar_items = [o for o in similar_items if o.object.pk != _exclude_pk]
 
    if limit:
        try:
            return similar_items[:int(limit)]
        except:
            pass
    return similar_items

def more_like_this(pia_request, limit=None):
    """
    Retrieve items similar to the given one.
    """
    # WARNING! Using `django_ct__exact` (haystack's internal field)
    # is a dirty trick, but the only working. Find better solution!
    similar_items = SearchQuerySet().more_like_this(pia_request).filter(
        django_ct__exact='pia_request.piarequest')
    if limit:
        try:
            return similar_items[:int(limit)]
        except:
            pass
    return similar_items

def awaiting_message(curr_user, request_user):
    """
    In case of 'awaiting classification' status, return a proper user_message.
    """
    if curr_user.is_anonymous():
        return AppMessage('ClassifyRespAnonim').message % {
            'user_id': request_user.pk,
            'user_name': request_user.get_full_name()
            }
    else:
        if request_user == curr_user:
            return AppMessage('ClassifyRespUser').message
        else:
            return AppMessage('ClassifyRespAlien').message

def view_thread(request, t_id=None, **kwargs):
    """
    View request thread by given ID.
    """
    template = kwargs.get('template', 'thread.html')
    form, mode = None, None
    if request.method == 'POST':
        raise Http404
    try:
        thread = PIAThread.objects.filter(request=PIARequest.objects.get(
            id=int(t_id))).order_by('created')
    except (PIAThread.DoesNotExist, PIARequest.DoesNotExist):
        raise Http404

    # Turning public attention to those 'awaiting classification'.
    user_message = request.session.pop('user_message', {})
    if thread[0].request.status == 'awaiting':
        update_user_message(user_message,
            awaiting_message(request.user, thread[0].request.user), 'success')

    # In case it is for print, we don't need any further details.
    is_print = request.GET.get('print', '')
    if is_print.lower() in settings.URL_PARAM_TRUE:
        mode = 'print'
        template = template.replace('.html', '_print.html')
        return render_to_response(template,
                                  {'form': form,
                                   'mode': mode,
                                   'request_id': t_id,
                                   'thread': thread,
                                   'user_message': user_message,
                                   'page_title': thread[0].request.summary[:50]},
            context_instance=RequestContext(request))

    attachments_allowed = request.session.pop('attachments_allowed',
                                             settings.ATTACHMENT_MAX_NUMBER)
    # Extract similar requests.
    similar_items = more_like_this(thread[0].request, 10)
    # similar_items= retrieve_similar_items(thread[0].request, 10)

    # If there's a draft in the thread, make a form.
    for msg in thread:
        try:
            draft = msg.draft
        except:
            continue
        if draft:
            form = ReplyDraftForm(instance=draft)
            mode = 'draft'
            break # Only one draft in Thread.

    # Check if the user is following the request.
    following = False
    if not request.user.is_anonymous():
        content_type_id = ContentType.objects.get_for_model(
            thread[0].request.__class__).id
        try:
            item = TaggedItem.objects.get(object_id=thread[0].request.id,
                                         content_type_id=content_type_id)
        except TaggedItem.DoesNotExist:
            pass
        else:
            following = item.is_followed_by(request.user)

    return render_to_response(template,
                              {'mode': mode,
                               'request_id': id,
                               'form': form,
                               'thread': thread,
                               'following': following,
                               'user_message': user_message,
                               'similar_items': similar_items,
                               'attachments_allowed': attachments_allowed,
                               'request_status': PIA_REQUEST_STATUS_VISIBLE,
                               'page_title': thread[0].request.summary[:50]},
        context_instance=RequestContext(request))

def download_thread(request, t_id=None, **kwargs):
    """
    Create a PDF from the print form of the thread, pack it into ZIP
    together with all the attached files, and return the archive.
    """
    template = kwargs.get('template', 'thread_print.html')
    if request.method == 'POST':
        raise Http404
    try:
        thread = PIAThread.objects.filter(request=PIARequest.objects.get(
            id=int(t_id))).order_by('created')
    except (PIAThread.DoesNotExist, PIARequest.DoesNotExist):
        raise Http404

    # Turning public attention to those 'awaiting classification'.
    user_message = request.session.pop('user_message', {})
    if thread[0].request.status == 'awaiting':
        update_user_message(user_message,
            awaiting_message(request.user, thread[0].request.user), 'success')

    data = {'request_id': t_id,
           'thread': thread,
           'mode': 'print',
           'form': None,
           'pagesize':'A4',
           'user_message': user_message,
           'title': thread[0].request.summary[:50]}
    pdf, pdf_content = render_to_pdf(template, data, context=RequestContext(request))

    if not pdf.err:
        basename = downcode(
            thread[0].request.summary[:40].strip().replace(' ','_').lower())
        zip_file = zip_thread(thread, pdf_content, basename)
        response = HttpResponse()
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename=%s.zip' % basename
        response.write(zip_file)
        return response
    # undefined html
    return HttpResponse(_(u'There are errors in the template <pre>%s</pre>') %\
                        cgi.escape(html))

def zip_thread(thread, pdf_content, basename):
    """
    Create a directory, copy there all attachments in the thread,
    name them uniquely, pack it all into Zip and serve as a file.
    """
    # Create a temp directory.
    a, d = settings.ATTACHMENT_DIR, settings.DOWNLOAD_ROOT
    save_to_path = d + id_generator()
    os.makedirs(save_to_path)
    # Save PDF there.
    filename = '%s/%s.pdf' % (save_to_path, basename)
    with open(filename, 'wb+') as destination:
        destination.write(pdf_content.getvalue())
    # Create zip file and add PDF there.
    in_memory = StringIO.StringIO()
    zip_f = zipfile.ZipFile(in_memory, 'a')
    zip_f.write(filename, arcname=basename+'.pdf')
    # Iterate through the thread's messages, copy attachments to `save_to_path`
    file_count = 1
    for msg in thread:
        if msg.attachments.count() == 0:
            continue
        for attachment in msg.attachments.all():
            re_name = '%d-%s' % (file_count, attachment.filename)
            try:
                zip_f.write(a + attachment.path, arcname=re_name)
            except Exception as e:
                print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)
            file_count += 1
    # Fix for Linux zip files read in Windows.
    for z_file in zip_f.filelist:
        z_file.create_system = 0
    zip_f.close()
    # Clean temp dir.
    rmtree(save_to_path, ignore_errors=True)
    in_memory.seek(0)
    return in_memory.read()


def similar_requests(request, r_id=None, **kwargs):
    """
    Browse requests, similar to the given one.
    """
    if request.method == 'POST':
        raise Http404
    if r_id is None:
        raise Http404
    try:
        rq = PIARequest.objects.get(pk=int(r_id))
    except:
        raise Http404
    user_message = request.session.pop('user_message', {})
    template = kwargs.get('template', 'search/search.html')
    form = ModelSearchForm(request.GET)

    initial, query, urlparams = process_filter_request(
        request, PIA_REQUEST_STATUS)

    similar_items = more_like_this(rq)

    paginator = Paginator(similar_items, settings.PAGINATE_BY)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        results = paginator.page(page)
    except (EmptyPage, InvalidPage):
        results = paginator.page(paginator.num_pages)

    return render_to_response(template,
                              {'page': results,
                               'query': rq.summary,
                               'urlparams': urlparams,
                               'user_message': user_message,
                               'form': PIAFilterForm(initial=initial),
                               'page_title': _(u'Browse similar requests')},
        context_instance=RequestContext(request))

@login_required
def reply_to_thread(request, t_id=None, **kwargs):
    """
    User's reply to the thread of the PIARequest with given ID:
    POST vs. GET processing.
    """
    template = kwargs.get('template', 'thread.html')
    user_message = request.session.pop('user_message', {})
    attachments_allowed = settings.ATTACHMENT_MAX_NUMBER
    is_response = request.GET.get('response', '')

    if is_response.lower() in settings.URL_PARAM_TRUE:
        is_response = True
        email_template = 'emails/authority_reply.txt'
    else:
        is_response = False
        email_template = 'emails/user_reply.txt'

    # Get the whole thread of messages.
    thread = PIAThread.objects.filter(
        request=PIARequest.objects.get(id=int(t_id))).order_by('created')

    # The last message in the thread (reference for annotations and replies!).
    msg = thread.reverse()[0]

    page_title = _(u'Reply to: ') + thread[0].request.summary[:50]

    if request.method == 'GET': # Show empty form to fill.
        if t_id is None:
            raise Http404
        initial = {'thread_message': msg,
                  'user': request.user, 'authority': [msg.request.authority],
                  'subject': re_subject(msg.subject),
                  'body': render_to_string(email_template,
                                           {'content': '',
                                            'authority_name': msg.request.authority.name,
                                            'last_msg_created': msg.created,
                                            'last_msg_email_from': msg.email_from,
                                            'last_msg_content': msg.body.replace('\n', '\n>> '),
                                            'info_email': 'info@%s' % get_domain_name()}),
                  'is_response': is_response,} # This one is particularly important!!!
                                               # It tells if e-mails should be
                                               # swapped in case User manually
                                               # enters reply from Authority.
        form = ReplyDraftForm(initial=initial)

        return render_to_response(template,
                                  {'form': form,
                                   'mode': 'reply',
                                   'thread': thread,
                                   'request_id': t_id,
                                   'user_message': user_message,
                                   'page_title': page_title,
                                   'request_status': PIA_REQUEST_STATUS_VISIBLE},
            context_instance=RequestContext(request))

    # Process the Reply form data.
    elif request.method == 'POST':
        form = ReplyDraftForm(request.POST)
        try: # Collect it before validation.
            draft_id = form.data['draft_id']
        except:
            draft_id = None

        # SCENARIO 1
        # User wants to discard the draft -> try to find the draft and
        # delete it. Redirect to view_thread.
        if request.POST.get('discard_reply_draft', None):
            if draft_id:
                try:
                    PIARequestDraft.objects.get(id=int(draft_id)).delete()
                except Exception as e:
                    pass
            return redirect(reverse('view_thread', args=(str(t_id),)))

        if not form.is_valid():
            # If form is invalid and user doesn't want to discard a draft.
            return render_to_response(template,
                                      {'form': form,
                                       'mode': 'reply',
                                       'thread': thread,
                                       'request_id': t_id,
                                       'page_title': page_title,
                                       'user_message': user_message,
                                       'attachments_allowed': attachments_allowed},
                context_instance=RequestContext(request))

        # Form is valid, process scenarios.
        # In case of any scenario the Draft must be saved first.
        data = form.cleaned_data
        data.update({'thread_message': msg,
                     'attachments': dict(request.FILES).get('attachments', []),
                     'attached': dict(request.POST).get(u'attached_id', [])})
        if draft_id:
            data.update({'id': draft_id})

        result = save_draft(data)

        # Report.
        if result['errors']:
            user_message = update_user_message(user_message,
                                              result['errors'], 'fail')
        if result['draft']:
            reply_draft = result['draft']
            user_message = update_user_message(user_message,
                                              _(u'Draft saved successfully.'), 'success')
            # Update number of allowed attachments.
            request.session['attachments_allowed'] = result['attachments_allowed']
        else:
            # Something went wrong while saving draft.
            request.session['user_message'] = user_message
            return redirect('/request/%s/#form_reply' % t_id)

        # SCENARIO 2
        # User only wants to save the draft -> redirect to the Thread view.
        if request.POST.get('save_reply_draft', None):
            request.session['user_message'] = user_message
            return redirect('/request/%s/#form_reply' % t_id)

        else:
            # Ignore anything said so far.
            user_message = {}

            # Used to distinguish answers of Authority manually entered by User.
            disclaimer = ''

            # SCENARIO 3
            # User wants to send the message -> collect data and attachments
            # from the saved draft, prepare message and send it.
            if request.POST.get('send_reply', None):
                email_to = msg.email_from if msg.is_response else msg.email_to
                email_from = email_from_name(reply_draft.user.get_full_name(),
                                            id=t_id, delimiter='.')
                _email_from = settings.DEFAULT_FROM_EMAIL if settings.USE_DEFAULT_FROM_EMAIL else email_from

                # Make and send email.
                reply = EmailMessage(reply_draft.subject,
                                    reply_draft.body,
                                    _email_from,
                                    [email_to],
                                    headers = {'Reply-To': email_from})
                reply = attach_files(reply, reply_draft) # Attachments from draft.

                try: # to send the message.
                    reply.send(fail_silently=False)
                except Exception as e:
                    user_message = update_user_message(user_message,
                        _(u'Error sending reply! System error: %s' % e), 'fail')
                    # If unsuccessful, all the data stays in the Draft.
                    request.session['user_message'] = user_message
                    return redirect('/request/%s/#form_reply' % t_id)

                # What will be reported if all operations done successfully.
                is_response = False
                success_message = _(u'Reply sent successfully.')

            # SCENARIO 4
            # User wants to save a reply from Authority manually.
            # All the data and attachments are already in the draft.
            elif request.POST.get('save_reply', None):
                # Swapping emails. Take `email_from` from AuthorityProfile,
                # since there were no real email, but PIAMessage requires one.
                email_to = email_from_name(reply_draft.user.get_full_name(),
                                          id=t_id, delimiter='.')
                email_from = msg.request.authority.email
                is_response = True
                disclaimer = AppMessage('DisclaimerManualReply').message % {
                        'auth': msg.request.authority.name,
                        'domain': get_domain_name()}
                success_message = _(u'Reply saved successfully.')

            # Common part of SCENARIOS 3 and 4
            # Save the message in the thread, re-link attachments, remove draft.
            message_data = {'request': msg.request,
                           'is_response': is_response,
                           'email_to': email_to,
                           'email_from': email_from,
                           'subject': reply_draft.subject,
                           'body': disclaimer + reply_draft.body}
            pia_msg = PIAThread(**message_data)
            try:
                pia_msg.save()
            except Exception as e:
                user_message = update_user_message(user_message,
                    _(u'Error saving message in the thread!'), 'fail')
                request.session['user_message'] = user_message
                return redirect('/request/%s/#form_reply' % t_id)
            # Re-link the attachments and delete the draft.
            if reply_draft.attachments.count() > 0:
                for attachment in reply_draft.attachments.all():
                    attachment.message = pia_msg
                    attachment.save()
            reply_draft.delete()
            # Report.
            user_message = update_user_message(user_message,
                                              success_message, 'success')
            request.session['user_message'] = user_message
            return redirect(reverse('view_thread', args=(str(t_id),)))


@login_required
def set_request_status(request, r_id=None, status_id=None, **kwargs):
    """
    Set new status to the request.
    """
    if r_id is None:
        raise Http404
    if (status_id is None) or status_id not in [k[0] for k in PIA_REQUEST_STATUS_VISIBLE]:
        raise Http404

    user_message = request.session.pop('user_message', {})
    pia_request = PIARequest.objects.get(id=int(r_id))

    if request.user != pia_request.user:
        user_message = update_user_message({},
            _(u'You cannot update status of the request made by other user!'),
            'fail')
    else:
        pia_request.status = status_id
        try:
            pia_request.save()
        except Exception as e:
            user_message = update_user_message({},
                _(u'Error updating status!'), 'fail')
        else:
            if status_id in ['successful', 'part_successful']:
                # Ask user if he/she wants to provide any additional details.
                user_message = update_user_message({},
                    AppMessage('AddDetailsToThread').message % {
                        'url': '/request/%s/reply/?response=true#form_reply' % r_id},
                    'success')
    request.session['user_message'] = user_message
    return redirect(reverse('view_thread', args=(str(r_id),)))


@login_required
def annotate_request(request, r_id=None, **kwargs):
    """
    User's reply to the thread of the PIARequest with given ID.
    """
    template = kwargs.get('template', 'thread.html')
    user_message = request.session.pop('user_message', {})

    # Get the whole thread of messages.
    thread = PIAThread.objects.filter(
        request =PIARequest.objects.get(id=int(r_id))).order_by('created')

    # The last message in the thread (reference for annotations and replies!).
    msg = thread.reverse()[0]
    
    page_title = _(u'Annotate request: ') + thread[0].request.summary[:50]

    if request.method == 'POST': # Process Comment form data.
        if request.POST.get('cancel_comment', None):
            # Cancel annotation - simply redirect back.
            return redirect(reverse('view_thread', args=(str(r_id),)))
        elif request.POST.get('post_comment', None):
            form = CommentForm(request.POST)
            if form.is_valid():
                # Save in the db, redirect to the Thread.
                try:
                    PIAAnnotation.objects.create(user=request.user,
                        thread_message = msg, body=form.cleaned_data['comment'])
                    return redirect(reverse('view_thread', args=(str(r_id),)))
                except Exception as e:
                    user_message = update_user_message({},
                        _(u'Cannot save annotation!'), 'fail')
            else:
                user_message = update_user_message({},
                    _(u'Draft saving failed! See details below.'), 'fail')

        return render_to_response(template,
            {'thread': thread, 'request_id': r_id, 'user_message': user_message,
            'form': form, 'page_title': page_title, 'mode': 'annotate',
            'request_status': PIA_REQUEST_STATUS_VISIBLE},
            context_instance=RequestContext(request))

    elif request.method == 'GET': # Show empty form to fill.
        if r_id is None:
            raise Http404

    return render_to_response(template,
                              {'thread': thread,
                               'request_id': r_id,
                               'user_message': user_message,
                               'page_title': page_title,
                               'mode': 'annotate',
                               'form': CommentForm(),
                               'request_status': PIA_REQUEST_STATUS_VISIBLE},
        context_instance=RequestContext(request))

@login_required
def report_request(request, r_id=None, **kwargs):
    """
    Report the request - sends mail to site admin
    and updates user message.
    """
    user_message = None
    if request.method == 'GET':
        user_message = update_user_message({},
                        AppMessage('ReportRequest').message % get_domain_name(),
                        'warning_yesno')
    elif request.method == 'POST':
        if request.POST.get('cancel', None):
            pass
        elif request.POST.get('proceed', None):
            if r_id is not None:
                rq = None
                try:
                    pia_request = PIARequest.objects.get(id=int(r_id))
                except (ValueError, PIARequest.DoesNotExist):
                    user_message = update_user_message({}, 'No such request!', 'fail')
                else:
                    subject = _(u'The request is reported to be offensive or unsuitable: ') + str(r_id)
                    email_template = kwargs.get('email_template', 'emails/report_request.txt')
                    message_content = render_to_string(email_template,
                                                      {'user': request.user,
                                                       'pia_request': pia_request},
                        context_instance=RequestContext(request))
                    headers = {'reply_to': request.user.email}
                    send_mail_managers(subject, message_content,
                                       headers=headers,
                                       fail_silently=False,
                                       connection=None)
                    user_message = update_user_message({},
                                    'The report sent to the managers!',
                                    'success')
    if user_message:
        request.session['user_message'] = user_message
    return redirect(request.META.get('HTTP_REFERER'))

def _do_discard_request_draft(draft):
    """
    Deleting draft from the db.
    Can receive a PIARequestDraft instance, but can also receive
    a Draft id.
    """
    if not isinstance(draft, PIARequestDraft):
        try:
            draft = PIARequestDraft.objects.get(pk=int(draft))
        except Exception as e:
            return e
    # Delete attachments from disk.
    if draft.attachments.count() > 0:
        for attachment in draft.attachments.all():
            full_path = ('%s/attachments/%s' % (
                settings.MEDIA_ROOT, attachment.path)).replace('//', '/')
            try:
                os.remove(full_path)
            except Exception as e:
                pass
    # Delete draft itself.
    try:
        draft.delete()
    except Exception as e:
        return e
    return None # No news are good news

@login_required
def discard_request_draft(request, r_id=None, **kwargs):
    """
    Discards a draft or a bunch of drafts. If id is omitted,
    the list of drafts to discard should be gathered from POST data.
    """
    if request.method != 'POST':
        raise Http404
    user_message = request.session.pop('user_message', {})
    draft_id_list = []
    if r_id:
        draft_id_list.append(r_id)
    else:
        try:
            draft_id_list.extend(dict(request.POST).get('draft_id', None))
        except TypeError: # Nothing selected.
            pass # No reaction.
    if draft_id_list:
        for draft_id in draft_id_list:
            if _do_discard_request_draft(draft_id):
                # result undefined
                request.session['user_message'] = update_user_message(
                    user_message,
                    AppMessage('DraftDiscardFailed',
                               value=(draft_id,)).message % result,
                    'fail')
    return redirect(request.META.get('HTTP_REFERER'))

def create_request_notification(user, obj, r_id, name, events):
    """
    Create notification for a request.
    """
    try:
        item = TaggedItem.objects.get(object_id=r_id,
                                     name=name,
                                     content_type_id=ContentType.objects.get_for_model(obj.__class__).id)
    except TaggedItem.DoesNotExist:
        item = TaggedItem.objects.create(name=name,
                                        content_object=obj)
    for k, v in events.iteritems():
        try:
            evnt, created = EventNotification.objects.get_or_create(
                item=item, action=k, receiver=user, summary=v)
        except:
            pass # TO-DO: Log it!
    return

@login_required
def follow_request(request, r_id=None, **kwargs):
    """
    Follow request.
    """
    if request.method == 'POST':
        return redirect(request.META.get('HTTP_REFERER'))
    if not r_id:
        raise Http404
    user_message = request.session.pop('user_message', {})
    
    piarequest = get_object_or_404(PIARequest, id=int(r_id))

    # Create notifier.
    create_request_notification(request.user,
                                piarequest,
                                piarequest.id,
                                piarequest.summary[:50],
                                request_events(piarequest))
    return redirect(request.META.get('HTTP_REFERER'))


@login_required
def unfollow_request(request, r_id=None, **kwargs):
    """
    Removes any activity of the Request from a notification list.
    """
    if request.method == 'POST':
        raise Http404
    piarequest = get_object_or_404(PIARequest, id=int(r_id))

    try: # to get notifier.
        item = TaggedItem.objects.get(object_id=piarequest.id,
            content_type_id=ContentType.objects.get_for_model(
                piarequest.__class__).id)
    except TaggedItem.DoesNotExist:
        return redirect(request.META.get('HTTP_REFERER'))

    for k, v in request_events(piarequest).iteritems():
        try:
            evnt = EventNotification.objects.get(item=item, action=k,
                                                receiver=request.user, summary=v)
        except EventNotification.DoesNotExist:
            continue
        evnt.delete()

    # Check if there is any notification connected to this item.
    if not EventNotification.objects.filter(item=item):
        try: # to wipe it out.
            item.delete()
        except:
            pass
    return redirect(request.META.get('HTTP_REFERER'))


def request_events(piarequest):
    """
    request event
    """

    return {'new_message': 'New message in the Thread of request %s' % piarequest,
            'annotation': 'Annotation to the message in the Thread of request %s' % piarequest}
