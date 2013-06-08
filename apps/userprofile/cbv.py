"""
Userprofile Class Based Views
"""

from registration.views import RegistrationView

from apps.userprofile.forms import RegistrationFormUniqueEmail

class RegistrationTosView(RegistrationView):
    """
    Registration view wirh TOS field
    """
    form_class = RegistrationFormUniqueEmail


