from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext

from apps.pia_request.models import PIARequest
from apps.vocabulary.models import AuthorityProfile
from apps.backend.utils import get_domain_name

def display_index(request, **kwargs):
    """ Display index page.
        """
    template= kwargs.get('template', 'index.html')
    authority_list= AuthorityProfile.objects.all().order_by('-created')
    request_list= PIARequest.objects.all().order_by('-created')
    data= {'authority_list': authority_list[:20],
        'request_list': request_list[:10],
        'authorities_count': authority_list.count(),
        'requests_count': request_list.count()}
    return render_to_response(template, {'data': data,
        'page_title': _(u'Home') + ' - ' + get_domain_name()},
        context_instance=RequestContext(request))

