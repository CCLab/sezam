from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.core.mail import EmailMessage
from django.http import Http404
from django.conf import settings
from haystack.query import SearchQuerySet

import re
import os
from time import struct_time, strptime

from apps.pia_request.models import PIARequestDraft, PIARequest, PIAThread, PIAAnnotation, PIAAttachment, PIA_REQUEST_STATUS
from apps.pia_request.forms import MakeRequestForm, PIAFilterForm, ReplyDraftForm, CommentForm
from apps.browser.forms import ModelSearchForm
from apps.vocabulary.models import AuthorityProfile
from apps.backend import AppMessage
from apps.backend.models import TaggedItem, EventNotification
from apps.backend.utils import re_subject, process_filter_request,\
    downcode, save_attached_file, update_user_message,\
    get_domain_name, email_from_name, clean_text_for_search

def request_list(request, status=None, **kwargs):
    """
    Display list of the latest PIA requests.
    """
    if request.method == 'POST':
        raise Http404
    user_message= request.session.pop('user_message', {})
    template= kwargs.get('template', 'requests.html')

    initial, query, urlparams= process_filter_request(
        request, PIA_REQUEST_STATUS)

    # Query db.
    if query:
        pia_requests= PIARequest.objects.filter(**query)
    else:
        pia_requests= PIARequest.objects.all()

    paginator= Paginator(pia_requests, settings.PAGINATE_BY)
    try:
        page= int(request.GET.get('page', '1'))
    except ValueError:
        page= 1
    try:
        results= paginator.page(page)
    except (EmptyPage, InvalidPage):
        results= paginator.page(paginator.num_pages)

    return render_to_response(template, {'page': results,
        'form': PIAFilterForm(initial=initial), 'user_message': user_message,
        'page_title': _(u'View and search requests'), 'urlparams': urlparams},
        context_instance=RequestContext(request))


