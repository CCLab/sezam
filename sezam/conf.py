"""
Config file with passwords and other secure data.
Warning! Keep it ignored by the version control!
"""

DATABASES = {
    'default': {
        'ENGINE': '',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

STATIC_URL = ''

# SMTP settings
EMAIL_HOST = ''
EMAIL_PORT = None
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = ''

# Email - mailbox backend settings
MAILBOXES = {
    'default': { # Test mailbox: go to http://poczta.onet.pl/ to check mail.
        'host': '',
        'port': None,
        'login': '',
        'domain': '',
        'password': '',
        'use_ssl': False,
    }
}

# Haystack for elasticsearch
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': '',
        'URL': '',
        'INDEX_NAME': '',
    },
}
