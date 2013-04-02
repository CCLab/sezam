#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Functions used in other modules.
"""
from django.core.paginator import Paginator, Page, EmptyPage, PageNotAnInteger
from django.core.mail.message import EmailMessage
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.template.loader import render_to_string, get_template
from django.template.defaultfilters import filesizeformat
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import views as auth_views
from django.contrib.sites.models import Site
from django.utils.encoding import force_unicode
from django.utils.timezone import utc
from django.conf import settings

from apps.backend import AppMessage
from apps.backend.html2text import html2text

from datetime import datetime
from time import strptime, strftime
from PIL import Image

import xhtml2pdf
import xhtml2pdf.pisa as pisa
import cStringIO as StringIO
import random, string, re, os, sys

"""
Creating a unique slug depending on the model.
slugify_unique
"""

LATIN_MAP = {
    u'À': 'A', u'Á': 'A', u'Â': 'A', u'Ã': 'A', u'Ä': 'A', u'Å': 'A', u'Æ': 'AE', u'Ç':'C', 
    u'È': 'E', u'É': 'E', u'Ê': 'E', u'Ë': 'E', u'Ì': 'I', u'Í': 'I', u'Î': 'I',
    u'Ï': 'I', u'Ð': 'D', u'Ñ': 'N', u'Ò': 'O', u'Ó': 'O', u'Ô': 'O', u'Õ': 'O', u'Ö':'O', 
    u'Ő': 'O', u'Ø': 'O', u'Ù': 'U', u'Ú': 'U', u'Û': 'U', u'Ü': 'U', u'Ű': 'U',
    u'Ý': 'Y', u'Þ': 'TH', u'ß': 'ss', u'à':'a', u'á':'a', u'â': 'a', u'ã': 'a', u'ä':'a', 
    u'å': 'a', u'æ': 'ae', u'ç': 'c', u'è': 'e', u'é': 'e', u'ê': 'e', u'ë': 'e',
    u'ì': 'i', u'í': 'i', u'î': 'i', u'ï': 'i', u'ð': 'd', u'ñ': 'n', u'ò': 'o', u'ó':'o', 
    u'ô': 'o', u'õ': 'o', u'ö': 'o', u'ő': 'o', u'ø': 'o', u'ù': 'u', u'ú': 'u',
    u'û': 'u', u'ü': 'u', u'ű': 'u', u'ý': 'y', u'þ': 'th', u'ÿ': 'y'
}
LATIN_SYMBOLS_MAP = {
    u'©':'(c)'
}
GREEK_MAP = {
    u'α':'a', u'β':'b', u'γ':'g', u'δ':'d', u'ε':'e', u'ζ':'z', u'η':'h', u'θ':'8',
    u'ι':'i', u'κ':'k', u'λ':'l', u'μ':'m', u'ν':'n', u'ξ':'3', u'ο':'o', u'π':'p',
    u'ρ':'r', u'σ':'s', u'τ':'t', u'υ':'y', u'φ':'f', u'χ':'x', u'ψ':'ps', u'ω':'w',
    u'ά':'a', u'έ':'e', u'ί':'i', u'ό':'o', u'ύ':'y', u'ή':'h', u'ώ':'w', u'ς':'s',
    u'ϊ':'i', u'ΰ':'y', u'ϋ':'y', u'ΐ':'i',
    u'Α':'A', u'Β':'B', u'Γ':'G', u'Δ':'D', u'Ε':'E', u'Ζ':'Z', u'Η':'H', u'Θ':'8',
    u'Ι':'I', u'Κ':'K', u'Λ':'L', u'Μ':'M', u'Ν':'N', u'Ξ':'3', u'Ο':'O', u'Π':'P',
    u'Ρ':'R', u'Σ':'S', u'Τ':'T', u'Υ':'Y', u'Φ':'F', u'Χ':'X', u'Ψ':'PS', u'Ω':'W',
    u'Ά':'A', u'Έ':'E', u'Ί':'I', u'Ό':'O', u'Ύ':'Y', u'Ή':'H', u'Ώ':'W', u'Ϊ':'I',
    u'Ϋ':'Y'
}
TURKISH_MAP = {
    u'ş':'s', u'Ş':'S', u'ı':'i', u'İ':'I', u'ç':'c', u'Ç':'C', u'ü':'u', u'Ü':'U',
    u'ö':'o', u'Ö':'O', u'ğ':'g', u'Ğ':'G'
}
RUSSIAN_MAP = {
    u'а':'a', u'б':'b', u'в':'v', u'г':'g', u'д':'d', u'е':'e', u'ё':'yo', u'ж':'zh',
    u'з':'z', u'и':'i', u'й':'j', u'к':'k', u'л':'l', u'м':'m', u'н':'n', u'о':'o',
    u'п':'p', u'р':'r', u'с':'s', u'т':'t', u'у':'u', u'ф':'f', u'х':'h', u'ц':'c',
    u'ч':'ch', u'ш':'sh', u'щ':'sh', u'ъ':'', u'ы':'y', u'ь':'', u'э':'e', u'ю':'yu',
    u'я':'ya',
    u'А':'A', u'Б':'B', u'В':'V', u'Г':'G', u'Д':'D', u'Е':'E', u'Ё':'Yo', u'Ж':'Zh',
    u'З':'Z', u'И':'I', u'Й':'J', u'К':'K', u'Л':'L', u'М':'M', u'Н':'N', u'О':'O',
    u'П':'P', u'Р':'R', u'С':'S', u'Т':'T', u'У':'U', u'Ф':'F', u'Х':'H', u'Ц':'C',
    u'Ч':'Ch', u'Ш':'Sh', u'Щ':'Sh', u'Ъ':'', u'Ы':'Y', u'Ь':'', u'Э':'E', u'Ю':'Yu',
    u'Я':'Ya'
}
UKRAINIAN_MAP = {
    u'Є':'Ye', u'І':'I', u'Ї':'Yi', u'Ґ':'G', u'є':'ye', u'і':'i', u'ї':'yi', u'ґ':'g'
}
CZECH_MAP = {
    u'č':'c', u'ď':'d', u'ě':'e', u'ň':'n', u'ř':'r', u'š':'s', u'ť':'t', u'ů':'u',
    u'ž':'z', u'Č':'C', u'Ď':'D', u'Ě':'E', u'Ň':'N', u'Ř':'R', u'Š':'S', u'Ť':'T',
    u'Ů':'U', u'Ž':'Z'
}

POLISH_MAP = {
    u'ą':'a', u'ć':'c', u'ę':'e', u'ł':'l', u'ń':'n', u'ó':'o', u'ś':'s', u'ź':'z',
    u'ż':'z', u'Ą':'A', u'Ć':'C', u'Ę':'e', u'Ł':'L', u'Ń':'N', u'Ó':'o', u'Ś':'S',
    u'Ź':'Z', u'Ż':'Z'
}

LATVIAN_MAP = {
    u'ā':'a', u'č':'c', u'ē':'e', u'ģ':'g', u'ī':'i', u'ķ':'k', u'ļ':'l', u'ņ':'n',
    u'š':'s', u'ū':'u', u'ž':'z', u'Ā':'A', u'Č':'C', u'Ē':'E', u'Ģ':'G', u'Ī':'i',
    u'Ķ':'k', u'Ļ':'L', u'Ņ':'N', u'Š':'S', u'Ū':'u', u'Ž':'Z'
}

def _makeRegex():
    ALL_DOWNCODE_MAPS = {}
    ALL_DOWNCODE_MAPS.update(LATIN_MAP)
    ALL_DOWNCODE_MAPS.update(LATIN_SYMBOLS_MAP)
    ALL_DOWNCODE_MAPS.update(GREEK_MAP)
    ALL_DOWNCODE_MAPS.update(TURKISH_MAP)
    ALL_DOWNCODE_MAPS.update(RUSSIAN_MAP)
    ALL_DOWNCODE_MAPS.update(UKRAINIAN_MAP)
    ALL_DOWNCODE_MAPS.update(CZECH_MAP)
    ALL_DOWNCODE_MAPS.update(POLISH_MAP)
    ALL_DOWNCODE_MAPS.update(LATVIAN_MAP)
    
    s = u"".join(ALL_DOWNCODE_MAPS.keys())
    regex = re.compile(u"[%s]|[^%s]+" % (s,s))
    
    return ALL_DOWNCODE_MAPS, regex

_MAPINGS = None
_regex = None
def downcode(s):
    """
    This function is 'downcode' the string pass in the parameter s. This is useful 
    in cases we want the closest representation, of a multilingual string, in simple
    latin chars. The most probable use is before calling slugify.
    """
    global _MAPINGS, _regex

    if not _regex:
        _MAPINGS, _regex = _makeRegex()    

    downcoded = ""
    for piece in _regex.findall(s):
        if _MAPINGS.has_key(piece):
            downcoded += _MAPINGS[piece]
        else:
            downcoded += piece
    return downcoded


def slugify_unique(value, model, slugfield="slug"):
    suffix = 0
    potential = base = slugify(downcode(value))
    while True:
        if suffix:
            potential = "-".join([base, str(suffix)])
        if not model.objects.filter(**{slugfield: potential}).count():
            return potential
        suffix += 1

"""
slugify_unique - end
"""


def clean_text_for_search(text):
    """
    Prepare text for indexing and search.
    """
    # Get the normalized unicode text.
    text= force_unicode(text).strip()

    # Remove e-mail quotation from the beginnings of the string.
    text= re.sub(r'^\>+', '', text)

    # Remove e-mail addresses.
    text= re.sub(r'\b[A-Za-z0-9_\.-]+@[A-Za-z0-9_\.-]+[A-Za-z0-9_][A-Za-z0-9_]\b', '', text)

    # Try to convert html to text.
    try:
        text= html2text(text)
    except:
        pass

    # Clean the text from special characters, such as
    # section divisions ***, etc. but preserve punctuation.
    text= re.sub(r'\B\W{2,}\B', ' ', text)

    # Remove all returns and new lines.
    text= re.sub(r'\n+', ' ', text)
    text= re.sub(r'\r+', ' ', text)

    # Convert multiple spaces to singles.
    text= re.sub(r'\s{2,}', ' ', text)

    return text


def get_domain_name(id=1):
    """
    Get the project's domain name by its ID.
    Default is the 1st project.
    """
    try:
        return Site.objects.get(id=id).domain
    except Site.DoesNotExist: # Return the default one.
        return Site.objects.get(id=1).domain


def increment_id(model, field):
    """
    Get the maximum of `field`, return its value increment to 1.
    """
    try:
        return model.objects.values(field).distinct()\
                   .order_by('-'+field)[0][field] + 1
    except IndexError: # No records yet
        return 1
    except TypeError: # Non-integer/float field cannot be incremented.
        return None


def re_subject(line):
    """
    Constructing a subject in a manner 'Re[N]: subject line' or 
    'Re(N): subject line', based on the given line.

    If there's already such a pattern, increment N, otherwise simply add
    'Re: ' to the beginning.
    """
    caseRe= re.match(r'(?P<num>Re\:)', line)
    caseReN= re.match(r'Re(\[|\()(?P<num>\d+)(\]|\))', line)
    try:
        return line.replace(caseReN.group('num'),
                            str(int(caseReN.group('num'))+1))
    except:
        try:
            return line.replace(caseRe.group('num'), 'Re[1]:')
        except:
            pass
    return 'Re: ' + line


def process_filter_request(request, statuses):
    """
    Process GET with parameters:
    - extract params for initial dict
    - prepare kwargs for db query
    - define urlparams string.
    """
    # "Constants".
    filtered_status= {'all': [k[0] for k in statuses],
        'successful': ['successful', 'part_successful'],
        'unsuccessful': ['refused', 'no_info'],
        'unresolved': ['in_progress', 'overdue', 'long_overdue', 'withdrawn', 'awaiting']}

    # Define kwargs for filtering.
    query, initial= dict(), dict()
    
    # Define keywords.
    initial.update({'keywords': request.GET.get('keywords', '')})
    if initial['keywords'] != '':
        query.update({'summary__iregex': initial['keywords'].replace(' ', '|')})
    
    # Define status. Warning: status is in the param name, not value!
    status= 'all'
    for param in dict(request.GET).keys():
        if param in filtered_status.keys():
            status= param
            break
    query.update({'status__in': filtered_status[status]})

    # URL params
    urlparams= {'status': status, 'params': \
        '?'+'&'.join(['='.join([k, v[0]]) for k, v in dict(request.GET).iteritems()])}
    
    # Define `date_after` and `date_before`.
    initial['date_after']= request.GET.get('date_after', '')
    initial['date_before']= request.GET.get('date_before', '')
    if initial['date_after'] != '':
        query.update({'created__gte': strftime('%Y-%m-%d',
            strptime(initial['date_after'], '%d-%m-%Y'))})
    if initial['date_before'] != '':
        query.update({'created__lte': strftime('%Y-%m-%d 23:59:59',
            strptime(initial['date_before'], '%d-%m-%Y'))})
    return initial, query, urlparams


def id_generator(size=6, chars=string.ascii_lowercase+string.digits):
    """
    Generate unique filename to store in FS.
    """
    return ''.join(random.choice(chars) for x in range(size))


def handle_image(f, store_path, **kwargs):
    """
    Upload file, create a thumbnail from it, name it randomly,
    save to site_media, return it's name.
    """
    filename_len= kwargs.get('filename_len', 16)
    thumbnail_size= kwargs.get('thumbnail_size', (70, 70))
    ext= f.name.split('.')[-1]
    ext= '.'+ext if ext != f.name else '' # no extension
    filename= id_generator(filename_len)
    path= store_path + filename + ext
    with open(path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    im= Image.open(path) # Create thumbnail
    if im.mode != "RGB":
        im = im.convert("RGB")
    im.thumbnail(thumbnail_size, Image.ANTIALIAS)
    im.save(path, "JPEG")
    return filename + ext


def save_attached_file(f, store_root, **kwargs):
    """
    Check if attachments are ok, save files,
    return what is needed to save attachment in the db.
    """
    max_size= kwargs.get('max_size', 104857600) # Default limit is 100MB
    dir_name= kwargs.get('dir_name', id_generator()) # Random name, if not given
    dir_id= kwargs.get('dir_id', None)
    if dir_id is None: # Now, if not given
        dir_id= datetime.strftime(datetime.utcnow().replace(
            tzinfo=utc), '%d-%m-%Y_%H-%M')

    f_info= {'size': len(f), 'path': None, 'errors': []} # Object to return
    if f_info['size'] > max_size:
        f_info['errors'].append(AppMessage('AttachTooBig').message %
                                {'filename': f.name,
                                 'maxsize': filesizeformat(max_size)})

    # TO-DO: 'Sniff' the file before saving

    if len(f_info['errors']) == 0:

        # Ensure all directory names.
        dir_full= ('%s/attachments/%s/%s' % (
            store_root, dir_name, dir_id)).replace('//', '/')
        path_report= ('%s/%s/%s' % (
            dir_name, dir_id, f.name)).replace('//', '/')
        path_full= ('%s/%s' % (dir_full, f.name)).replace('//', '/')

        # Ensure directory on disk.
        if not os.path.exists(dir_full):
            os.makedirs(dir_full)

        try:
            path= default_storage.save(path_full, ContentFile(f.read()))
            f_info['path']= path_report # Returns relative (to MEDIA_ROOT) path.
        except Exception as e:
            err= AppMessage('CantSaveAttachmnt').message % {
                'filename': filename, 'error': e}
            print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), err)
            f_info['errors'].append(err)
    return f_info


def email_from_name(name, **kwargs):
    """
    Build e-mail address from given name.
    """
    id= kwargs.get('id', None)
    delimiter=kwargs.get('delimiter', None)
    domain= kwargs.get('domain', get_domain_name())
    name= slugify(downcode(name))
    if id:
        template= '%s-%s@%s' % (name, id, domain)
    else:
        template= '%s@%s' % (name, domain)
    if delimiter:
        template= template.replace('-', delimiter)
    return template


def login(request, **kwargs):
    """
    Custom view - handling the login form with "Remember me" checkbox.
    """
    template_name= kwargs.get('template_name', 'registration/login.html')
    response= auth_views.login(request, template_name)
    if request.POST.has_key('remember_me'):
        request.session.set_expiry(settings.SESSION_EXPIRE_AFTER)
    return response


def update_user_message(msg, notification, kind):
    """
    Updates session messages. The structure of the dict is:
    {
        'success': [<notifications>],
        'warning': [<notifications>],
        'warning_yesno': [<notifications>],
        'fail': [<errors>]
    }
    Anything else is considered as 'info'.
    """
    kinds= ('success', 'warning', 'warning_yesno', 'fail',)
    if kind not in kinds:
        kind= 'info'
    notifications= msg.pop(kind, [])
    if notifications is None:
        notifications= []
    if isinstance(notification, basestring):
        try:
            notifications.append(notification)
        except:
            pass
    elif isinstance(notification, list):
        try:
            notifications.extend(notification)
        except:
            pass
    else: # Ignore anything else.
        pass
    msg.update({kind: notifications})
    return msg

def send_mail_managers(subject, message, fail_silently=False,
                       connection=None, headers=None):
    """
    Sends a message to the managers, as defined by the MANAGERS setting.
    """
    if not settings.MANAGERS:
        return
    mail= EmailMessage(subject, message, settings.SERVER_EMAIL,
                       [a[1] for a in settings.MANAGERS], headers=headers)
    mail.send(fail_silently=fail_silently)

def send_notification(notification):
    """
    Sending user a notification about the event
    as described in EventNotification.

    Returns True if message successfully sent.
    """
    template= 'emails/notification_%s.txt' % notification.action
    subj_name= None
    for attr in ['name', 'summary', 'subject']:
        try:
            subj_name= getattr(notification.item.content_object, attr)
        except:
            pass
        else:
            break
    message_subject= '%s: %s' % (notification.get_action_display(), subj_name)
    message_subject= force_unicode(message_subject)
    message_content= render_to_string(template, {'notification': notification,
                                                 'domain': get_domain_name()})
    message_notification= EmailMessage(message_subject, message_content,
        settings.SERVER_EMAIL, [notification.receiver_email])
    try: # sending the message to the receiver, check if it doesn't fail.
        message_notification.send(fail_silently=False)
    except Exception as e:
        print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(),
            AppMessage('MailSendFailed').message % e)
        return False
    return True

def render_to_pdf(template_src, context_dict, **kwargs):
    """
    Renders html template to PDF.
    Returns a response of MIME type 'application/pdf'
    """
    context_instanse= kwargs.get('context', None)
    context_dict.update({'download': True})
    result= StringIO.StringIO()
    try:
        html= render_to_string(template_src, context_dict, context_instanse)
        pdf= pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")), result,
                               encoding="utf8")
    except xhtml2pdf.w3c.cssParser.CSSParseError:
        html= render_to_string(template_src, context_dict, None)
        pdf= pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")), result,
                               encoding="utf8")
    return pdf, result
