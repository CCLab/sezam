from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext
# from haystack.forms import HighlightedSearchForm
from haystack.query import SearchQuerySet

from apps.browser.forms import ModelSearchForm
from apps.pia_request.models import PIARequest
from apps.vocabulary.models import AuthorityProfile

def display_index(request, **kwargs):
    """
    Display index page.
    """
    template= kwargs.get('template', 'index.html')
    form= kwargs.get('form', ModelSearchForm)
    authority_list= AuthorityProfile.objects.all().order_by('-created')
    request_list= PIARequest.objects.all().order_by('-lastchanged')
    data= {'authority_list': authority_list[:20],
        'request_list': request_list[:10],
        'authorities_count': authority_list.count(),
        'requests_count': request_list.count()}
    return render_to_response(template, {'data': data, 'form': form,
        'page_title': _(u'Home')},
        context_instance=RequestContext(request))


# WARNING! Might be unnecessary!
def search_all(request, **kwargs):
    """
    Search over all or chosen data models.
    """
    try:
        q= request.GET['q']
    except:
        return redirect('/')
    template= kwargs.get('template', 'search/search.html')    
    form= ModelSearchForm(request.GET)
    user_message= request.session.pop('user_message', {})

    result= SearchQuerySet().auto_query(q)

    return render_to_response(template, {'result': result,
        'form': form, 'user_message': user_message,
        'page_title': _(u'Search')},
        context_instance=RequestContext(request))
