""" Models for project-wide vocabularies.
    """

import re
from django.db.models import *
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

from apps.backend.utils import CountryField, slugify_unique
from sezam.settings import MEDIA_URL

class Vocabulary(Model):
    """ Abstract model for all vocabularies.
        """
    name= CharField(max_length=1000, verbose_name=_(u'Name'))
    order= IntegerField(default=100, verbose_name=_(u'Order'))

    class Meta:
        abstract= True
        ordering= ('order',)

    def __unicode__(self):
        return self.name


class SlugVocabulary(Model):
    """ Abstract model for all vocabularies with slug.
        """
    slug= SlugField(max_length=100, unique=True, verbose_name=_(u'Slug'))

    class Meta:
        abstract= True

    def __unicode__(self):
        return self.slug

    def save(self, *args, **kwargs):
	""" Override save: slugify uniquely.
        """
        self.slug= slugify_unique(self.name, self.__class__)
        super(SlugVocabulary, self).save(*args, **kwargs)


class TreeVocabulary(MPTTModel):
    """ Abstract class for tree-like vocabularies.
        """
    name= CharField(max_length=1000, verbose_name=_(u'Name'))
    parent= TreeForeignKey('self', null=True, blank=True,
                           related_name='children')
    order= IntegerField(default=100, null=True, verbose_name=_(u'Order'))

    class MPTTMeta:
        order_insertion_by= ('name',)

    class Meta:
        abstract= True

    def __unicode__(self):
        return self.name


class AuthorityCategory(TreeVocabulary, SlugVocabulary):
    """ A classification Tree for authorities.
        
        Only the leaf objects of this class can be used as foreign keys
        for Authority.
        """


class TerritoryType(Vocabulary):
    """ Type of the territory.
        For Poland: wojewodztwo, gmina, miasto, etc.
        """
    display_name= CharField(max_length=50, blank=True, null=True,
                            verbose_name=_(u'Name tp display'))


class Territory(AuthorityCategory):
    """ Classified vocabulary of the territories: Cities (Gmina), Provinces 
        (Wojewodstwo), District (Powiat).
        
        There is no vocabulary for Countries, as the platform is country
        specific. It is possible to adapt it for similar tasks in other
        countries than Poland, but it makes no sense to use it in several 
        counries simulteneously.
        """
    code= CharField(max_length=50, blank=True, null=True,
                    verbose_name=_(u'Territory Code'))
    type= ForeignKey(TerritoryType,
                     verbose_name=_(u'Territory Type'))

    class MPTTMeta:
        order_insertion_by= ('parent',)

    class Meta:
        ordering= ('parent',)


