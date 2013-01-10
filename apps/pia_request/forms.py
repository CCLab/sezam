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
        # that there can be 'trusted' users, who should have an access to a
        # 'mass requests' feature (e.g. request to several selected authorities).
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


    def __fill_emails(self):
        """
        Authorities and user emails should always be filled!

        Warning! It is not a real email message, we only need one correct (!)
        email address in `email_to`, even if there are several Authorities
        selected. So, we simply use the first one's email address to fill out
        `email_to`.
        """
        # WARNING! This is obviously a bad design, but forced by the requirement,
        # that there can be 'trusted' users, who should have an access to a
        # 'mass requests' feature (e.g. request to several selected authorities).

        def _obj(m, i):
            _id= lambda x: x[0] if isinstance(x, list) else x
            return m.objects.get(id= int(_id(i)))

        # If the form has an instance, there is no need to fill out emails.
        if self.instance.id is not None:
            return (True, True)

        email_from, email_to= None, None

        # Filling emails on form submit.
        if self.data:
            data_dict= dict(self.data)

            try: # Check user's email.
                email_from= self.data['email_from']
            except: pass
            if email_from is None: # No user's mail, fill it!
                user= _obj(User, self.data['user'])
                email_from= user.email

            try: # Check Authority email.
                email_to= self.data['email_to']
            except: pass
            if email_to is None: # No authority's mail, fill it!
                authority= _obj(AuthorityProfile, self.data['authority'])
                email_to= authority.email

            self.data['email_from'], self.data['email_to']= email_from, email_to

        # Filling emails on form open.
        elif self.initial:
            try: # Check user's email.
                email_from= self.fields['email_from'].initial
            except: pass
            if email_from is None: # No user's mail, fill it!
                try:
                    email_from= self.initial['user'].email
                except AttributeError:
                    user= _obj(User, self.initial['user'])
                    email_from= user.email

            try: # Check Authority's email.
                email_to= self.fields['email_to'].initial
            except: pass
            if email_to is None: # No Authority's mail, fill it!
                try:
                    email_to= self.initial['authority'][0].email
                except AttributeError:
                    authority= _obj(AuthorityProfile, self.initial['authority'])
                    email_to= authority.email

            self.fields['email_from'].initial, self.fields['email_to'].initial= email_from, email_to

        return (email_from, email_to)
    

    def __init__(self, *args, **kwargs):
        """
        Initializing request form with message template.
        """
        super(MakeRequestForm, self).__init__(*args, **kwargs)

        initial= kwargs.pop('initial', None)
        if initial:
            self.fields['authority'].initial= initial['authority']
            self.fields['user'].initial= initial['user']
            try:
                self.fields['body'].initial= initial['body']
            except KeyError:
                self.fields['body'].initial= REQUEST_BODY_TEMPLATE % {
                    'name': initial['authority'][0].official_short_name(),
                    'user_name': initial['user'].get_full_name(),
                    'space3': SPACER*3, 'space1': SPACER}
            try:
                self.fields['subject'].initial= initial['subject']
            except KeyError:
                self.fields['subject'].initial= ''
        else:
            self.fields['body'].initial= REQUEST_BODY_TEMPLATE % {
                'name': ' ', 'user_name': ' ', 'space3': SPACER*3, 'space1': SPACER}

        # Draft is a PIAMessage, so the e-mails should always be filled.
        emails= self.__fill_emails()
        if emails[0] is None or emails[1] is None:
            print "WARNING! Emails are still None"


class ReplyDraftForm(forms.ModelForm):
    """
    Much reduced version of MakeRequestForm, used for drafts of the replies
    only, not for general ones.
    """
    subject= forms.CharField(label=_(u'Subject'),
        widget=forms.TextInput(attrs={'class': 'span6'}))
    body= forms.CharField(label=_(u'Reply'),
        widget=forms.Textarea(attrs={'class': 'span7'}))

    class Meta:
        model= PIARequestDraft

    def __init__(self, *args, **kwargs):
        initial= kwargs.pop('initial', None)
        super(ReplyDraftForm, self).__init__(*args, **kwargs)
        if initial:
            for init_key, init_val in initial.iteritems():
                self.fields[init_key].initial= init_val


class CommentForm(forms.Form):
    """
    Form for comments, can also be used in Blog, or anywhere where it isn't
    necessary to have a subject and from-to fields. Simple text.
    """
    comment= forms.CharField(label=_(u'Your comment here'),
        widget=forms.Textarea(attrs={'class': 'span6', 'id': 'id_comment'}))


class PIAFilterForm(forms.Form):
    """
    Form for filtering request list.
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