@login_required
def new_request(request, slug=None, **kwargs):
    """
    Display the form for making a request to the Authority (slug).
    """
    template= kwargs.get('template', 'request.html')
    if request.method == 'GET':
        try:
            authority= AuthorityProfile.objects.get(slug=slug)
        except AuthorityProfile.DoesNotExist:                
            raise Http404
        authority= [authority] # Result should always be a list.
    elif request.method == 'POST':
        # Multiple Authorities.
        authority_slug= dict(request.POST).get(u'authority_slug', None)
        authority= list()
        if authority_slug:
            for slug in authority_slug:
                try:
                    auth= AuthorityProfile.objects.get(slug=slug)
                except:
                    continue
                authority.append(auth)
        else: # Nothing selected.
            return redirect(request.META.get('HTTP_REFERER'))
    initial= {'authority': authority, 'user': request.user}
    return render_to_response(template, {
        'form': MakeRequestForm(initial=initial)},
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
    dir_name= kwargs.get('dir_name', 'undefined')
    dir_id= kwargs.get('dir_id', None)

    # Try to convert the last part of dir_name to time -
    # maybe we already have dir_id.
    dir_name_post_fix= dir_name.rsplit('/')
    if len(dir_name_post_fix) > 1:
        for substr in dir_name_post_fix[:2]:
            try:
                _dir_id= strptime(substr, '%d-%m-%Y_%H-%M')
            except ValueError:
                _dir_id= None
            if isinstance(_dir_id, struct_time):
                dir_id= substr
                break
    if dir_id: # If so, remove its part from dir_name.
        dir_name= dir_name.replace(dir_id, '').replace('//', '/')

    # attached_so_far= {f.filename: f.filesize for f in msg.attachments.all()}
    # This doesn't work in python 2.6, so:
    attached_so_far= {}
    for f in msg.attachments.all():
        attached_so_far.update({f.filename: f.filesize})

    attachment_failed= []
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
                    saved_path= msg.attachments.get(
                        message=msg, filename=attachment.filename).path
                    saved_path= saved_path.split('/')
                    dir_name, dir_id= saved_path[:2]

        f= save_attached_file(attachment, settings.MEDIA_ROOT,
            max_size=settings.ATTACHMENT_MAX_FILESIZE,
            dir_name=dir_name, dir_id=dir_id)
        if f['errors']:
            attachment_failed.append(f.name)
            continue

        filename= f['path'].rsplit('/')[-1]
        filetype= f['path'].rsplit('.')[-1]
        try:
            pia_attachment, created= PIAAttachment.objects.get_or_create(
                message=msg, filename=filename, filetype=filetype, path=f['path'])
            pia_attachment.filesize= f['size']
            pia_attachment.save()
        except Exception as e:
            print e

    if attachment_failed:
        return AppMessage('AttachSaveFailed').message % ', '.join(
            attachment_failed)
    else:
        return None # No news are good news.


def _do_remove_attachment(id_attachment):
    """
    Wipe out attachment file from the disk, and clean it from the draft record.
    """
    attachment_obj= PIAAttachment.objects.get(id=int(id_attachment))
    full_path= ('%s/attachments/%s' % (
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
    count_sofar= draft.attachments.count()
    count_remain= len(id_list_remain)

    # If there are attachments already, and more to be saved,
    # get the directory name. Do this before the removal,
    # because all attachments can be removed.
    dir_name= None
    if (count_sofar > 0) and (count_new > 0):
        dir_name= draft.attachments.all()[0].path.rsplit('/', 1)[0]

    # Number of allowed attachments is the difference
    # between what is allowed in settings and summary of new
    # and remained in the db.
    num_allowed= settings.ATTACHMENT_MAX_NUMBER - (count_new + count_remain)

    # Processing the only case when some attachments removed.
    # `count_remain == count_sofar` leaves everything as is.
    # `count_remain > count_sofar` is impossible.
    if count_remain < count_sofar:
        id_set_remain= set([int(i) for i in id_list_remain])
        id_set_sofar= set([int(a.id) for a in draft.attachments.all()])
        id_set_remove= id_set_sofar - id_set_remain
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
    d= data
    _r= ['body', 'subject', 'authority', 'attachments', 'attached']
    _u= ['body', 'subject']
    _id= d.pop('id', None)
    lookup_fields= dict((k, d[k]) for k in d.keys() if k not in _r)
    update_fields= dict((k, d[k]) for k in data.keys() if k in _u)

    # Update or create.
    if _id:
        try:
            draft= PIARequestDraft.objects.get(id=int(_id))
        except:
            pass
    # All following exceptions are fatal, return with draft: None.
    else:
        try:
            draft, created= PIARequestDraft.objects.get_or_create(
                **lookup_fields)
        except Exception as e:
            return {'draft': None, 'errors': e}
    try:
        for k, v in update_fields.iteritems():
            setattr(draft, k, v)
    except Exception as e:
        return {'draft': None, 'errors': e}
    try:
        draft.save()
    except Exception as e:
        return {'draft': None, 'errors': e}

    # Maintain many-to-many link with Authority.
    draft.fill_authority(d['authority'])

    # Process attachments:
    # * delete from the db and disk those that are unchecked.
    attachments_allowed, dir_name= remove_attachments(draft,
        id_list_remain=d['attached'], count_new=len(d['attachments']))
    # * add to the db and save on disk newly attached.
    if dir_name is None:
        dir_name='%s_%s' % (
            d['user'].get_full_name().strip().lower().replace(' ', '_'),
            'upload')
    attach_errors= process_attachments(draft, d['attachments'],
                                       dir_name=dir_name)
    return {'draft': draft, 'errors': attach_errors,
            'attachments_allowed': attachments_allowed}


def save_request_draft(request, id=None, **kwargs):
    """
    Saving a draft whether it is a new request or an updated one.
    """
    draft_id= id
    similar_items= None
    template= kwargs.get('template', 'request.html')
    user_message= request.session.pop('user_message', {})
    form= MakeRequestForm(request.POST)
    attachments_allowed= settings.ATTACHMENT_MAX_NUMBER
    response= {'request_id': draft_id, 'template': template,
               'attachments_allowed': attachments_allowed,
               'user_message': user_message}

    if form.is_valid():
        data= form.cleaned_data
        data.update({'attachments': dict(request.FILES).get('attachments', []),
                     'attached': dict(request.POST).get(u'attached_id', [])})
        if draft_id:
            data.update({'id': draft_id})

        result= save_draft(data)

        # Report.
        if result['errors']:
            user_message= update_user_message(user_message,
                                              result['errors'], 'fail')
        if result['draft']:
            draft_id= result['draft'].id
            form= MakeRequestForm(instance=result['draft'])
            attachments_allowed= result['attachments_allowed']
            if id: # Report only if it's draft save, not the first preview.
                user_message= update_user_message(user_message,
                    _(u'Draft saved successfully.'), 'success')
            # Try to find similar items.
            similar_items= retrieve_similar_items(result['draft'], 20)
    response.update({'request_id': draft_id, 'user_message': user_message,
        'form': form, 'attachments_allowed': attachments_allowed,
        'similar_items': similar_items})
    return response


def get_request_draft(request, id, **kwargs):
    """
    Return request draft data for display.
    """
    try:
        draft= PIARequestDraft.objects.get(pk=int(id))
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
    
    template= kwargs.get('template', 'request.html')
    user_message= request.session.pop('user_message', {})
    form= MakeRequestForm(instance=draft)
    return {'template': template, 'form': form,
            'request_id': id, 'user_message': user_message}


@login_required
def preview_request(request, id=None, **kwargs):
    """
    Preview request.
    If it's a new one, create a draft, otherwise (has ID) update it.
    """
    if request.method == 'POST':
        response_data= save_request_draft(request, id, **kwargs)
    elif request.method == 'GET':
        response_data= get_request_draft(request, id, **kwargs)
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
        path= ('%s/attachments/%s' % (settings.MEDIA_ROOT,
                                      attachment.path)).replace('//', '/')
        try:
            message.attach_file(path)
        except Exception as e:
            print AppMessage('AttachFailed', value=(attachment.path, draft.id,)).message
    return message

def ensure_attachments(message, draft):
    """
    Attaching files to PIARequestMessage from the Draft.
    """
    if draft.attachments.count() > 0:
        for attachment in draft.attachments.all():
            msg_attachmemnt= attachment
            msg_attachmemnt.id= None
            msg_attachmemnt.message= message
            try:
                msg_attachmemnt.save()
            except Exception as e:
                print AppMessage('AttachFailed', value=(attachment.path, draft.id,)).message
    return message


@login_required
def send_request(request, id=None, **kwargs):
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

    # SCENARIO 1.
    # Discard the draft.
    if request.POST.get('discard_request_draft'):
        if id: # Saved draft (otherwise we just don't bother).
            if _do_discard_request_draft(int(id)):
                user_message= update_user_message({}, AppMessage(
                    'DraftDiscardFailed', value=(id,)).message % result, 'fail')
                request.session['user_message']= user_message
        # After discarding a draft redirect to User's Profile page.
        return redirect(reverse('user_profile', args=(request.user.id,)))

    template= kwargs.get('email_template', 'emails/request_to_authority.txt')
    successful, failed= list(), list()

    # SCENARIO 2.
    # Only save the draft.
    if request.POST.get('save_request_draft'):
        response_data= save_request_draft(request, id, **kwargs)
        return render_to_response(response_data.pop('template'), response_data,
                                  context_instance=RequestContext(request))

    # SCENARIO 3.
    # Send the message(s).
    form= MakeRequestForm(request.POST)
    if form.is_valid():
        # Saving it for the purpose of processing the results.
        selected_authority= form.cleaned_data['authority']
        
        data= form.cleaned_data
        data.update({'attachments': dict(request.FILES).get('attachments', []),
                     'attached': dict(request.POST).get(u'attached_id', [])})
        if id:
            data.update({'id': id})

        result= save_draft(data)

        # Report.
        if result['errors']:
            user_message= update_user_message(user_message,
                                              result['errors'], 'fail')
        if result['draft']:
            message_draft= result['draft']
            # Update number of allowed attachments.
            request.session['attachments_allowed']= result['attachments_allowed']
        else:
            # Something went wrong while saving draft.
            request.session['user_message']= user_message
            return redirect(reverse('preview_request', args=(id,)))

        # No newlines in Email subject!
        message_subject = ''.join(message_draft.subject.splitlines())
        message_content= render_to_string(template,
            {'content': message_draft.body,
             'info_email': 'info@%s' % get_domain_name()})

        # Process draft - try to send message to every Authority in the Draft.
        for authority in message_draft.authority.all():
            try:
                email_to= authority.email
            except:
                failed.append('%s: <a href="/authority/%s">%s</a>' % (
                    AppMessage('AuthEmailNotFound').message, authority.name))
                continue
            pia_request= PIARequest.objects.create(summary=message_subject,
                authority=authority, user=request.user)
            reply_to= email_from_name(request.user.get_full_name(),
                                      id=pia_request.id, delimiter='.')
            email_from= settings.DEFAULT_FROM_EMAIL if settings.USE_DEFAULT_FROM_EMAIL else reply_to
            message_data= {'request': pia_request, 'is_response': False,
                           'email_to': email_to, 'email_from': reply_to,
                           'subject': message_subject, 'body': message_content}
            message_request= EmailMessage(message_subject, message_content,
                email_from, [email_to], headers={'Reply-To': reply_to})

            # Attach files, if any.
            message_request= attach_files(message_request, message_draft)

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
            # Creating the 1st message in the thread.
            pia_msg= PIAThread.objects.create(**message_data)

            # Link the attachments from draft to the message created.
            pia_msg= ensure_attachments(pia_msg, message_draft)

            successful.append('<a href="/authority/%s">%s</a>' % (
                authority.slug, authority.name))
            message_draft.authority.remove(authority)

        # Update authorities - remove those that were successful,
        # or delete the draft if all successful.
        if len(failed) == 0:
            try: # Remove draft if nothing failed.
                message_draft.delete()
            except Exception as e:
                failed.append(AppMessage('DraftRemoveFailed', value=(message_draft.id,)).message % e)
        else: # Save updated Draft (unsuccessful Authorities already removed).
            try:
                message_draft.save()
            except:
                pass # TO-DO: Log it!
            # Update the form with updated instance of the Draft.
            form= MakeRequestForm(instance=message_draft)
    else:
        return render_to_response(template, {'request_id': id, 'form': form,
            'attachments_allowed': attachments_allowed,
            'user_message': user_message},
            context_instance=RequestContext(request))

    # Report the results (ignore `save_draft` user messages).
    if successful:
        user_message= update_user_message({},
            _(u'Successfully sent request(s) to: %s') % ', '.join(successful),
            'success')
    if failed:
        user_message= update_user_message({},
            _(u'Request(s) sending failed: %s') % ', '.join(failed), 'fail')

    # Report the results to the user session.
    request.session['user_message']= user_message

    # Re-direct (depending on the Authorities and Failed status).
    if len(list(selected_authority)) == len(successful): # All is good.
        if len(list(selected_authority)) == 1: # Authority profile.
            return redirect(reverse('get_authority_info', args=(
                selected_authority[0].slug,)))
        else: # Or list of Authorities in case of a mass message.
            return redirect(reverse('display_authorities'))
    else:
        # Some are not good - return to the draft page.
        return render_to_response(template, {'request_id': id, 'form': form,
            'attachments_allowed': attachments_allowed,
            'user_message': user_message},
            context_instance=RequestContext(request))

def retrieve_similar_items(obj, limit=None):
    """
    Retrieve items similar to the given one.
    """
    # WARNING!
    # This is a dirty way to get similar requests to the current one - via
    # search on its summary, but haystack doesn't process elasticsearch's
    # `more_like_this` properly.

    similar_items= []
    text_for_search= None
    try: # Draft?
        text_for_search= obj.subject
    except:
        try: # Request?
            text_for_search= obj.summary
        except:
            try: # Thread?
                text_for_search= obj[0].request.summary
            except: # Give up...
                pass
    if not text_for_search:
        return similar_items

    text_for_search= downcode(clean_text_for_search(text_for_search.lower()))
    text_for_search= [d for d in text_for_search.split()]

    similar_items= SearchQuerySet().filter(summary__in=text_for_search)

    # If the search is performed on PIAThread, need to exclude this.
    _exclude_pk= None
    if isinstance(obj, PIARequest):
        _exclude_pk= obj.pk
    elif isinstance(obj, PIAThread):
        _exclude_pk= obj.request.pk
    if _exclude_pk:
        similar_items= [o for o in similar_items if o.object.pk != _exclude_pk]
 
    if limit:
        try:
            return similar_items[:int(limit)]
        except: pass
    return similar_items

def more_like_this(pia_request, limit=None):
    """
    Retrieve items similar to the given one.
    """
    # WARNING! Using `django_ct__exact` (haystack's internal foeld)
    # is a dirty trick, but the only working. Find better solution!
    similar_items= SearchQuerySet().more_like_this(pia_request).filter(
        django_ct__exact='pia_request.piarequest')
    if limit:
        try:
            return similar_items[:int(limit)]
        except: pass
    return similar_items


def view_thread(request, id=None, **kwargs):
    """
    View request thread by given ID.
    """
    template= kwargs.get('template', 'thread.html')
    if request.method == 'POST':
        raise Http404
    try:
        thread= PIAThread.objects.filter(request=PIARequest.objects.get(
            id=int(id))).order_by('created')
    except (PIAThread.DoesNotExist, PIARequest.DoesNotExist):
        raise Http404
    # Turning public attention to those 'awaiting classification'.
    user_message= request.session.pop('user_message', {})
    attachments_allowed= request.session.pop('attachments_allowed',
                                             settings.ATTACHMENT_MAX_NUMBER)
    if thread[0].request.status == 'awaiting':
        if request.user.is_anonymous():
            user_message= update_user_message(user_message,
                AppMessage('ClassifyRespAnonim').message % (
                    thread[0].request.user.pk,
                    thread[0].request.user.get_full_name()), 'success')
        else:
            if thread[0].request.user == request.user:
                user_message= update_user_message(user_message,
                    AppMessage('ClassifyRespUser').message, 'success')
            else:
                user_message= update_user_message(user_message,
                    AppMessage('ClassifyRespAlien').message, 'success')
    # similar_items= more_like_this(thread[0].request, 10)
    similar_items= retrieve_similar_items(thread[0].request, 10)

    # If there's a draft in the thread, make a form.
    form, mode= None, None
    for msg in thread:
        try:
            draft= msg.draft
        except:
            continue
        if draft:
            form= ReplyDraftForm(instance=draft)
            mode= 'draft'
            break # Only one draft in Thread.

    # Check if the user is following the request.
    following= thread[0].request.is_followed_by(request.user)

    return render_to_response(template, {'thread': thread, 'form': form,
        'similar_items': similar_items, 'user_message': user_message,
        'request_status': PIA_REQUEST_STATUS, 'request_id': id, 'mode': mode,
        'following': following, 'attachments_allowed': attachments_allowed,
        'page_title': thread[0].request.summary[:50]},
        context_instance=RequestContext(request))


def similar_requests(request, id=None, **kwargs):
    """
    Browse requests, similar to the given one.
    """
    if request.method == 'POST':
        raise Http404
    if id is None:
        raise Http404
    try:
        rq= PIARequest.objects.get(pk=int(id))
    except:
        raise Http404
    user_message= request.session.pop('user_message', {})
    template= kwargs.get('template', 'search/search.html')
    form= ModelSearchForm(request.GET)

    initial, query, urlparams= process_filter_request(
        request, PIA_REQUEST_STATUS)

    similar_items= more_like_this(rq)

    paginator= Paginator(similar_items, settings.PAGINATE_BY)
    try:
        page= int(request.GET.get('page', '1'))
    except ValueError:
        page= 1
    try:
        results= paginator.page(page)
    except (EmptyPage, InvalidPage):
        results= paginator.page(paginator.num_pages)

    return render_to_response(template, {'page': results, 'query': rq.summary,
        'form': PIAFilterForm(initial=initial), 'user_message': user_message,
        'page_title': _(u'Browse similar requests'),
        'urlparams': urlparams}, context_instance=RequestContext(request))


@login_required
def reply_to_thread(request, id=None, **kwargs):
    """
    User's reply to the thread of the PIARequest with given ID:
    POST vs. GET processing.
    """
    template= kwargs.get('template', 'thread.html')
    user_message= request.session.pop('user_message', {})
    attachments_allowed= settings.ATTACHMENT_MAX_NUMBER
    is_response= request.GET.get('response', '')

    if is_response.lower() in ['1', 'yes', 'y', 'tak', 'true']:
        is_response= True
        email_template= 'emails/authority_reply.txt'
    else:
        is_response= False
        email_template= 'emails/user_reply.txt'

    # Get the whole thread of messages.
    thread= PIAThread.objects.filter(
        request=PIARequest.objects.get(id=int(id))).order_by('created')

    # The last message in the thread (reference for annotations and replies!).
    msg= thread.reverse()[0]

    page_title= _(u'Reply to: ') + thread[0].request.summary[:50]

    if request.method == 'GET': # Show empty form to fill.
        if id is None:
            raise Http404
        initial= {'thread_message': msg,
                  'user': request.user, 'authority': [msg.request.authority],
                  'subject': re_subject(msg.subject),
                  'body': render_to_string(email_template, {
                      'authority_name': msg.request.authority.name,
                      'content': '', 'last_msg_created': msg.created,
                      'last_msg_email_from': msg.email_from,
                      'last_msg_content': msg.body.replace('\n', '\n>> '),
                      'info_email': 'info@%s' % get_domain_name()}),
                  'is_response': is_response,} # This one is special!!!
                                               # It tells if e-mails should be
                                               # swapped in case User manually
                                               # enters reply from Authority.
        form= ReplyDraftForm(initial=initial)

        return render_to_response(template, {'thread': thread,
            'request_id': id, 'user_message': user_message,
            'form': form, 'page_title': page_title, 'mode': 'reply',
            'request_status': PIA_REQUEST_STATUS},
            context_instance=RequestContext(request))

    # Process the Reply form data.
    elif request.method == 'POST':
        form= ReplyDraftForm(request.POST)
        try: # Collect it before validation.
            draft_id= form.data['draft_id']
        except:
            draft_id= None

        # SCENARIO 1
        # User wants to discard the draft -> try to find the draft and
        # delete it. Redirect to view_thread.
        if request.POST.get('discard_reply_draft', None):
            if draft_id:
                try:
                    PIARequestDraft.objects.get(id=int(draft_id)).delete()
                except Exception as e:
                    pass
            return redirect(reverse('view_thread', args=(str(id),)))

        if not form.is_valid():
            # If form is invalid and user doesn't want to discard a draft.
            return render_to_response(template, {'thread': thread,
                'request_id': id, 'form': form, 'page_title': page_title,
                'user_message': user_message, 'mode': 'reply',
                'attachments_allowed': attachments_allowed,},
                context_instance=RequestContext(request))

        # Form is valid, process scenarios.
        # In case of any scenario the Draft must be saved first.
        data= form.cleaned_data
        data.update({'thread_message': msg,
            'attachments': dict(request.FILES).get('attachments', []),
            'attached': dict(request.POST).get(u'attached_id', [])})
        if draft_id:
            data.update({'id': draft_id})

        result= save_draft(data)

        # Report.
        if result['errors']:
            user_message= update_user_message(user_message,
                                              result['errors'], 'fail')
        if result['draft']:
            reply_draft= result['draft']
            user_message= update_user_message(user_message,
                _(u'Draft saved successfully.'), 'success')
            # Update number of allowed attachments.
            request.session['attachments_allowed']= result['attachments_allowed']
        else:
            # Something went wrong while saving draft.
            request.session['user_message']= user_message
            return redirect('/request/%s/#form_reply' % id)

        # SCENARIO 2
        # User only wants to save the draft -> redirect to the Thread view.
        if request.POST.get('save_reply_draft', None):
            request.session['user_message']= user_message
            return redirect('/request/%s/#form_reply' % id)

        else:
            user_message= {} # Ignore anything said so far.

            # SCENARIO 3
            # User wants to send the message -> collect data and attachments
            # from the saved draft, prepare message and send it.
            if request.POST.get('send_reply', None):
                email_to= msg.email_from if msg.is_response else msg.email_to
                email_from= email_from_name(reply_draft.user.get_full_name(),
                                            id=id, delimiter='.')
                _email_from= settings.DEFAULT_FROM_EMAIL if settings.USE_DEFAULT_FROM_EMAIL else email_from

                # Make and send email.
                reply= EmailMessage(reply_draft.subject, reply_draft.body,
                    _email_from, [email_to], headers = {'Reply-To': email_from})
                reply= attach_files(reply, reply_draft) # Attachments from draft.

                try: # to send the message.
                    reply.send(fail_silently=False)
                except Exception as e:
                    user_message= update_user_message(user_message,
                        _(u'Error sending reply! System error: %s' % e), 'fail')
                    # If unsuccessful, all the data stays in the Draft.
                    request.session['user_message']= user_message
                    return redirect('/request/%s/#form_reply' % id)

                # If successful, collect data for saving
                # the message in the thread.
                message_data= {'request': msg.request, 'is_response': False,
                    'email_to': email_to, 'email_from': email_from,
                    'subject': reply_draft.subject, 'body': reply_draft.body}

                # What will be reported if all operations done successfully.
                success_message= _(u'Reply sent successfully.')

            # SCENARIO 4
            # User wants to save a reply from Authority manually.
            # All the data and attachments are already in the draft.
            elif request.POST.get('save_reply', None):
                # Swapping emails. Take `email_from` from AuthorityProfile,
                # since there were no real email, but PIAMessage requires one.
                email_to= email_from_name(reply_draft.user.get_full_name(),
                                          id=id, delimiter='.')
                email_from= msg.request.authority.email
                message_data= {'request': msg.request, 'is_response': True,
                    'email_to': email_to, 'email_from': email_from,
                    'subject': reply_draft.subject, 'body': reply_draft.body}
                success_message= _(u'Reply saved successfully.')

            # Common part of SCENARIOS 3 and 4
            # Save the message in the thread, re-link attachments, remove draft.
            pia_msg= PIAThread(**message_data)
            try:
                pia_msg.save()
            except Exception as e:
                user_message= update_user_message(user_message,
                    _(u'Error saving message in the thread! System error:')\
                    + e, 'fail')
                request.session['user_message']= user_message
                return redirect('/request/%s/#form_reply' % id)
            # Re-link the attachments and delete the draft.
            if reply_draft.attachments.count() > 0:
                for attachment in reply_draft.attachments.all():
                    attachment.message= pia_msg
                    attachment.save()
            reply_draft.delete()
            # Report.
            user_message= update_user_message(user_message,
                                              success_message, 'success')
            request.session['user_message']= user_message
            return redirect(reverse('view_thread', args=(str(id),)))


@login_required
def set_request_status(request, id=None, status_id=None, **kwargs):
    """
    Set new status to the request.
    """
    if id is None:
        raise Http404
    if (status_id is None) or status_id not in [k[0] for k in PIA_REQUEST_STATUS]:
        raise Http404

    user_message= request.session.pop('user_message', {})
    pia_request= PIARequest.objects.get(id=int(id))

    if request.user != pia_request.user:
        user_message= update_user_message({},
            _(u'You cannot update status of the request made by other user!'),
            'fail')
    else:
        pia_request.status=status_id
        try:
            pia_request.save()
        except Exception as e:
            user_message= update_user_message({},
                _(u'Error updating status!'), 'fail')
        else:
            if status_id in ['successful', 'part_successful']:
                # Ask user if he/she wants to provide any additional details.
                user_message= update_user_message({},
                    AppMessage('AddDetailsToThread').message % {
                        'url': '/request/%s/reply/?response=true#form_reply' % id},
                    'success')
    request.session['user_message']= user_message
    return redirect(reverse('view_thread', args=(str(id),)))


@login_required
def annotate_request(request, id=None, **kwargs):
    """
    User's reply to the thread of the PIARequest with given ID.
    """
    template= kwargs.get('template', 'thread.html')
    user_message= request.session.pop('user_message', {})

    # Get the whole thread of messages.
    thread= PIAThread.objects.filter(
        request=PIARequest.objects.get(id=int(id))).order_by('created')

    # The last message in the thread (reference for annotations and replies!).
    msg= thread.reverse()[0]
    
    page_title= _(u'Annotate request: ') + thread[0].request.summary[:50]

    if request.method == 'POST': # Process Comment form data.
        if request.POST.get('cancel_comment', None):
            # Cancel annotation - simply redirect back.
            return redirect(reverse('view_thread', args=(str(id),)))
        elif request.POST.get('post_comment', None):
            form= CommentForm(request.POST)
            if form.is_valid():
                # Save in the db, redirect to the Thread.
                try:
                    PIAAnnotation.objects.create(user=request.user,
                        thread_message= msg, body=form.cleaned_data['comment'])
                    return redirect(reverse('view_thread', args=(str(id),)))
                except Exception as e:
                    user_message= update_user_message({},
                        _(u'Cannot save annotation!'), 'fail')
            else:
                user_message= update_user_message({},
                    _(u'Draft saving failed! See details below.'), 'fail')

        return render_to_response(template,
            {'thread': thread, 'request_id': id, 'user_message': user_message,
            'form': form, 'page_title': page_title, 'mode': 'annotate',
            'request_status': PIA_REQUEST_STATUS},
            context_instance=RequestContext(request))

    elif request.method == 'GET': # Show empty form to fill.
        if id is None:
            raise Http404

    return render_to_response(template,
        {'thread': thread, 'request_id': id, 'user_message': user_message,
        'form': CommentForm(), 'page_title': page_title, 'mode': 'annotate',
        'request_status': PIA_REQUEST_STATUS},
        context_instance=RequestContext(request))    


def _do_discard_request_draft(draft):
    """
    Deleting draft from the db.
    Can receive a PIARequestDraft instance, but can also receive
    a Draft id.
    """
    if not isinstance(draft, PIARequestDraft):
        try:
            draft= PIARequestDraft.objects.get(pk=int(draft))
        except Exception as e:
            return e
    # Delete attachments from disk.
    if draft.attachments.count() > 0:
        for attachment in draft.attachments.all():
            full_path= ('%s/attachments/%s' % (
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
def discard_request_draft(request, id=None, **kwargs):
    """
    Discards a draft or a bunch of drafts. If id is omitted,
    the list of drafts to discard should be gathered from POST data.
    """
    if request.method != 'POST':
        raise Http404
    user_message= request.session.pop('user_message', {})
    draft_id_list= []
    if id:
        draft_id_list.append(id)
    else:
        try:
            draft_id_list.extend(dict(request.POST).get('draft_id', None))
        except TypeError: # Nothing selected.
            pass # No reaction.
    if draft_id_list:
        for draft_id in draft_id_list:
            if _do_discard_request_draft(draft_id):
                request.session['user_message']= update_user_message(
                    user_message, AppMessage('DraftDiscardFailed',
                    value=(draft_id,)).message % result, 'fail')
    return redirect(request.META.get('HTTP_REFERER'))

@login_required
def follow_request(request, id=None, **kwargs):
    """
    Follow request.
    """
    if request.method == 'POST':
        return redirect(request.META.get('HTTP_REFERER'))
    if not id:
        raise Http404
    user_message= request.session.pop('user_message', {})
    
    piarequest= get_object_or_404(PIARequest, id=int(id))
    if request.user == piarequest.user:
        request.session['user_message']= update_user_message(
            user_message, AppMessage('AuthorCantFollow').message, 'warning')
    else:
        # Create notifier.
        try:
            item= TaggedItem.objects.get(object_id=piarequest.id,
                name=piarequest.summary[:50],
                content_type_id=ContentType.objects.get_for_model(
                    piarequest.__class__).id)
        except TaggedItem.DoesNotExist:
            item= TaggedItem.objects.create(name=piarequest.summary[:50],
                                            content_object=piarequest)
        for k, v in request_events(piarequest).iteritems():
            try:
                evnt, created= EventNotification.objects.get_or_create(
                    item=item, action=k, receiver=request.user, summary=v)
            except:
                pass # TO-DO: Log it!        
    return redirect(request.META.get('HTTP_REFERER'))


def request_events(piarequest):
    return {'new_message': 'New message in the Thread of request %s' % piarequest,
            'annotation': 'Annotation to the message in the Thread of request %s' % piarequest}
