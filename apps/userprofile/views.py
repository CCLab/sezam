from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.template import RequestContext
from django.http import Http404

from apps.vocabulary.models import UserProfile
from apps.pia_request.models import PIARequest, PIA_REQUEST_STATUS
from apps.pia_request.forms import PIAFilterForm
from apps.backend.utils import process_filter_request, handle_image, get_domain_name
from forms import UserProfileForm, UserpicForm

from sezam.settings import MEDIA_ROOT, THUMBNAIL_SIZE


def user_profile(request, id=None, **kwargs):
    """ Show user's full profile.
        
        If this user is logged on and she's asking about her own profile,
        show private profile info and request drafts.
        
        Otherwise display public profile (name, when joined), lists of requests
        made by user so far, and annotations made by user.
        """
    if request.method == 'POST':
        raise Http404
    user_message= request.session.pop('user_message', {})
    template= kwargs.get('template', 'user.html')
    profile= kwargs.get('profile', False)

    if id is None:
        raise Http404

    user= get_object_or_404(User, pk=int(id))
    if profile:
        try:
            user_profile, created= UserProfile.objects.get_or_create(user=user)
        except Exception as e:
            pass # TO-DO: Log it!
    else:
        user_profile= {}

    # Fill requests list.
    initial, query, urlparams= process_filter_request(
            request, PIA_REQUEST_STATUS)
    query.update({'user': user})

    if query:
        pia_requests= PIARequest.objects.filter(**query)
    else:
        pia_requests= list()

    return render_to_response(template, { 'usr': user,
        'user_profile': user_profile, 'user_message': user_message,
        'pia_requests': pia_requests, 'urlparams': urlparams,
        'form': PIAFilterForm(initial=initial),
        'page_title': _(u"User's profile") + ' - ' + get_domain_name()},
        context_instance=RequestContext(request))


def user_profile_update(request, id=None, **kwargs):
    """ Show/process form for user's profile update.
        """
    user_message= request.session.pop('user_message', {})
    template= kwargs.get('template', 'user.html')

    # Retrieve user's profile from db.
    user= get_object_or_404(User, pk=int(id))
    try:
        user_profile, created= UserProfile.objects.get_or_create(user=user)
    except Exception as e:
        pass # TO-DO: Log it!
            
    if request.method == 'POST':
        # Save changes.
        if request.POST.get('save_changes', None):
            form= UserProfileForm(request.POST, instance=user_profile)
            if form.is_valid():
                try:
                    user_profile= form.save()
                    return redirect(reverse('user_profile', args=(str(id),)))
                except Exception as e: # Do nothing, simply return the form with errors
                    user_message= {'fail': _('Failed to update user profile.')}
            else:
                user_message= {'fail': _('Correct the errors: ')}
    elif request.method == 'GET':
        form= UserProfileForm(instance=user_profile)

    return render_to_response(template, {'user_message': user_message,
        'user_profile': user_profile, 'form': form,
        'page_title': _(u"User's profile") + ' - ' + get_domain_name()},
        context_instance=RequestContext(request))


def user_set_userpic(request, id=None, **kwargs):
    """
    Update userpic.
    """
    template= kwargs.get('template', 'user.html')
    user_message= request.session.pop('user_message', {})

    # Retrieve user's profile from db.
    user= get_object_or_404(User, pk=int(id))

    if request.method == 'POST':
        # Save changes.
        form= UserpicForm(request.POST)
        if request.POST.get('submit_userpic', None):
            file_path= request.FILES.get('file_path', None)
            if file_path:
                try:
                    user.profile.userpic= handle_image(file_path, MEDIA_ROOT,
                        thumbnail_size=THUMBNAIL_SIZE)
                    user.profile.save()
                    return redirect(reverse('user_profile', args=(str(id),)))
                except Exception as e:
                    print e
                    user_message= {'fail': _('Failed to update userpic.')}
            else:
                user_message= {'fail': _('Correct the errors: ')}
        else:
            return redirect(reverse('user_profile', args=(str(id),)))
    elif request.method == 'GET':
        form= UserpicForm()

    return render_to_response(template, {'user_message': user_message,
        'form': form, 'page_title': _(u"User's profile") + ' - ' + get_domain_name()},
        context_instance=RequestContext(request))