class AuthorityProfile(TreeVocabulary, SlugVocabulary):
    """ Authority reference.
        
        Inherits from TreeVocabulary to support Authority->Department relation.
        """
    description= TextField(null=True, blank=True,
                           verbose_name=_(u'Description'))
    notes= CharField(max_length=1000, null=True, blank=True,
                     verbose_name=_(u'Notes'))
    category= ForeignKey(AuthorityCategory,
                         verbose_name=_(u'Authority category'))
    # ADDRESS DETAILS
    address_street= CharField(max_length=200, verbose_name=_(u'Street'))
    address_num= CharField(max_length=200, verbose_name=_(u'Office'),
                           help_text=_(u'Building and office number'))
    address_line1= CharField(max_length=200, null=True, blank=True,
                             verbose_name=_(u'Address (additional line 1)'))
    address_line2= CharField(max_length=200, null=True, blank=True,
                             verbose_name=_(u'Address (additional line 2)'))
    address_postalcode= CharField(max_length=6,
        verbose_name=_(u'Postal code'), help_text=_(u'Digits only!'))
    address_city= CharField(max_length=100, verbose_name=_(u'City'))

    # TELEPHONES
    tel_code= CharField(max_length=3, verbose_name=_(u'tel code'),
                        help_text=_(u'Example: 45'))
    tel_number= CharField(max_length=20, verbose_name=_(u'Telephone'), # TO-DO: control format. Make char(9)!!!
                          help_text=_(u'Digits only! Example: 4430976'))
    tel_internal= CharField(max_length=50, null=True, blank=True,
                            verbose_name=_(u'Internal'))
    tel1_code= CharField(max_length=3, null=True, blank=True,
                         verbose_name=_(u'Tel 1 code'))
    tel1_number= CharField(max_length=20, null=True, blank=True,
                           verbose_name=_(u'Telephone 1'))
    tel2_code= CharField(max_length=3, null=True, blank=True,
                         verbose_name=_(u'Tel 2 code'))
    tel2_number= CharField(max_length=20, null=True, blank=True,
                           verbose_name=_(u'Telephone 2'))
    fax_code= CharField(max_length=3, null=True, blank=True,
                        verbose_name=_(u'Fax code'))
    fax_number= CharField(max_length=20, null=True, blank=True,
                          verbose_name=_(u'Fax'))
    # E-MAILS
    email= EmailField(max_length=254, verbose_name=_(u'E-mail'))
    email_secretary= EmailField(max_length=254, blank=True,
                                verbose_name=_(u'secretary e-mail'))
    email_info= EmailField(max_length=254, blank=True,
                           verbose_name=_(u'info e-mail'))

    # WWW
    web_site= URLField(null=True, blank=True, verbose_name=_(u'Web-site'))
    web_site1= URLField(null=True, blank=True, verbose_name=_(u'Web-site 1'),
                        help_text=_(u'Public Information Bulletin'))

    # Responsible person.
    official= CharField(max_length=200, verbose_name=_(u'Official'),
                        help_text=_(u'Title of official position'))
    official_name= CharField(max_length=200, verbose_name=_(u'Name'),
                             help_text=_(u'Official representative name'))
    official_lastname= CharField(max_length=200, verbose_name=_(u'Last name'),
        help_text=_(u'Official representative last name'))

    # When the record was created.
    created= DateField(auto_now_add=True, verbose_name=_(u'Created'))


    def save(self, *args, **kwargs):
	""" Override save: get rid of non-digits in postalcode, telephone numbers
        and codes.
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


class UserProfile(Model):
    """ Custom user profile with additional information.
        All the fields are optional, except of slug.
        
        UserProfile is not inherited from Vocabulary, since it doesn't need a
        name (his/her name is in User).
        """
    user= OneToOneField(User, primary_key=True, parent_link=True,
                        related_name='profile', verbose_name=_(u'User'))
    description= TextField(null=True, blank=True,
                           verbose_name=_(u'About'))
    company= CharField(max_length=300, null=True, blank=True,
                       verbose_name=_(u'Company/organizaion'))
    # ADDRESS DETAILS
    address_street= CharField(max_length=300, null=True, blank=True,
                                     verbose_name=_(u'Street'),
        help_text=_(u'Street name, building and office number'))
    address_line1= CharField(max_length=300, null=True, blank=True,
                             verbose_name=_(u'Address (additional line 1)'))
    address_line2= CharField(max_length=200, null=True, blank=True,
                             verbose_name=_(u'Address (additional line 2)'))
    address_postalcode= CharField(max_length=6, null=True, blank=True,
        verbose_name=_(u'Postal code'), help_text=_(u'Digits only!'))
    address_city= CharField(max_length=100, null=True, blank=True,
                            verbose_name=_(u'City'))
    address_country= CountryField(verbose_name=_(u'Country'))
    # TELEPHONES
    tel_code= CharField(max_length=3, null=True, blank=True,
        verbose_name=_(u'tel code'), help_text=_(u'Example: 45'))
    tel_number= CharField(max_length=20, null=True, blank=True,
        verbose_name=_(u'Telephone'),
        help_text=_(u'Digits only! Example: 504566462'))
    tel_internal= CharField(max_length=50, null=True, blank=True,
                            verbose_name=_(u'Internal'))
    # WWW
    web_site= URLField(null=True, blank=True,
                       verbose_name=_(u'Web-site'))
    # USERPIC
    userpic= CharField(max_length=20, default='default_userpic.gif',
        verbose_name=_(u'Userpic'), help_text=_(u'Choose a picture'))

    # WHEN THE RECORD WAS CREATED
    created= DateField(auto_now_add=True, verbose_name=_(u'Created'))

    def save(self, *args, **kwargs):
	""" Override save:
        - get rid of non-digits in postalcode, telephone numbers and codes.
        """
        try:
            self.address_postalcode= re.sub('[^0-9]+', '',
                                            self.address_postalcode)
            self.tel_code= re.sub('[^0-9]+', '', self.tel_code)
            self.tel_number= re.sub('[^0-9]+', '', self.tel_number)
        except: # Ignore errors, none of those fields are actually required.
            pass
        super(UserProfile, self).save(*args, **kwargs)

    def __unicode__(self):
        return '%s (%s)' % (self.user.username, self.user.get_full_name())
