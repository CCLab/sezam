from django.utils.translation import ugettext_lazy as _
from django.forms import *

from apps.vocabulary.models import UserProfile
from apps.backend.utils import COUNTRIES

class UserProfileForm(ModelForm):
    """ UserProfile form.
        """
    description= CharField(label=_(u'About you'), required=False,
        widget=forms.Textarea(attrs={'class': 'span4', 'rows': 3, 'id': 'id_comment'}))
    company= CharField(label=_(u'Company'), required=False,
                       widget=TextInput(attrs={'class': 'span3',
                            'placeholder': _(u'Company/organizaion')}))
    # ADDRESS DETAILS
    address_street= CharField(label=_(u'Address'), required=False,
        widget=TextInput(attrs={'class': 'span4',
            'placeholder': _(u'Street name, building and office number')}))
    address_line1= CharField(label=_(u'Address line 1'), required=False,
                             widget=TextInput(attrs={'class': 'span4'}))
    address_line2= CharField(label=_(u'Address line 2'), required=False,
                             widget=TextInput(attrs={'class': 'span4'}))
    address_postalcode= CharField(label=_(u'Postal code'), required=False,
        widget=TextInput(attrs={'class': 'span1', 'placeholder': '20354'}))
    address_city= CharField(label=_(u'City'), required=False,
                            widget=TextInput(attrs={'class': 'span2'}))
    address_country= ChoiceField(label=_(u'Country'), required=False,
                                 choices=COUNTRIES)
    # TELEPHONES
    tel_code= CharField(label=_(u'Tel code'), required=False,
        widget=TextInput(attrs={'class': 'span1', 'placeholder': _(u'code')}))
    tel_number= CharField(label=_(u'Tel.'), required=False,
        widget=TextInput(attrs={'class': 'span2', 'placeholder': _(u'number')}))
    tel_internal= CharField(label=_(u'Internal'), required=False,
        widget=TextInput(attrs={'class': 'span1', 'placeholder': _(u'internal')}))
    # WWW
    web_site= URLField(label=_(u'Web-site'), required=False,
                       widget=TextInput(attrs={'class': 'span3',
                                        'placeholder': _(u'http://')}))
    # AVATAR
    userpic= CharField(label=_(u'Choose a picture'),
                      widget=TextInput(attrs={'style': 'display: none;'}))

class UserpicForm(Form):
    """ Simple form for chosing user pic.
        """
    file_path= ImageField(label=_(u'Photo of you'),
                          widget=ClearableFileInput(attrs={'class': 'span3'}))