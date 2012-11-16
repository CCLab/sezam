"""
Models for project-wide vocabularies.
"""

import re
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey
from apps.backend.utils import slugify_unique


class Vocabulary(models.Model):
    """
    Abstract model for all vocabularies.
    """
    name= models.CharField(max_length=1000, verbose_name=_(u'Name'))
    order= models.IntegerField(default=100, verbose_name=_(u'Order'))

    class Meta:
        abstract= True
        ordering= ('order',)

    def __unicode__(self):
        return self.name


class SlugVocabulary(models.Model):
    """
    Abstract model for all vocabularies with slug.
    """
    slug= models.SlugField(max_length=100, unique=True, verbose_name=_(u'Slug'))

    class Meta:
        abstract= True

    def __unicode__(self):
        return self.slug

    def save(self, *args, **kwargs):
	"""
        Override save: slugify uniquely.
	"""
        self.slug= slugify_unique(self.name, self.__class__)
        super(SlugVocabulary, self).save(*args, **kwargs)


class TreeVocabulary(MPTTModel):
    """
    Abstract class for tree-like vocabularies
    """
    name= models.CharField(max_length=1000, verbose_name=_(u'Name'))
    parent= TreeForeignKey('self', null=True, blank=True,
        related_name='children')
    order= models.IntegerField(default=100, null=True, verbose_name=_(u'Order'))

    class MPTTMeta:
        order_insertion_by= ('name',)

    class Meta:
        abstract= True

    def __unicode__(self):
        return self.name


class AuthorityCategory(TreeVocabulary, SlugVocabulary):
    """
    A classification Tree for authorities.

    Only the leaf objects of this class can be
    used as foreign keys for Authority.
    """


class TerritoryType(Vocabulary):
    """
    Type of the territory.
    For Poland: wojewodztwo, gmina, miasto, etc.
    """
    display_name= models.CharField(max_length=50, blank=True, null=True,
                                   verbose_name=_(u'Name tp display'))


class Territory(AuthorityCategory):
    """
    Classified vocabulary of the territories.
    the Cities (Gmina), Provinces (Wojewodstwo), District (Powiat).

    There is no vocabulary for Countries, as the platform is country specific.
    It is possible to adapt it for similar tasks in other countries than Poland,
    but it makes no sense to use it in several counries simulteneously.
    """
    code= models.CharField(max_length=50, blank=True, null=True,
                           verbose_name=_(u'Territory Code'))
    type= models.ForeignKey(TerritoryType,
                            verbose_name=_(u'Territory Type'))

    class MPTTMeta:
        order_insertion_by= ('parent',)

    class Meta:
        ordering= ('parent',)


