"""
Sezam context processors.
Return dictionaries to be merged into a template context. Each function takes
the request object as its only parameter and returns a dictionary to add to the
context.

These are referenced from the setting TEMPLATE_CONTEXT_PROCESSORS and used by
RequestContext.
"""

def get_current_path(request):
    return {'current_path': request.get_full_path()}
