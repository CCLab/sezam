from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django import forms

from apps.vocabulary.models import AuthorityProfile
from apps.pia_request.models import PIARequestDraft

REQUEST_BODY_TEMPLATE= _(u"Dear %(name)s, %(space3)sYours faithfully, %(space1)s%(user_name)s")
SPACER="""
"""

class MakeRequestForm(forms.ModelForm):
    authority= forms.ModelMultipleChoiceField(label=_(u'You are sending a request to'),
        queryset=AuthorityProfile.objects.filter(active=True).order_by('name'),
        widget=forms.SelectMultiple(attrs={'class': 'span4', 'rows': "24"}))
    subject= forms.CharField(label=_(u'Request summary'),
        widget=forms.TextInput(attrs={'class': 'span5', 'placeholder': _(u'Subject')}))
    body= forms.CharField(label=_(u'Your request'),
        widget=forms.Textarea(attrs={'class': 'span4'}))
    user= forms.ModelChoiceField(label=_(u'User'),
        queryset=User.objects.filter(is_active=True),
        widget=forms.TextInput(attrs={'style': 'display:none'}))

    class Meta:
        model= PIARequestDraft

    def get_authority_label(self):
        """
        Return a label of an authority.
        Warning! Works only for the cases of a sigle Authority in a Draft.
        """
        # WARNING! This is obviously a bad design, but forced by the requirement,
        # that there can be 'trusted' users, who should have an access to a mass
        # requests (to several selected authorities). Gottabe sthn smarter!
        authority_id= None
        try:
            return self.fields['authority'].initial[0].name
        except:
            try:
                authority_id= self.initial['authority']
            except:
                try:
                    authority_id= self.data['authority']
                except: pass
        if authority_id:
            if isinstance(authority_id, basestring):
                try:
                    return AuthorityProfile.objects.get(pk=int(authority_id))
                except: pass
            elif isinstance(authority_id, list):
                try:
                    return AuthorityProfile.objects.get(pk=int(authority_id[0]))
                except: pass
        return ''

    def __init__(self, *args, **kwargs):
        """
        Initializing request form with message template and authority slugs.
        Slugs are necessary to control if there is any Authority is selected,
        and if not, re-fill it using slugs.
        """
        def _get_official_name_short():
            if len(initial['authority']) == 1:
                return '%s %s' % (initial['authority'][0].official_name,
                                  initial['authority'][0].official_lastname)
            else:
                return ''
        
        super(MakeRequestForm, self).__init__(*args, **kwargs)

        initial= kwargs.pop('initial', None)
        if initial:
            self.fields['authority'].initial= initial['authority']
            self.fields['user'].initial= initial['user']
            try:
                self.fields['body'].initial= initial['body']
            except KeyError:
                self.fields['body'].initial= REQUEST_BODY_TEMPLATE % {
                    'name': _get_official_name_short(),
                    'user_name': initial['user'].get_full_name(),
                    'space3': SPACER*3, 'space1': SPACER}
            try:
                self.fields['subject'].initial= initial['subject']
            except KeyError:
                self.fields['subject'].initial= ''
        else:
            self.fields['body'].initial= REQUEST_BODY_TEMPLATE % {
                'name': ' ', 'user_name': ' ', 'space3': SPACER*3, 'space1': SPACER}
            self.fields['subject'].initial= ''
            self.fields['authority'].initial= None
            self.fields['user'].initial= None


class ReplyDraftForm(forms.Form):
    """ Much reduced version of MakeRequestForm, used for drafts of the replies
        only, not for general ones.
        """
    subject= forms.CharField(label=_(u'Subject'),
        widget=forms.TextInput(attrs={'class': 'span6'}))
    body= forms.CharField(label=_(u'Reply'),
        widget=forms.Textarea(attrs={'class': 'span7', 'id': 'id_request_body'}))

    def __init__(self, *args, **kwargs):
        initial= kwargs.pop('initial', None)
        super(ReplyDraftForm, self).__init__(*args, **kwargs)
        if initial:
            for init_key, init_val in initial.iteritems():
                self.fields[init_key].initial= init_val


class CommentForm(forms.Form):
    """ Form for comments, can also be used in Blog, or anywhere where it isn't
        necessary to have a subject and from-to fields. Simple text.
        """
    comment= forms.CharField(label=_(u'Your comment here'),
        widget=forms.Textarea(attrs={'class': 'span6', 'id': 'id_comment'}))


class PIAFilterForm(forms.Form):
    """ Form for filtering request list.
        """
    keywords= forms.CharField(label=_(u'Keywords'), widget=forms.TextInput(
        attrs={'class': 'span3', 'placeholder': _(u'Keywords')}))
    date_after= forms.DateField(required=False, label=_(u'Made between'),
        widget=forms.TextInput(
            attrs={'class': 'span2', 'id': 'date_after'}))
    date_before= forms.DateField(required=False, label=_(u'and'),
        widget=forms.TextInput(
            attrs={'class': 'span2', 'id': 'date_before'}))
    status= forms.ChoiceField(widget=forms.RadioSelect,
        choices= (
            ('all', 'all',),
            ('successful', 'successful',),
            ('unsuccessful', 'unsuccessful',),
            ('unresolved', 'unresolved')))

    def __init__(self, *args, **kwargs):
        initial= kwargs.pop('initial', None)
        super(PIAFilterForm, self).__init__(*args, **kwargs)
        if initial:
            for init_key, init_val in initial.iteritems():
                self.fields[init_key].initial= init_val
