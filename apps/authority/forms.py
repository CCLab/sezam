from django.utils.translation import ugettext_lazy as _
from django import forms

from apps.vocabulary.models import AuthorityProfile

class AuthorityProfileForm(forms.ModelForm):
    name= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span5', 'placeholder': _(u'Authority name')}))
    official= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span2', 'placeholder': _(u'Position')}))
    official_name= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span2', 'placeholder': _(u'Name')}))
    official_lastname= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span2', 'placeholder': _(u'Last name')}))
    address_street= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span3', 'placeholder': _(u'Street name')}))
    address_num= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span2', 'placeholder': _(u'Building, floor, office')}))
    address_line1= forms.CharField(required=False,
        label=_(u'More address data'), widget=forms.TextInput(
            attrs={'class': 'span5', 'placeholder': _(u'Line 1')}))
    address_line2= forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'span5', 'placeholder': _(u'Line 2')}))
    address_postalcode= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span1', 'placeholder': _(u'Postal code'),}))
    address_city= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span4', 'placeholder': _(u'City')}))
    tel_code= forms.CharField(widget=forms.TextInput(
        attrs={'class': 'span1', 'placeholder': _(u'Code')}))
    tel_number= forms.CharField(label=_(u'Primary number'),
        widget=forms.TextInput(
            attrs={'class': 'span3', 'placeholder': _(u'Number')}))
    tel_internal= forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'span2', 'placeholder': _(u'Internal')}))
    tel1_code= forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'span1', 'placeholder': _(u'Code')}))
    tel1_number= forms.CharField(required=False, label=_(u'More telephones'),
        widget=forms.TextInput(
            attrs={'class': 'span3', 'placeholder': _(u'Number')}))
    tel2_code= forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'span1', 'placeholder': _(u'Code')}))
    tel2_number= forms.CharField(required=False, widget=forms.TextInput(
            attrs={'class': 'span3', 'placeholder': _(u'Number')}))
    fax_code= forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'span1', 'placeholder': _(u'Code')}))
    fax_number= forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'span3', 'placeholder': _(u'Fax number')}))
    email= forms.EmailField(widget=forms.TextInput(
        attrs={'class': 'span2', 'placeholder': _(u'Primary email')}))
    email_secretary= forms.EmailField(required=False, widget=forms.TextInput(
        attrs={'class': 'span2', 'placeholder': _(u'Secretary e-mail')}))
    email_info= forms.EmailField(required=False, widget=forms.TextInput(
        attrs={'class': 'span2', 'placeholder': _(u'Info e-mail')}))
    web_site= forms.URLField(required=False, widget=forms.TextInput(
        attrs={'class': 'span3', 'placeholder': _(u'Official web-site')}))
    web_site1= forms.URLField(required=False, widget=forms.TextInput(
        attrs={'class': 'span3', 'placeholder': _(u'Public Information Bulletin')}))
    description= forms.CharField(required=False, widget=forms.Textarea(
        attrs={'class': 'span6', 'placeholder': _(u'Description')}))
    slug= forms.TextInput(attrs={'style': 'display:none'})
    order= forms.TextInput(attrs={'style': 'display:none'})

    class Meta:
        model= AuthorityProfile

    def __init__(self, *args, **kwargs):
        """
        Initializing Authority profile form with initials template.
        """
        super(AuthorityProfileForm, self).__init__(*args, **kwargs)

        initial= kwargs.pop('initial', None)
        if initial:
            for k, v in initial.iteritems():
                self.fields[k].initial= v
