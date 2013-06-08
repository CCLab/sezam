"""
Userprofile app forms
"""

from django.contrib.auth.models import User 
from django.core.validators import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelForm, CharField, Textarea, TextInput, ChoiceField, URLField, Form, \
    ImageField, ClearableFileInput, BooleanField, CheckboxInput

from registration.forms import RegistrationForm
from apps.backend import COUNTRIES

class UserProfileForm(ModelForm):
    """ UserProfile form.
        """
    description = CharField(label=_(u'About you'), required=False,
        widget=Textarea(attrs={'class': 'span4', 'rows': 3, 'id': 'id_comment'}))
    company = CharField(label=_(u'Company'), required=False,
                       widget=TextInput(attrs={'class': 'span3',
                            'placeholder': _(u'Company/organizaion')}))
    # ADDRESS DETAILS
    address_street = CharField(label=_(u'Address'), required=False,
        widget=TextInput(attrs={'class': 'span4',
            'placeholder': _(u'Street name, building and office number')}))
    address_line1 = CharField(label=_(u'Address line 1'), required=False,
                             widget=TextInput(attrs={'class': 'span4'}))
    address_line2 = CharField(label=_(u'Address line 2'), required=False,
                             widget=TextInput(attrs={'class': 'span4'}))
    address_postalcode = CharField(label=_(u'Postal code'), required=False,
        widget=TextInput(attrs={'class': 'span1', 'placeholder': '20354'}))
    address_city = CharField(label=_(u'City'), required=False,
                            widget=TextInput(attrs={'class': 'span2'}))
    address_country = ChoiceField(label=_(u'Country'), required=False,
                                 choices=COUNTRIES)
    # TELEPHONES
    tel_code = CharField(label=_(u'Tel code'), required=False,
        widget=TextInput(attrs={'class': 'span1', 'placeholder': _(u'code')}))
    tel_number = CharField(label=_(u'Tel.'), required=False,
        widget=TextInput(attrs={'class': 'span2', 'placeholder': _(u'number')}))
    tel_internal = CharField(label=_(u'Internal'), required=False,
        widget=TextInput(attrs={'class': 'span1', 'placeholder': _(u'internal')}))
    # WWW
    web_site = URLField(label=_(u'Web-site'), required=False,
                       widget=TextInput(attrs={'class': 'span3',
                                        'placeholder': _(u'http://')}))
    # AVATAR
    userpic = CharField(label=_(u'Choose a picture'),
                      widget=TextInput(attrs={'style': 'display: none;'}))

class UserpicForm(Form):
    """ Simple form for chosing user pic.
        """
    file_path = ImageField(label=_(u'Photo of you'),
                          widget=ClearableFileInput(attrs={'class': 'span3'}))

attrs_dict = {'class': 'required'}

class RegistrationFormUniqueEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which enforces uniqueness of
    email addresses.
    
    """
    # DK change - add first and last name, tos
    first_name = CharField(max_length=200,
                                  widget=TextInput(attrs=attrs_dict),
                                  label=_("First name"))
    last_name = CharField(max_length=200,
                                 widget=TextInput(attrs=attrs_dict),
                                 label=_("Last name"))
    tos = BooleanField(widget=CheckboxInput(attrs=attrs_dict),
                             label=mark_safe(_(u'<a href="/regulamin">I have read and agree to the Terms of Service<a/>')),
                             error_messages={'required': _("You must agree to the terms to register")})
    
    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.
        
        """
        if User.objects.filter(email__iexact=self.cleaned_data['email']):
            raise ValidationError(_("This email address is already in use. Please supply a different email address."))
        return self.cleaned_data['email']

