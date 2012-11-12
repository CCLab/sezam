#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Uploading territory information from XML to the DB.

Assumes the structure, in which the last 3 layers should be
<catalog> consisting of <row>s consisting of <col>s.
"""

import os
import sys
import optparse
import utils # Custom module.


# Data constants.
CODE_ATTRIBS= [u'WOJ', u'POW', u'GMI'] # Order matters!
CODE_TEXT_IF_NONE= u'00'

# Script constants.
VERBOSE= False

class Uploader(object):
    """
    Main class for uploading references.
    """

    # Class constants.
    MSG= {
        'start': u'Uploading data from the dictionary of %s to db.',
        'finito': u'Uploading of %s to db complete.'
        }
    TERYT_ROOT_NAME= u'Administracja Lokalna'

    @staticmethod
    def upload_territorytype(ref, verbose=False):
        """
        Uploading the territory types
        to the vocabulary TerritoryType.
        """
        ref_name= 'Territory Types'
        u= Uploader
        r= utils.RecordManager

        if verbose: print u.MSG['start'] % ref_name            
        for tp in ref:
            if not r.create_element(
                    TerritoryType, verbose=verbose, name=tp):
                return False
        if verbose: print u.MSG['finito'] % ref_name
        return True


    @staticmethod
    def upload_territory(ref, verbose=False):
        """
        Uploading territories according to TERYT classification
        (parent-child depending on the code).
        """
        ref_name= 'Territories'
        u= Uploader
        r= utils.RecordManager

        # The root category for Territory.
        _root= r.create_element(AuthorityCategory, name=u.TERYT_ROOT_NAME)
        if not _root:
            return False

        if verbose: print u.MSG['start'] % ref_name
        for tr in ref:
            _type= r.get_element(TerritoryType, report=False, name=tr['nazdod'])
            _code, _name= (tr['code'], tr['nazwa'])
            code_list= _code.split('-')
            if code_list[-2:] == [CODE_TEXT_IF_NONE, CODE_TEXT_IF_NONE]:
                _parent= _root # 1st level, the parent is AuthorityCategory.
            else: # 2nd level, look for parent on the 1st.
                if code_list[-1:] == [CODE_TEXT_IF_NONE]:
                    lookup= '-'.join([code_list[0], CODE_TEXT_IF_NONE, CODE_TEXT_IF_NONE])
                else: # 3rd level, look for parent on 2nd.
                    lookup= '-'.join([code_list[0], code_list[1], CODE_TEXT_IF_NONE])
                _parent= r.get_element(Territory, report=False, code=lookup)
            if not r.create_element(Territory, verbose,
                    name=_name, code=_code, type=_type, parent=_parent):
                return False
        if verbose: print u.MSG['finito'] % ref_name
        return True


def convert_codes(lst):
    """
    Convert codes from the form
    {u'woj': u'XX', u'pow': u'YY', u'gmi': u'ZZ'}
    to {u'code': u'XX-YY-ZZ'}
    """
    for elem in lst:
        code= [CODE_TEXT_IF_NONE for i in CODE_ATTRIBS]
        for k, v in elem.iteritems():
            if k.strip().upper() in CODE_ATTRIBS:
                # Complete the item code with compliance with the order.
                if v.strip() != '':
                    code[CODE_ATTRIBS.index(k.strip().upper())]= v.strip()
        elem.update({'code': '-'.join(code)})
        for attr in CODE_ATTRIBS: del elem[attr.lower()]
    return lst


def extract_types(lst):
    """
    Extract types of territory into the list.
    """
    terr_types= set(k[u'nazdod'] for k in lst)
    return list(terr_types)


def process_tree(src):
    """
    Parse the source, create the tree.
    """
    if VERBOSE: print "Parsing the source XML file."
    try:
        territory= utils.Parser.parse(src)
        if VERBOSE: print "Parse complete successfully."
    except Exception as e:
        print e

    if VERBOSE: print "Converting codes in the obtained dataset."
    try:
        territory= convert_codes(territory)
        if VERBOSE: print "Code conversion complete successfully."
    except Exception as e:
        print e

    if VERBOSE: print "Creating dictionary of territory types."
    try:
        territorycode= extract_types(territory)
        if VERBOSE: print "The dictionary of territory types successfully created."
    except Exception as e:
        print e

    # Uploading section.
    if not Uploader.upload_territorytype(territorycode, VERBOSE):
        return False
    # if not Uploader.upload_territory(territory, VERBOSE):
    #     return False
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
    if process_tree(src_file):
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
    from apps.vocabulary.models import TerritoryType, Territory, AuthorityCategory

    # Process command line options, start the process, report on the results.
    cmdparser = optparse.OptionParser(
        usage="usage: python %prog [Options] src_filename.xml")
    cmdparser.add_option("-v", "--verbose", action="store_true", dest='verbose',
        help="verbose mode (comment and report every action)")
    opts, args= cmdparser.parse_args()
    # Set verbose mode globally.
    if opts.verbose: VERBOSE= True

    # Go!
    main(opts, args)
