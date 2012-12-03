from django.contrib.sites.models import Site

def get_domain_name(id=1):
    """Get the project's domain name by its ID.
        Default is the 1st project.
        """
    try:
        return Site.objects.get(id=id).domain
    except Site.DoesNotExist:
        # If doesn't exist, return the default one.
        return Site.objects.get(id=1).domain
