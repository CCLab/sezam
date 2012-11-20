from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext


def display_index(request, **kwargs):
    """
    Display index page.
    """
    template= kwargs.get('template', 'index.html')
    return render_to_response(template, {
        'page_title': _(u'Name')},
        context_instance=RequestContext(request))

