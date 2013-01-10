from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.core.mail import EmailMessage
from django.http import Http404
from haystack.query import SearchQuerySet

import re
import os
from time import struct_time, strptime

from apps.pia_request.models import PIARequestDraft, PIARequest, PIAThread, PIAAnnotation, PIAAttachment, PIA_REQUEST_STATUS
from apps.pia_request.forms import MakeRequestForm, PIAFilterForm, ReplyDraftForm, CommentForm
from apps.backend.utils import re_subject, process_filter_request, get_domain_name, email_from_name, clean_text_for_search, downcode, save_attached_file
from apps.backend import AppMessage
from apps.browser.forms import ModelSearchForm
from apps.vocabulary.models import AuthorityProfile
from sezam.settings import DEFAULT_FROM_EMAIL, USE_DEFAULT_FROM_EMAIL, PAGINATE_BY, MEDIA_ROOT, ATTACHMENT_MAX_FILESIZE, ATTACHMENT_MAX_NUMBER


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

    paginator= Paginator(pia_requests, PAGINATE_BY)
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

    attached_so_far= {f.filename: f.filesize for f in msg.attachments.all()}

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

        f= save_attached_file(attachment, MEDIA_ROOT,
            max_size=ATTACHMENT_MAX_FILESIZE, dir_name=dir_name, dir_id=dir_id)
        if f['errors']:
            attachment_failed.append(f.name)
            continue

        filename= f['path'].rsplit('/')[-1]
        filetype= f['path'].rsplit('.')[-1]
        err_msg= AppMessage('AttachFailed', value=(filename, msg.id,)).message
        try:
            pia_attachment, created= PIAAttachment.objects.get_or_create(
                message=msg, filename=filename, filetype=filetype, path=f['path'])
        except Exception as e:
            print err_msg
        pia_attachment.filesize= f['size']
        try:
            pia_attachment.save()
        except Exception as e:
            print err_msg

    if attachment_failed:
        return {'fail': 'Filed to save attachments: %s!' % \
                ', '.join(attachment_failed)}
    else:
        return {} # No news are good news.


def _do_remove_attachment(id_attachment):
    """
    Wipe out attachment file from the disk, and clean it from the draft record.
    """
    attachment_obj= PIAAttachment.objects.get(id=int(id_attachment))
    full_path= ('%s/attachments/%s' % (
        MEDIA_ROOT, attachment_obj.path)).replace('//', '/')
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
    num_allowed= ATTACHMENT_MAX_NUMBER - (count_new + count_remain)

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


@login_required
def save_request_draft(request, id=None, **kwargs):
    """
    Saving a draft whether it is a new request or an updated one.
    """
    request_id= id
    template= kwargs.get('template', 'request.html')
    user_message= request.session.pop('user_message', {})
    form= MakeRequestForm(request.POST)
    attachments_allowed= ATTACHMENT_MAX_NUMBER
    data= {'request_id': request_id, 'template': template,
           'attachments_allowed': attachments_allowed,
           'user_message': user_message}

    if form.is_valid():
        selected_authority= form.cleaned_data['authority']
        if selected_authority:
            params={
                'email_from': form.cleaned_data['email_from'],
                'email_to': form.cleaned_data['email_to'],
                'user': form.cleaned_data['user'],
                'body': form.cleaned_data['body'],
                'subject': ''.join(form.cleaned_data['subject'].splitlines())}

            if id: # Already saved, need to be updated.
                piarequest_draft= PIARequestDraft.objects.get(id=int(id))
                for k,v in params.iteritems():
                    setattr(piarequest_draft, k, v)
            else:
                piarequest_draft= PIARequestDraft(**params)

            try:
                piarequest_draft.save()
            except Exception as e:
                ex= AppMessage('DraftSaveFailed', value=(data,)).message % e
                user_message.update({'fail': ex})
                data.update({'user_message': user_message})
                return data

            piarequest_draft.authority.clear()
            for authority in selected_authority:
                piarequest_draft.authority.add(authority)

            request_id= piarequest_draft.id

            # For is initiated from instanse, so, it should be made after all
            # changes to the `piarequest_draft` are done!
            form= MakeRequestForm(instance=piarequest_draft)

            # Report about saving draft only if it was 'Save', not 'Preview'.
            if id:
                user_message.update({'success': _(
                    u'Draft successfully saved. You can send it now, \
                    or check other stuff on our web-site.')})

            # Process attachments.
            attachments= dict(request.FILES).get('attachments', [])

            # Delete from the db and disk those that are unchecked.
            attachments_allowed, dir_name= remove_attachments(piarequest_draft,
                id_list_remain=dict(request.POST).get(u'attached_id', []),
                count_new=len(attachments))

            # Add to the db and save on disk newly attached.
            if dir_name is None:
                dir_name='%s_%s' % (
                    request.user.get_full_name().strip().lower().replace(' ', '_'),
                    'upload')
                
            attach_report= process_attachments(piarequest_draft, attachments,
                                               dir_name=dir_name)
            user_message.update(attach_report)
    data.update({'request_id': request_id, 'user_message': user_message,
                 'attachments_allowed': attachments_allowed, 'form': form})
    return data


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
        try:
            message.attach_file('%s/attachments/%s' % (MEDIA_ROOT, attachment.path))
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

    # Check if we only should save the draft.
    if request.POST.get('save_request_draft'):
        response_data= save_request_draft(request, id, **kwargs)
        return render_to_response(response_data.pop('template'), response_data,
                                  context_instance=RequestContext(request))

    # Discard the draft.
    if request.POST.get('discard_request_draft'):
        if id: # Saved draft (otherwise we just don't bother).
            result= _do_discard_request_draft(int(id))
            if result != 'success':
                request.session['message']= AppMessage(
                    'DraftDiscardFailed', value=(id,)).message % result
        # After discarding a draft redirect to User's Profile page.
        return redirect(reverse('user_profile', args=(request.user.id,)))

    template= kwargs.get('email_template', 'emails/request_to_authority.txt')
    successful, failed= list(), list()

    form= MakeRequestForm(request.POST)
    if form.is_valid():
        # No newlines in Email subject!
        message_subject = ''.join(form.cleaned_data['subject'].splitlines())
        message_content= render_to_string(template, {
            'content': form.cleaned_data['body'],
            'info_email': 'info@%s' % get_domain_name()})

        message_draft= PIARequestDraft.objects.get(id=int(id))
        selected_authority= form.cleaned_data['authority']
        for authority in selected_authority:
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
            email_from= DEFAULT_FROM_EMAIL if USE_DEFAULT_FROM_EMAIL else reply_to
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
                # WARNING! Normally this should be done the following way:
                #     result= _do_discard_request_draft(message_draft)
                # But this would wipe out attachment files from disk, which
                # should stay in place, since they are attached to e-mail(s).
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

    # Report the results.
    user_message= {'success': None, 'fail': None}
    if successful:
        user_message['success']= _(
            u'Successfully sent request(s) to: %s') % ', '.join(successful)
    if failed:
        user_message['fail']= _(
            u'Request(s) sending failed: %s') % ', '.join(failed)

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
        response_data= save_request_draft(request, id, **kwargs)
        response_data.update({'form': form})
        return render_to_response(response_data.pop('template'), response_data,
                                  context_instance=RequestContext(request))


