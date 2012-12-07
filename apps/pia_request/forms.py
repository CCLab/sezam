from django.utils.translation import ugettext_lazy as _
from django import forms

REQUEST_BODY_TEMPLATE= _(u"Dear %(name)s, %(space3)sYours faithfully, %(space1)s%(user_name)s")
SPACER="""
"""

class MakeRequestForm(forms.Form):
    authority_name= forms.CharField(
        required=False, # It IS (of course) required, but it's checked elsewhere.
        label=_(u'You are sending a request to'),
        widget=forms.TextInput(
            attrs={
                'class': 'span',
                'readonly': '',
                'style': 'display: none;'
                }
            )
        )
    authority_slug= forms.CharField(
        required=False, # It IS (of course) required, but it's checked elsewhere.
        widget=forms.TextInput(
            attrs={
                'class': 'span',
                'readonly': '',
                'style': 'display: none;'
                }
            )
        )
    request_subject= forms.CharField(
        label=_(u'Request summary'),
        widget=forms.TextInput(
            attrs={
                'class': 'span5',
                'placeholder': _(u'Subject')
                }
            )
        )
    request_body= forms.CharField(
        label=_(u'Your request'),
        widget=forms.Textarea(
            attrs={
                'class': 'span4',
                }
            ),
        )

    def __init__(self, *args, **kwargs):
        initial= kwargs.pop('initial', None)
        super(MakeRequestForm, self).__init__(*args, **kwargs)
        if initial:
            try:
                self.fields['request_body'].initial= initial['request_body']
                self.fields['request_subject'].initial= initial['request_subject']
            except KeyError:
                self.fields['request_body'].initial= REQUEST_BODY_TEMPLATE % {
                    'name': initial['authority_name'],
                    'user_name': initial['user_name'],
                    'space3': SPACER*3, 'space1': SPACER}
                self.fields['request_subject'].initial= ''
            self.fields['authority_name'].initial= initial['authority_name']
            self.fields['authority_slug'].initial= initial['authority_slug']
        else:
            self.fields['request_body'].initial= REQUEST_BODY_TEMPLATE % {
                'name': ' ', 'user_name': ' ', 'space3': SPACER*3, 'space1': SPACER}
            self.fields['request_subject'].initial= ''
            self.fields['authority_name'].initial= ''
            self.fields['authority_slug'].initial= ''


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