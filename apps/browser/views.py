from django.shortcuts import render_to_response
from django.template import RequestContext

def display_index(request, **kwargs):
    """
    Display index page.
    """
    template= kwargs.get('template', 'index')
    if template:
        template= '.'.join([template, 'html'])
    return render_to_response(template, {
        'page_title': 'Sezam main page'},
        context_instance=RequestContext(request))