def retrieve_similar_items(pia_request, limit=None):
    """
    Retrieve items similar to the given one.
    """
    # WARNING!
    # This is a dirty way to get similar requests to the current one - via
    # search on its summary, but haystack's more_like_this doesn't work
    # properly.
    # [0:11] means that the request, by whose summary we're looking is also
    # somewhere in the result, so we have to exclude it, and to return
    # the rest 10.
    # text_for_search= downcode(clean_text_for_search(thread[0].request.summary))
    # similar_items= []
    # for res in sqs.raw_search(text_for_search)[0:11]:
    #     if res.object.pk != thread[0].request.pk:
    #         similar_items.append(res)

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
    user_message= {}
    if thread[0].request.status == 'awaiting':
        if request.user.is_anonymous():
            user_message.update({
                'success': AppMessage('ClassifyRespAnonim').message \
                % (thread[0].request.user.pk, \
                   thread[0].request.user.get_full_name())})
        else:
            if thread[0].request.user == request.user:
                user_message.update({
                    'success': AppMessage('ClassifyRespUser').message})
            else:
                user_message.update({
                    'success': AppMessage('ClassifyRespAlien').message})
    similar_items= retrieve_similar_items(thread[0].request, 10)

    # If there's a draft in the thread, create a form.
    form, mode= None, None
    for msg in thread:
        try:
            draft= msg.draft
        except:
            continue
        if draft:
            # initial= {'subject': msg.draft.subject, 'body': msg.draft.body}
            # form= ReplyDraftForm(initial=initial)
            initial= {'authority': msg.draft.authority, 'body': msg.draft.user,
                      'email_to': msg.draft.email_to, 'email_from': msg.draft.email_from}
            form= ReplyDraftForm(instance=draft, initial=initial)
            mode= 'draft'
            break # Only one draft in Thread.

    return render_to_response(template, {'thread': thread, 'form': form,
        'similar_items': similar_items, 'user_message': user_message,
        'request_status': PIA_REQUEST_STATUS, 'request_id': id, 'mode': mode,
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

    similar_items= retrieve_similar_items(rq)

    paginator= Paginator(similar_items, PAGINATE_BY)
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
    email_template= kwargs.get('email_template', 'emails/user_reply.txt')
    user_message= request.session.pop('user_message', {})

    # Get the whole thread of messages.
    thread= PIAThread.objects.filter(
        request=PIARequest.objects.get(id=int(id))).order_by('created')

    # The last message in the thread (reference for annotations and replies!).
    msg= thread.reverse()[0]
    
    page_title= _(u'Reply to: ') + '%s' % (thread[0].request.summary[:50])

    if request.method == 'POST': # Process the Reply form data.
        if request.POST.get('cancel_reply_draft', None):
            # Cancel reply - simply redirect back.
            return redirect(reverse('view_thread', args=(str(id),)))
        else:
            form= ReplyDraftForm(request.POST)

            if form.is_valid():
                initial= {'thread_message': msg,
                    'body': form.cleaned_data['body'],
                    'subject': form.cleaned_data['subject'],
                    'user': request.user.get_full_name(),
                    'authority': msg.request.authority}

                # Change the keys for proper search for the draft in the db.
                lookup_fields= initial.copy()
                del lookup_fields['subject'], lookup_fields['body']
                lookup_fields['user']= request.user

                if request.POST.get('send_reply', None):
                    try: # Remove the draft (if any).
                        PIARequestDraft.objects.get(**lookup_fields).delete()
                    except: # There was no draft.
                        pass

                    email_from= msg.email_to if msg.is_response else msg.email_from
                    email_to= msg.email_from if msg.is_response else msg.email_to
                    message_data= {'request': msg.request, 'is_response': False,
                        'email_to': email_to, 'email_from': email_from,
                        'subject': initial['subject'], 'body': initial['body']}

                    _email_from= DEFAULT_FROM_EMAIL if USE_DEFAULT_FROM_EMAIL else email_from
                        
                    reply= EmailMessage(initial['subject'], initial['body'],
                        _email_from, [email_to], headers = {'Reply-To': email_from})
                    try: # to send the message.
                        reply.send(fail_silently=False)
                        # Save a new message in the thread.
                        pia_msg= PIAThread.objects.create(**message_data)
                        user_message= {'success': _(u'Reply sent successfully')}
                        # Redirect to see the updated thread
                        return redirect(reverse('view_thread', args=(str(id),)))
                    except Exception as e:
                        user_message= {'fail': _(u'Error sending reply!')}

                elif request.POST.get('save_reply_draft', None):

                    # Save the draft in the db and return to the same page.
                    authority= lookup_fields.pop('authority')
                    reply_draft, created= PIARequestDraft.objects.get_or_create(
                        **lookup_fields)
                    reply_draft.body= initial['body']
                    reply_draft.subject= initial['subject']
                    reply_draft.authority.add(authority)
                    reply_draft.save()
                    user_message= {'success': _(u'Draft saved')}

                    # Process attachments.
                    attachments= dict(request.FILES).get('attachments', [])
                    dir_name='%s_%s' % (
                        request.user.get_full_name().strip().lower().replace(' ', '_'),
                        'upload')
                    attach_report= process_attachments(reply_draft, attachments,
                                                       dir_name=dir_name)
                    user_message.update(attach_report)
            else:
                user_message= {'fail': _(u'Draft saving failed! See details below.')}

            return render_to_response(template, {'thread': thread,
                'request_id': id, 'form': form, 'page_title': page_title,
                'user_message': user_message, 'mode': 'reply'},
                context_instance=RequestContext(request))

    elif request.method == 'GET': # Show empty form to fill.
        if id is None:
            raise Http404
        initial= {
            'user': request.user, 'authority': [msg.request.authority],
            'subject': re_subject(msg.subject),
            'body': render_to_string(email_template, {
                'content': '', 'last_msg_created': msg.created,
                'last_msg_email_from': msg.email_from,
                'last_msg_content': msg.body.replace('\n', '\n>> '),
                'info_email': 'info@%s' % get_domain_name()})}
        reply_draft= PIARequestDraft()

        return render_to_response(template,
            {'thread': thread, 'request_id': id, 'user_message': user_message,
            'form': ReplyDraftForm(initial=initial), 'page_title': page_title,
            'mode': 'reply', 'request_status': PIA_REQUEST_STATUS},
            context_instance=RequestContext(request))


@login_required
def set_request_status(request, id=None, status_id=None, **kwargs):
    """
    Set new status to the request.
    """
    if id is None:
        raise Http404
    if (status_id is None) or status_id not in [k[0] for k in PIA_REQUEST_STATUS]:
        raise Http404

    try:
        PIARequest.objects.filter(id=int(id)).update(status=status_id)
    except Exception as e:
        user_message= {'fail': _(u'Cannot update status!')}

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
                    user_message= {'fail': _(u'Cannot save annotation!')}
            else:
                user_message= {'fail': _(u'Draft saving failed! See details below.')}

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
                MEDIA_ROOT, attachment.path)).replace('//', '/')
            try:
                os.remove(full_path)
            except Exception as e:
                pass
    # Delete draft itself.
    try:
        draft.delete()
    except Exception as e:
        return e
    return 'success'
    

@login_required
def discard_request_draft(request, id=None, **kwargs):
    """
    Discards a draft or a bunch of drafts. If id is omitted,
    the list of drafts to discard should be gathered from POST data.
    """
    if request.method != 'POST':
        raise Http404
    message= request.session.pop('message', [])
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
            result= _do_discard_request_draft(draft_id)
            if result != 'success':
                ex= AppMessage('DraftDiscardFailed', value=(draft_id,)).message % result
                request.session['message']= ex
    return redirect(request.META.get('HTTP_REFERER'))