class AuthorityProfile(TreeVocabulary, SlugVocabulary):
    """
    Authority reference.

    Inherits from TreeVocabulary to support Authority -> Department relation.
    """
    description= models.TextField(null=True, blank=True,
        verbose_name=_(u'Description'))
    notes= models.CharField(max_length=1000, null=True, blank=True,
        verbose_name=_(u'Notes'))
    category= models.ForeignKey(AuthorityCategory,
                                verbose_name=_(u'Authority category'))

    # ADDRESS DETAILS
    address_street= models.CharField(max_length=200, verbose_name=_(u'Street'))
    # TO-DO: foreign key to the Vocabulary of the streets
    address_num= models.CharField(max_length=200, verbose_name=_(u'Office'),
                                  help_text=_(u'Building and office number'))
    address_line1= models.CharField(max_length=200, null=True, blank=True,
        verbose_name=_(u'Address (additional line 1)'))
    address_line2= models.CharField(max_length=200, null=True, blank=True,
        verbose_name=_(u'Address (additional line 2)'))
    address_postalcode= models.CharField(max_length=6,
        verbose_name=_(u'Postal code'), help_text=_(u'Digits only!'))
    address_city= models.CharField(max_length=100, verbose_name=_(u'City'))

    # TELEPHONES
    tel_code= models.CharField(max_length=3, verbose_name=_(u'tel code'),
                               help_text=_(u'Example: 45'))
    tel_number= models.CharField(max_length=20, verbose_name=_(u'Telephone'), # TO-DO: control format. Make char(9)!!!
                                 help_text=_(u'Digits only! Example: 504566462'))
    tel_internal= models.CharField(max_length=50, null=True, blank=True, 
        verbose_name=_(u'Internal'))
    tel1_code= models.CharField(max_length=3, null=True, blank=True,
        verbose_name=_(u'Tel 1 code'))
    tel1_number= models.CharField(max_length=20, null=True, blank=True,
        verbose_name=_(u'Telephone 1'))
    tel2_code= models.CharField(max_length=3, null=True, blank=True,
        verbose_name=_(u'Tel 2 code'))
    tel2_number= models.CharField(max_length=20, null=True, blank=True,
        verbose_name=_(u'Telephone 2'))
    fax_code= models.CharField(max_length=3, null=True, blank=True,
                               verbose_name=_(u'Fax code'))
    fax_number= models.CharField(max_length=20, verbose_name=_(u'Fax'))

    # E-MAILS
    email= models.EmailField(max_length=254, verbose_name=_(u'E-mail'))
    email_secretary= models.EmailField(max_length=254, blank=True,
        verbose_name=_(u'secretary e-mail'))
    email_info= models.EmailField(max_length=254, blank=True,
        verbose_name=_(u'info e-mail'))

    # WWW
    web_site= models.URLField(null=True, blank=True, verbose_name=_(u'Web-site'))
    web_site1= models.URLField(null=True, blank=True,
        verbose_name=_(u'Web-site 1'),
        help_text=_(u'Public Information Bulletin'))

    # Responsible person.
    official= models.CharField(max_length=200,
        help_text=_(u'Title of official position'),
        verbose_name=_(u'Official'))
    official_name= models.CharField(max_length=200,
        help_text=_(u'Official representative name'), verbose_name=_(u'Name'))
    official_lastname= models.CharField(max_length=200,
        help_text=_(u'Official representative last name'),
        verbose_name=_(u'Last name'))


    def save(self, *args, **kwargs):
	"""
        Override save:
        - get rid of non-digits in postalcode, telephone numbers and codes.
	"""
        self.address_postalcode= re.sub('[^0-9]+', '', self.address_postalcode)
        self.tel_code= re.sub('[^0-9]+', '', self.tel_code)
        self.tel_number= re.sub('[^0-9]+', '', self.tel_number)
        self.tel1_code= re.sub('[^0-9]+', '', self.tel1_code)
        self.tel1_number= re.sub('[^0-9]+', '', self.tel1_number)
        self.tel2_code= re.sub('[^0-9]+', '', self.tel2_code)
        self.tel2_number= re.sub('[^0-9]+', '', self.tel2_number)
        self.fax_code= re.sub('[^0-9]+', '', self.fax_code)
        self.fax_number= re.sub('[^0-9]+', '', self.fax_number)
        super(AuthorityProfile, self).save(*args, **kwargs)


# class AuthorityStat(models.Model):
#     """
#     Authority statistics.

#     Data in this model cannot be updated manually.
#     """
#     authority= models.ForeignKey(AuthorityProfile,
#         verbose_name=_(u'Authority Profile'))
#     requests_num= models.IntegerField(default=0,
#         verbose_name=_(u'Number of requests to the Authority'))
#     positive= models.IntegerField(default=0,
#         verbose_name=_(u'Number of requests to the Authority properly answered'))
#     positive_but= models.IntegerField(default=0,
#         verbose_name=_(u'Number of requests to the Authority answered, but...'))
#     negative= models.IntegerField(default=0,
#         verbose_name=_(u'Number of requests to the Authority not answered'))

#     def __unicode__(self):
#         return "%s: requests %d ('yes' %d, 'yes, but' %d, 'no' %d)"\
#             % (self.authority.name, self.requests_num, self.positive,
#                self.positive_but, self.negative)


# class UserProfile(User):
#     """
#     User Profile.
#     """
#     # TO-DO: e-mail as username


# class UserStat(models.Model):
#     """
#     Statistics for User.

#     Data in this model cannot be updated manually.
#     """
#     user= models.ForeignKey(User, verbose_name=_(u'User'))
#     # TO-DO: Foreign key - to User or to UserProfile?
#     requests_num= models.IntegerField(default=0,
#         verbose_name=_(u'Number of requests to the Authority'))
    
#     def __unicode__(self):
#         return "%s (requests %d)" % (
#             self.user.get_full_name(), self.requests_num)


# class UserRequest(models.Model):
#     """
#     Request in a Thread.
#     """
#     authority= models.ForeignKey(AuthorityProfile,
#                                  verbose_name=_(u'Authority Profile'))
#     user= models.ForeignKey(User, verbose_name=_(u'User'))
#     subject= models.CharField(max_length=255, null=True, blank=True,
#                               verbose_name=_(u'Subject'))
#     body= models.TextField(verbose_name=_(u'Request'))
#     sent= models.DateField(auto_now_add= True, verbose_name=_(u'Request'))
#     # TO-DO: save tags and keywords (depend on the search mechanism)


# class AuthorityResponse(models.Model):
#     """
#     Response from Authority.
#     """
#     # TO-DO


# class UserShare(models.Model):
#     """
#     User shared documents from the Response of Authority.
#     """
#     # TO-DO
