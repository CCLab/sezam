#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Uploading Authorities records from CSV to the DB.
"""

import re
import os
import sys
import optparse
from django.template.defaultfilters import slugify

# Custom module.
from utils import Extractor as EX, RecordManager as RM

# Debug.
import pdb


# Mapping the Authority types from import files to the data in the db.
TYPE_MAP= {
    'PZ': [u"powiat", u"miasto na prawach powiatu", u"gmina miejska"],
    'MNP':[u"miasto na prawach powiatu"],
    'GM': [u"gmina miejska"],
    'GW': [u"gmina wiejska"],
    'GMW':[u"gmina miejsko-wiejska", u"gmina wiejska"],
    'UDW':[u"miasto stołeczne, na prawach powiatu"],
    'WJ': [u"województwo"]
    }

OTHERS_NAME= u"Inne"
TERRITORIES_NAME= u"Administracja lokalna"


def define_schema(vocabulary_type):
    """
    Define schema for different data type.
    """
    schema= {AuthorityProfile:
    {
        'alias': ('num', 'teryt_name', 'woj', 'pow', 'typ',
            'name', 'post_office', 'address_postalcode', 'address_city', 'address_street', 'address_num',
            'tel_code', 'tel_number', 'tel_internal', 'fax_code', 'fax_number',
            'official', 'official_name', 'official_lastname',
            'email_secretary', 'email', 'web_site', 'notes'),
        'type': {
            'num': 'string',
            'postal_code': 'string',
            'house_num': 'string',
            'tel_number': 'string',
            'tel_internal': 'string',
            'fax_regional_code': 'string',
            'notes': 'string'
            },
        }
    }
    return schema[vocabulary_type]


def upper_diacr(ln):
    """
    Correct upper func for words with diacritics.
    """
    return ln.upper().decode('utf-8')\
        .replace(u'ą', u'Ą').replace(u'ć', u'Ć').replace(u'ę', u'Ę')\
        .replace(u'ł', u'Ł').replace(u'ń', u'Ń').replace(u'ó', u'Ó')\
        .replace(u'ś', u'Ś').replace(u'ź', u'Ź').replace(u'ż', u'Ż')


def create_element(record, category):
    """
    Creating new Authority record.
    """
    for k in ('num', 'teryt_name', 'woj', 'pow', 'typ', 'post_office',
              'name_lookup'):
        del record[k] # Remove unnecessary keys.
    record['category']= category # Add category.
    new_record= RM.create_element(AuthorityProfile, verbose=True, **record)
    return new_record


def get_category(rec, cat_territory):
    """
    Find or create Category in Territories.
    cat_territory - global parent of all Territories in AuthorityCategory.
    """
    try:
        category_type= RM.get_element(TerritoryType, report=False,
                                       name__in=TYPE_MAP[rec['typ']])
    except Exception as e:
        print "Cannot even find Territory Type for the record %s - %s, here is what system says:\n%s" % (
            rec['num'], rec['address_city'], e)
        return None

    # Define Wojewodstwo.
    type1= RM.create_element(TerritoryType, verbose=False, name=TYPE_MAP['WJ'][0])
    territory1= RM.create_element(Territory, verbose=False, name=upper_diacr(rec['woj']), type=type1, parent=cat_territory)
    # Define Powiat.
    type2= RM.create_element(TerritoryType, verbose=False, name=TYPE_MAP['PZ'][0]) # Always powiat!
    territory2= RM.create_element(Territory, verbose=False, name=rec['pow'].strip(), type=type2, parent=territory1)
    return territory2


def get_category_old(rec):
    """
    Try to find Territory code (TERYT) by given parameters.
    """
    # Trying to find Territory Type.
    try:
        category_type= RM.get_element(TerritoryType, report=False,
                                       name__in=TYPE_MAP[rec['typ']])
    except Exception as e:
        print "Cannot even find Territory Type for the record %s - %s, here is what system says:\n%s" % (
            rec['num'], rec['address_city'], e)
        return None

    # Trying to find territory (category).
    # First try to find by name.
    # 1. WHERE name = ...
    category= RM.get_elements(Territory, report=False,
                               name=rec['address_city'], type=category_type)

    # If 'name =' doesn't work, try 'slug like' (more chances)
    # 2. WHERE slug LIKE '...%'
    if len(category) == 0:
        category= RM.get_elements(Territory, report=False,
            slug__startswith=rec['slug'], type=category_type)

    # If slug doesn't work, try name variations.
    # 3. WHERE name IN (...
    if len(category) == 0:
        category= RM.get_elements(Territory, report=False,
                    name__in=rec['name_lookup'], type=category_type)

    if len(category) == 0: # Now it's really nothing
        return None
    elif len(category) == 1:
        return category[0]
    elif len(category) > 1:
        # Search for category in the returned records.
        for tr in category:
            woj= rec['woj']
            pow= rec['pow']
            if tr.parent.name.encode('utf-8') in [woj, pow]:
                return tr.parent
        print "WARNING! More than one category found for %s - %s (placed under the category `%s`)!" % (
            rec['address_city'], rec['num'], OTHERS_NAME)
        for tr in category:
            print '%s%s' % (' ' * 4, tr)
        return None
    else:
        print "Wow, that's weird: the number of records returned by query is %s!" % len(category)
        return None


def ensure_category(cat_name, ord=100):
    """
    Look for the record (or create one, if None) "Others" in Categories.
    """
    cat= RM.get_element(AuthorityCategory, report=False, name=cat_name)
    if not cat:
        cat= RM.create_element(AuthorityCategory, False, name=cat_name,
                               order=ord)
    return cat


def process_extracted_data(dset):
    """
    Inserting extracted data into the AuthorityProfile vocabulary.
    """
    def _clean_record(rc):
        """
        Cleaning the record
        """

        # - Change 'a - b' to 'a-b'
        for k in rc.keys():
            if isinstance(rc[k], basestring):
                rc[k]= rc[k].replace(' - ', '-')

        # - Gather all possible variations of name.
        rc['name_lookup']= list([rc['address_city']])
        if ' ' in rc['address_city']:
            rc['name_lookup'].append(rc['address_city'].replace(' ', '-'))

        # - Add slug to increase probability of finding the record,
        #   even if name is written with mistakes
        rc['slug']= slugify(downcode(rc['address_city'].decode('utf-8')))

        # - Cleaning tel/fax codes and numbers.
        for code_num in ('tel_code', 'fax_code', 'tel_number', 'fax_number',
                         'address_postalcode'):
            rc[code_num]= re.sub('[^0-9]+', '', rc[code_num])

        # Re-naming elements according to their territory
        rc['name']= '%s, %s' % (rc['address_city'], rc['name'])

        return rc

    # category_other= ensure_category(OTHERS_NAME)
    category_territory= ensure_category(TERRITORIES_NAME)
    uncategorized= []

    for record in dset:
        # First check if record should be processed at all.
        if '.' in record['num']: # Removing silly dots after single int.
            record['num']= record['num'].replace('.', '')
        try: # If it can be converted to int, then it's an ordinary record.
            int(record['num'])
        except:
            continue

        category= get_category(_clean_record(record), category_territory)
        if not category:
            category= category_other
            uncategorized.append('%s - %s' % (
                record['address_city'].decode('utf-8'), record['num']))
        else:
            # print "%s - %s" % (record['num'], category)
            pass

        # INSERT new record!!!
        create_element(record, category)

    # Report "orphans".
    if uncategorized:
        print "%s %s %s:" % (
            "WARNING! No territory found for the following Authorities,",
            "they are placed under the category", category_other.name)
        for other in uncategorized:
            print other


def process_source(src):
    """
    Parse the source according to the given schema,
    create the list of dicts with records of Authorities.
    """
    schema= define_schema(AuthorityProfile)

    if VERBOSE: print "Extracting the data from the source CSV file."
    try:
        authorities= EX.extract(src, schema)
        if VERBOSE: print "Extracting complete successfully."
    except Exception as e:
        print e
        return False

    if VERBOSE: print "Processing data from the obtained dataset."
    try:
        authorities= process_extracted_data(authorities)
    except Exception as e:
        print e
        return False

    if VERBOSE: print "Processing complete."
    return True


def main(opts, args):
    """
    Process command line options, start the process, report on the results.
    """
    if len(args) == 0:
        print 'No parameters specified! Type python %prog -h for help'
        exit()

    # Process source.
    try:
        src_file= open(args[0], 'rb')
    except IOError as e:
        print 'Unable to open file: \n%s\n' % e
        exit()

    # Report results.
    if process_source(src_file):
        print "Finished successfully."
    else:
        print "Finished with errors!"

def switch_to_environment(src_file, settings_module):
    """
    Set the Project's Django environment.
    """
    message= "\n%s\n%s" % (
        "Most probably the script is in the wrong directory.",
        "The script should live in the `scripts` subdirectory of the main project directory!")
    try: # Update $PATH
        sys.path.append(
            os.path.abspath(
                os.path.join(os.path.dirname(src_file), os.path.pardir)))
    except Exception as e:
        print e
        return message
    try: # Switch to the given environment.
        os.environ['DJANGO_SETTINGS_MODULE']= settings_module
    except Exception as e:
        print e
        return message
    return None


if __name__ == "__main__":
    # Set the environment.
    env_response= switch_to_environment(__file__, 'sezam.settings')
    if env_response:
        print env_response
        exit()
    # Models can be imported only if and after the environment is set!
    from apps.vocabulary.models import TerritoryType, Territory, AuthorityCategory, AuthorityProfile
    from apps.backend.utils import downcode

    # Process command line options, start the process, report on the results.
    cmdparser = optparse.OptionParser(
        usage="usage: python %prog [Options] src_filename.csv")
    cmdparser.add_option("-v", "--verbose", action="store_true", dest='verbose',
        help="verbose mode (comment and report every action)")
    opts, args= cmdparser.parse_args()
    # Set verbose mode globally.
    if opts.verbose: VERBOSE= True

    # Go!
    main(opts, args)
