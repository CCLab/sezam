from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.core.mail import EmailMessage
from django.http import Http404

import re

from apps.pia_request.models import PIARequestDraft, PIARequest, PIAThread, PIAAnnotation, PIA_REQUEST_STATUS
from apps.pia_request.forms import MakeRequestForm, PIAFilterForm, ReplyDraftForm, CommentForm
from apps.backend.utils import re_subject, process_filter_request, get_domain_name, email_from_name
from apps.backend import AppMessage
from apps.vocabulary.models import AuthorityProfile
from sezam.settings import DEFAULT_FROM_EMAIL


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

    return render_to_response(template, {'pia_requests': pia_requests,
        'form': PIAFilterForm(initial=initial), 'user_message': user_message,
        'page_title': _(u'View and search requests') + ' - ' + get_domain_name(),
        'urlparams': urlparams}, context_instance=RequestContext(request))


@login_required
def new_request(request, slug=None, **kwargs):
    """
    Display the form for making a request to the Authority (slug).
    """
    template= kwargs.get('template', 'request.html')
    initial= {}
    if request.method == 'GET':
        try: # Try to find Authority.
            authority= AuthorityProfile.objects.get(slug=slug)
        except AuthorityProfile.DoesNotExist:                
            raise Http404
        initial.update({'authority_slug': [authority.slug]})
        if authority.official_lastname:
            initial.update({'authority_name': '%s %s' % (
                authority.official_name, authority.official_lastname)})
        else:
            initial.update({'authority_name': authority.name})
        authority= [authority] # Result should always be a list.
    else:

        # TO-DO: reaction for POST here (several Authorities).
        initial.update({'authority_name': ' ', 'authority_slug': ' '})
    if request.user.is_anonymous():
        initial.update({'user_name': ''})
    else:
        initial.update({'user_name': request.user.get_full_name()})
    return render_to_response(template, {
        'authority': authority, 'form': MakeRequestForm(initial=initial)},
        context_instance=RequestContext(request))


@login_required
def save_request_draft(request, id=None, **kwargs):
    """
    Saving a draft whether it is a new request or an updated one.
    """
    template= kwargs.get('template', 'request.html')
    if request.method != 'POST':
        raise Http404
    form= MakeRequestForm(request.POST)
    user_message= request.session.pop('user_message', {})

    # Slugs should be saved in the list for the case
    # it is a draft of the request to several Authorities.
    try:
        authority_slug= eval(request.POST[u'authority_slug'])
    except:
        authority_slug= []
    authority= []
    try: # Try to find Authority.
        for slug in authority_slug:
            authority.append(AuthorityProfile.objects.get(slug=slug))
    except AuthorityProfile.DoesNotExist:
        raise Http404

    if form.is_valid():
        if id: # Already saved, need to be updated.
            piarequest_draft= PIARequestDraft.objects.get(id=int(id))
            piarequest_draft.subject= form.cleaned_data['request_subject']
            piarequest_draft.body= form.cleaned_data['request_body']
            piarequest_draft.authority_slug= ','.join(authority_slug)
        else:
            try:
                piarequest_draft= PIARequestDraft.objects.create(
                    user=request.user, authority_slug=','.join(authority_slug),
                    subject=form.cleaned_data['request_subject'],
                    body=form.cleaned_data['request_body'])
            except Exception as e:
                pass # TO-DO: Process exceptions (for example anonymous user)
        piarequest_draft.save()
        request_id= piarequest_draft.id
    else:
        request_id= None

    return {'template': template, 'form': form, 'authority': authority,
            'request_id': request_id, 'user_message': user_message}


