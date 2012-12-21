# Django settings for sezam project.
import os
import sys
from platform import platform

ROOT_PATH = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Denis Kolokol', 'dkolokol@gmail.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'sezam',
        'USER': 'sezamsu',
        'PASSWORD': 'yootooQuieng8CeR',
        'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '', # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Warsaw'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'pl-pl'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(ROOT_PATH, 'site_media/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/site_media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(ROOT_PATH, 'static/')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
# WARNING: Absolute path for the development period only!
if 'Darwin' in platform():  # local
    STATIC_URL = 'http://localhost:8000/static/'
elif 'Linux' in platform():  # server
    STATIC_URL = 'http://sezam.centrumcyfrowe.pl:3002/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'y9j25i5y09uu5)ts)x+h_3#6&amp;yo4&amp;mft49&amp;6mi%(2f7i4*v6a_'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'sezam.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'sezam.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates').replace('\\', '/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'apps.authority',
    'apps.pia_request',
    'apps.browser',
    'apps.backend',
    'apps.vocabulary',
    'apps.userprofile',
    # 3rd party modules
    'kombu.transport.django',
    'registration',
    'xpaginate',
    'djcelery',
    'mptt',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# Registration settings
ACCOUNT_ACTIVATION_DAYS = 7 # One-week activation window.

# SMTP settings
if 'Darwin' in platform():  # local
    EMAIL_HOST = 'smtp.poczta.onet.pl'
    EMAIL_PORT = 587
    EMAIL_HOST_USER = 'wniosek.dip@op.pl'
    EMAIL_HOST_PASSWORD = 'sans640tirepita'
    EMAIL_USE_TLS = False
    DEFAULT_FROM_EMAIL = 'wniosek.dip@op.pl'
elif 'Linux' in platform():  # server
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 25
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_TLS = False
    DEFAULT_FROM_EMAIL = 'info@sezam.pl'

# User management
LOGIN_URL= '/accounts/login/'

# MPTT settings
MPTT_ADMIN_LEVEL_INDENT = 20

# Pagination settings
PAGINATE_BY = 50

# Thumbnail size
THUMBNAIL_SIZE = (70, 70)

# Email - mailbox backend settings.
MAILBOXES = {
    'default': { # Test mailbox: go to http://poczta.onet.pl/ to check mail.
        'host': 'imap.poczta.onet.pl',
        'port': 993,
        'login': 'wniosek.dip@op.pl',
        'domain': 'op.pl',
        'password': 'sans640tirepita',
        'use_ssl': True,
    }
}
# Directory for saving attachments from incoming e-mails.
ATTACHMENT_DIR= os.path.join(MEDIA_ROOT, 'attachments/')

# Django-celery
import djcelery
djcelery.setup_loader()

# Use django database as a broker
BROKER_URL = 'django://'

# Days before unanswered request become overdue.
OVERDUE_DAYS = 16

# Is session expires when a user exits the browser.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
