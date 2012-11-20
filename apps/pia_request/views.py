from django.shortcuts import get_object_or_404, render_to_response
from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext

from apps.vocabulary.models import AuthorityProfile
from apps.pia_request.models import PIARequestDraft
from apps.pia_request.forms import MakeRequestForm


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


def preview_request(request, id=None, **kwargs):
    """
    Preview request: if a new one, than create a draft, if with ID - update it.
    """
    template= kwargs.get('template', 'request.html')
    if request.method != 'POST':
        raise Http404
    form= MakeRequestForm(request.POST)

    # TO-DO: process non-valid form
    if form.is_valid():
        pass
    else:
        pass

    # Prepare initial values.
    try:
        initial= dict(tuple((k, v[0]) for k, v in dict(request.POST).iteritems()\
                        if k not in (u'csrfmiddlewaretoken', u'authority_slug')))
    except:
        initial= {}

    # Slugs should be saved in the list for the case
    # it is a draft of the request to several Authorities.
    if len(initial) > 0:
        initial.update({'authority_slug': eval(request.POST[u'authority_slug'])})
    authority= []
    try: # Try to find Authority.
        for slug in initial['authority_slug']:
            authority.append(AuthorityProfile.objects.get(slug=slug))
    except AuthorityProfile.DoesNotExist:
        raise Http404
    if request.user.is_anonymous():
        initial.update({'user_name': ''})
    else:
        initial.update({'user_name': request.user.get_full_name()})

    # TO-DO: process Anonymous User

    if id: # Already saved, need to be updated.
        piarequest_draft= PIARequestDraft.objects.get(id=int(id))
        piarequest_draft.subject= initial['request_subject']
        piarequest_draft.body= initial['request_body']
        piarequest_draft.authority_slug= initial['authority_slug']
    else:
        try:
            piarequest_draft= PIARequestDraft.objects.create(user=request.user,
                subject=initial['request_subject'], body=initial['request_body'],
                authority_slug=','.join(initial['authority_slug']))
        except Exception as e:
            pass # TO-DO: Process exception
    piarequest_draft.save()
    request_id= piarequest_draft.id

    return render_to_response(template, {
        'authority': authority, 'request_id': request_id,
        'form': MakeRequestForm(initial=initial)},
        context_instance=RequestContext(request))
