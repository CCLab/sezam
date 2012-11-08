#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Classes for parsing dictionaries from XML.
"""

import csv
import xml.etree.ElementTree as ET
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

import pdb # Debug.


class Parser(object):
    """
    Basic class for parsing XML data and converting it to list of dicts.

    Assumes the structure, in which the last 3 layers should be <catalog>
    consisting of <row>s consisting of <col>s.

    Returns a dict in which the keys are created from the attrib 'name'
    (the rest are being ignored) and the values made of tags' values.
    """

    def __init__(self):
        pass


    @staticmethod
    def parse(source=None):
        """
        Main parsing function.
        """
        # Constants.
        KEY_ATTRIB= u'name'
        CATALOG_LABEL= u'catalog'

        def _walk_tree(elem, parent=None):
            """
            Recurse function to walk through the tags
            picking up the elements of the structure.
            """

            def _walk_siblings(row):
                """
                Gather data from the lowest layer, arrange them into dict {k: v},
                where ``k`` is attrib name of the tag, ``v`` is tag's value
                """
                out_dict= {}
                for col in list(row):
                    for k, v in col.attrib.iteritems():
                        if k.strip() != KEY_ATTRIB:
                            continue
                        key= unicode(v.strip().lower())
                        val= unicode(col.text.strip()) if col.text else ''
                        out_dict.update({key: val})
                        break # Only the name counts.
                return out_dict

            if elem.tag.strip() == CATALOG_LABEL:
                # Walk through 'catalog', pick up 'row's
                # and fill them with data from 'col'.
                for row in list(elem):
                    out.append(_walk_siblings(row))
            else:
                # Children of 'catalog' are 'rows'.
                for child in list(elem):
                    _walk_tree(child, elem)
        
        try:
            root= ET.parse(source).getroot()
        except Exception as e:
            return e
        out= []
        _walk_tree(root)
        return out


class Extractor(object):
    """
    Basic class for extract data from CSV files
    and converting it to list of dicts.
    """

    @staticmethod
    def extract(source=None, schema=None, delimiter=';', quotechar='"'):
        """
        Main extracting function.

        Parses csv file and returns data as list of dicts using schema.
        For each field, tries to cast it on the type that is described
        in schema. Because of a few ways to write float values, for float
        values tries to modify value so that it can be casted to float.

        Arguments:
        source -- a csv reader with data
        schema -- schema describing data in the file
        """
        print '-- parsing csv file'
        out= []

        _source= csv.reader(source, delimiter=delimiter, quotechar=quotechar)
        dbkey_alias= schema["alias"] # dict of aliases -> document keys in db
        dbval_types= schema["type"] # dict of types -> values types in db

        for row in _source:
            row= iter(row)        
            for row in _source:
                i= 0
                dict_row= {} # this holds the data of the current row
                
                for field in row:
                    new_key= dbkey_alias[i]
                    new_type= None
                    if new_key in dbval_types:
                        new_type= dbval_types[new_key]

                    if new_type == "string":
                        dict_row[new_key]= str(field).strip()
                    elif new_type == "int":
                        if field == '':
                            dict_row[new_key]= None
                        else:
                            dict_row[new_key]= int(field)
                    elif new_type == "float":
                        commas_in_field= field.count(',')
                        dots_in_field= field.count('.')
                        if commas_in_field > 0:
                            if dots_in_field > 0:
                                field= field.replace(',', '', commas_in_field)
                            else:
                                field= field.replace(',', '', commas_in_field - 1)
                                field= field.replace(',', '.')
                        if field == '': # fields in hierarchy rows may have empty fields
                            field= 0.0
                        dict_row[new_key]= float(field)
                    elif new_type == None:
                        try:
                            dict_row[new_key]= float(field) # then if it is a number
                            if dict_row[new_key].is_integer(): # it can be integer
                                dict_row[new_key]= int(field)
                        except:
                            dict_row[new_key]= str(field).strip() # no, it is a string

                    i += 1

                out.append(dict_row)

        return out


class RecordManager(object):
    """
    Basic operations with data (create, find, etc.).
    Assumes that all the typing is done in the caller.
    """
    MSG= {
        'ignore': u'--- item `%s` already exists in the db, ignoring...',
        }
    
    @classmethod
    def create_element(cls, item_type, verbose=False, **kwargs):
        """
        Insert new record to the db.
        """
        r= RecordManager
        # Check if the item with given name exist already.
        new_item= r.get_element(item_type, report=False, **kwargs)
        if new_item:
            if verbose: print r.MSG['ignore'] % kwargs['name']
            return new_item
        new_item= item_type() # No such item - create new one.
        for arg, val in kwargs.iteritems():
            setattr(new_item, arg, val)
        try:
            new_item.save()
        except Exception as e:
            print e
            new_item= None
        return new_item


    @classmethod
    def get_element(cls, item_type, report=True, **kwargs):
        """
        Try to find the item in the db by the parameters given in kwargs.
        """
        try:
            return item_type.objects.get(**kwargs)
        except MultipleObjectsReturned:
            return item_type.objects.filter(**kwargs)[0]
        except ObjectDoesNotExist as e:
            if report: print e, "(%s: %s)" % (item_type, kwargs)
        return None


    @classmethod
    def get_elements(cls, item_type, report=True, **kwargs):
        """
        Try to find records in the db by the parameters given in kwargs.
        Return empty list if there're no records.
        """
        try:
            return item_type.objects.filter(**kwargs)
        except ObjectDoesNotExist as e:
            if report: print e, "(%s: %s)" % (item_type, kwargs)
        return None


def remove_diacritics(stri):
    """
    Returns name without diacritics and inserted latin letters.
    """
    return stri.decode('utf-8')\
        .replace(u'ą', u'a').replace(u'ć', u'c').replace(u'ę', u'e').replace(u'ł', u'l')\
        .replace(u'ń', u'n').replace(u'ó', u'o').replace(u'ś', u's').replace(u'ź', u'z')\
        .replace(u'ż', u'z').replace(u'Ą', u'A').replace(u'Ć', u'C').replace(u'Ę', u'E')\
        .replace(u'Ł', u'L').replace(u'Ń', u'N').replace(u'Ó', u'O').replace(u'Ś', u'S')\
        .replace(u'Ź', u'Z').replace(u'Ż', u'Z')


def add_diacritics(stri):
    """
    Returns name with diacritics instead of matching letters.
    """
    return stri.decode('utf-8')\
        .replace(u'a', u'ą').replace(u'c', u'ć').replace(u'e', u'ę').replace(u'l', u'ł')\
        .replace(u'n', u'ń').replace(u'o', u'ó').replace(u's', u'ś').replace(u'z', u'ź')\
        .replace(u'z', u'ż').replace(u'A', u'Ą').replace(u'C', u'Ć').replace(u'E', u'Ę')\
        .replace(u'L', u'Ł').replace(u'N', u'Ń').replace(u'O', u'Ó').replace(u'S', u'Ś')\
        .replace(u'Z', u'Ź').replace(u'Z', u'Ż')
