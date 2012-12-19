#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Functions used in other modules.
"""
from django.core.paginator import Paginator, Page, EmptyPage, PageNotAnInteger
from django.template.defaultfilters import slugify
from django.contrib.sites.models import Site

from time import strptime, strftime
from PIL import Image

import random
import string
import re
import os

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
        'unresolved': ['in_progress', 'overdue', 'long_overdue', 'withdrawn']}

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
