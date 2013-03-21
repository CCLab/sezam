from django.dispatch import Signal

from django.contrib.auth import login, authenticate

# A new user has registered.
user_registered = Signal(providing_args=["user", "request"])

# A user has activated his or her account.
user_activated = Signal(providing_args=["user", "request"])

def login_on_activation(sender, user, request, **kwargs):
    """
    Logs in the user after activation.
    """
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
 
# Registers the function with the django-registration user_activated signal
user_activated.connect(login_on_activation)
