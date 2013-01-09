"""
Sezam context processors.
Return dictionaries to be merged into a template context. Each function takes
the request object as its only parameter and returns a dictionary to add to the
context.

These are referenced from the setting TEMPLATE_CONTEXT_PROCESSORS and used by
RequestContext.
"""

from django.utils.translation import ugettext_lazy as _
from apps.backend.utils import get_domain_name
from django.contrib.sites.models import Site
from django.conf import settings

def get_current_path(request):
    return {'current_path': request.get_full_path()}

def get_resource_name(request):
    hostname= request.META.get('HTTP_HOST', None)
    try:
        return {'resource_name': Site.objects.get(domain=hostname).name}
    except:
        return {'resource_name': get_domain_name()}

def get_settings(request):
    """
    Selected settings variables into the default template context.
    """
    return {
        'ATTACHMENT_ACCEPTED_FILETYPES': '|'.join(settings.ATTACHMENT_ACCEPTED_FILETYPES),
        'ATTACHMENT_MAX_FILESIZE': settings.ATTACHMENT_MAX_FILESIZE,
        }