def get_request_draft(request, id, **kwargs):
    """
    Return request draft data for display.
    """
    template= kwargs.get('template', 'request.html')
    user_message= request.session.pop('user_message', {})
    try:
        draft= PIARequestDraft.objects.get(pk=id)
    except:
        raise Http404
    initial={'authority_slug': draft.authority_slug,
             'request_subject': draft.subject, 'request_body': draft.body,
             'authority_name': '', 'user_name': ''}
    authority_slug_list= draft.authority_slug.split(',')
    authority= []
    try: # Try to find Authority.
        for slug in authority_slug_list:
            authority.append(AuthorityProfile.objects.get(slug=slug))
    except AuthorityProfile.DoesNotExist:
        raise Http404
    form= MakeRequestForm(initial=initial)
    return {'template': template, 'form': form, 'authority': authority,
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
    return render_to_response(response_data.pop('template'), response_data,
        context_instance=RequestContext(request))


@login_required
def send_request(request, id=None, **kwargs):
    """ Processing the request to authority:

        * registers new request in the DB

        * sends the message to the selected Authorities (should always be a 
        list, even if it is a request to only one authority). The field `TO` 
        is being filled out according to the pattern:
        request-<request-id>@<domain>,
        where <request_id> is an ID of a newly created request.

        * successful e-mails are stored in `successful` dict, failed are in
        `failed` (if message sending failed, newly created request is deleted
        from the DB).

        * cleans the draft out.
        """
    if request.method != 'POST':
        raise Http404

    # Check if we only should save the draft.
    if request.POST.get('save_request_draft'):
        response_data= save_request_draft(request, id, **kwargs)
        return render_to_response(response_data.pop('template'), response_data,
                                  context_instance=RequestContext(request))
    template= kwargs.get('email_template', 'emails/request_to_authority.txt')

    # No newlines in Email subject!
    message_subject = ''.join(request.POST.get('request_subject').splitlines())
    message_content= render_to_string(template, {
        'content': request.POST.get('request_body', ''),
        'info_email': 'info@%s' % get_domain_name()})

    # Convert to a list.
    authority_slug= eval(request.POST.get('authority_slug'))

    successful, successful_slugs, failed= list(), set(), list()
    for slug in authority_slug:
        # Collect the information for the e-mail message and the message in
        # PIAThread, specific for the current authority.
        # PIARequest is being created first to get its id, which is a part of
        # the `reply-to` field in the message header (however it is becoming
        # `from` in the PIAThread message).
        # `from` field looks like this: name.surname.request_id@domain.name
        # If for some reason sending the request fails, it is being removed from
        # the db.
        authority= AuthorityProfile.objects.get(slug=slug)
        try:
            email_to= authority.email
        except:
            failed.append('%s: <a href="/authority/%s">%s</a>' % (
                AppMessage('AuthEmailNotFound').message,
                authority.slug, authority.name))
            continue
        pia_request= PIARequest.objects.create(summary= message_subject,
            authority=authority, user=request.user)
        email_from= email_from_name(request.user.get_full_name(),
                                    id=pia_request.id, delimiter='.')
        message_data= {'request': pia_request, 'is_response': False,
                       'email_to': email_to, 'email_from': email_from,
                       'subject': message_subject, 'body': message_content}
        message_request= EmailMessage(message_subject, message_content,
            DEFAULT_FROM_EMAIL, [email_to], headers = {'Reply-To': email_from})
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
        successful.append('<a href="/authority/%s">%s</a>' % (
            authority.slug, authority.name))
        successful_slugs.add(authority.slug)

    message_draft= PIARequestDraft.objects.get(id=int(id))
    if len(authority_slug) == len(successful):
        try: # Remove draft if nothing failed.
            message_draft.delete()
        except:
            pass # TO-DO: Log it!
    elif len(authority_slug) == len(failed):
        pass # This doesn't affect the draft - it stays the same.
    else: # Remove from the draft those slugs that were successful.
        draft_slugs= set(message_draft.authority_slug.split(','))
        message_draft.authority_slug= ','.join(
            list(draft_slugs - successful_slugs))
        try:
            message_draft.save()
        except:
            pass # TO-DO: Log it!

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
    if len(authority_slug) == len(failed):
        # If all are failed, return to the draft page.
        response_data= save_request_draft(request, id, **kwargs)
        return render_to_response(response_data.pop('template'), response_data,
                                  context_instance=RequestContext(request))
    else: # Otherwise:
        if len(authority_slug) == 1: # Authority profile.
            return redirect(reverse('get_authority_info', args=(authority_slug[0],)))
        else: # Or list of Authorities in case of a mass message.
            return redirect(reverse('display_authorities'))


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
    return render_to_response(template, {'thread': thread,
        'user_message': user_message, 'request_status': PIA_REQUEST_STATUS,
        'request_id': id, 'form': None, 'page_title': '%s - %s' % (
            thread[0].request.summary[:50], get_domain_name())},
        context_instance=RequestContext(request))


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
    
    page_title= _(u'Reply to the request: ') + ' - ' + '%s - %s' % (
        thread[0].request.summary[:50], get_domain_name())

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
                    'authority_slug': msg.request.authority.slug}

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
                    reply= EmailMessage(initial['subject'], initial['body'],
                                        DEFAULT_FROM_EMAIL, [email_to],
                                        headers = {'Reply-To': email_from})
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
                    reply_draft, created= PIARequestDraft.objects.get_or_create(
                        **lookup_fields)
                    reply_draft.body= initial['body']
                    reply_draft.subject= initial['subject']
                    reply_draft.save()

                    user_message= {'success': _(u'Draft saved')}
            else:
                user_message= {'fail': _(u'Draft saving failed! See details below.')}

            return render_to_response(template, {'thread': thread,
                'request_id': id, 'form': form, 'page_title': page_title,
                'user_message': user_message, 'mode': 'reply'},
                context_instance=RequestContext(request))

    elif request.method == 'GET': # Show empty form to fill.
        if id is None:
            raise Http404
        initial= {'subject': re_subject(msg.subject),
            'body': render_to_string(email_template, {
                'content': '', 'last_msg_created': msg.created,
                'last_msg_email_from': msg.email_from,
                'last_msg_content': msg.body.replace('\n', '\n>> '),
                'info_email': 'info@%s' % get_domain_name()})}

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
    
    page_title= _(u'Annotate request: ') + ' - ' + '%s - %s' % (
        thread[0].request.summary[:50], get_domain_name())

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
