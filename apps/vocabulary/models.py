"""
Models for project-wide vocabularies.
"""

from django.db import models
from django.db.models import Q
from mptt.models import MPTTModel, TreeForeignKey


class Vocabulary(models.Model):
    """
    Abstract model for all vocabularies.
    """
    name= models.CharField(max_length=1000, help_text=_(u'Name'))
    order= models.IntegerField(default=100, help_text=_(u'Order'))

    def __unicode__(self):
        return self.name

class TreeVocabulary(Vocabulary):
    """
    Abstract class for tree-like vocabularies
    """
    parent= TreeForeignKey('self', null=True, blank=True,
        related_name='children', limit_choices_to=Q(parent__isnull=True))

    class MPTTMeta:
        order_insertion_by = ('name',)

    def __unicode__(self):
        return "%s (of %s)" % (self.name, self.parent)


class Province(Vocabularies):
    """
    Vocabulary of the Provinces (Wojewodstwo).
    """


class City(Vocabularies):
    """
    Vocabulary of the Cities (Gmina).

    There is no vocabulary for Countries, as the platform is country specific.
    It is possible to adopt it for similar tasks in other countries than Poland,
    but it makes no sense to use it in several counries at once.

    For a consolidated information, use API.
    """
    # TO-DO: realize API
    province= models.ForeignKey(vocabularies.Province,
        help_text=_(u'Province'))


class AuthorityClassification(TreeVocabulary):
    """
    A classification Tree for authorities.

    Only the leaf objects of this class can be
    used as foreign keys for Authority.
    """


class AuthorityProfile(Vocabulary):
    """
    Authority reference.
    """

    address_street= models.CharField(max_length=200,
        help_text=_(u'Street'))
    address_num= models.CharField(max_length=200,
        help_text=_(u'Building and office number'))
    address_line1= models.CharField(max_length=200, null=True, blank=True,
        help_text=_(u'Address (additional line 1)'))
    address_line2= models.CharField(max_length=200, null=True, blank=True,
        help_text=_(u'Address (additional line 2)'))
    address_postalcode= models.ForeignKey(vocabularies.Country,
        help_text=_(u'Postal code'))
    address_city= models.ForeignKey(vocabularies.City,
        help_text=_(u'City'))
    tel_code= models.IntegerField(help_text=_(u'Telephone code'))
    tel_main= models.CharField(max_length=7, help_text=_(u'Telephone')) # TO-DO: control format
    tel_main_internal= models.IntegerField(null=True, blank=True,
        help_text=_(u'Internal code'))
    tel_1= models.CharField(max_length=9, null=True, blank=True,
        help_text=_(u'Telephone 1'))
    tel_1_code= models.CharField(max_length=5, null=True, blank=True,
        help_text=_(u'Telephone 1 code'))
    tel_2= models.CharField(max_length=9, null=True, blank=True,
        help_text=_(u'Telephone 2'))
    tel_2_code= models.CharField(max_length=5, null=True, blank=True,
        help_text=_(u'Telephone 2 code'))
    fax= models.CharField(max_length=7, help_text=_(u'Telephone'))
    fax_code= models.IntegerField(max_length=2, null=True, blank=True,
        help_text=_(u'Telephone 1 code'))
