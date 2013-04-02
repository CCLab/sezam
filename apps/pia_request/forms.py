from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django import forms

from apps.vocabulary.models import AuthorityProfile
from apps.pia_request.models import PIARequestDraft

REQUEST_BODY_TEMPLATE= _(u"Dear Sir/Madam, %(space3)sYours faithfully %(space1)s%(user_name)s")
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
                    'user_name': initial['user'].get_full_name(),
                    'space3': SPACER*3, 'space1': SPACER}
            try:
                self.fields['subject'].initial= initial['subject']
            except KeyError:
                self.fields['subject'].initial= ''
        else:
            self.fields['body'].initial= REQUEST_BODY_TEMPLATE % {
                'user_name': ' ', 'space3': SPACER*3, 'space1': SPACER}

        # Draft is a PIAMessage, so the e-mails should always be filled.
        ctrl= DraftFormControl().ensure_emails(self)
        if ctrl == 'OK':
            pass


class ReplyDraftForm(forms.ModelForm):
    """
    Much reduced version of MakeRequestForm, used for drafts of the replies
    only, not for general ones.
    """
    subject= forms.CharField(label=_(u'Subject'),
        widget=forms.TextInput(attrs={'class': 'span6'}))
    body= forms.CharField(label=_(u'Reply'),
        widget=forms.Textarea(attrs={'class': 'span7'}))
    user= forms.ModelChoiceField(label=_(u'User'),
        queryset=User.objects.filter(is_active=True))
    authority= forms.ModelMultipleChoiceField(
        label=_(u'You are sending a request to'),
        queryset=AuthorityProfile.objects.filter(active=True).order_by('name'))

    class Meta:
        model= PIARequestDraft

    def __init__(self, *args, **kwargs):
        super(ReplyDraftForm, self).__init__(*args, **kwargs)

        initial= kwargs.pop('initial', None)
        if initial:
            for k, v in initial.iteritems():
                self.fields[k].initial= v

        # Draft is a PIAMessage, so the e-mails should always be filled.
        ctrl= DraftFormControl().ensure_emails(self)

        # All model choice fields in the form are hidden, no need to extract
        # all data for a form, only those selected.
        ctrl= DraftFormControl().update_querysets(self)


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
            for k, v in initial.iteritems():
                self.fields[k].initial= v


class DraftFormControl():
    """
    """
    valid_form_classes= [MakeRequestForm, ReplyDraftForm]
    repr_valid_form_classes= [repr(a) for a in valid_form_classes]
    message= {
        'FormNotSpecified': "Error! Form not specified!",
        'WrongObject': "Error! Wrong object! Valid objects are forms of classes: %s" % ', '.join(repr_valid_form_classes),
        'WrongClass': "Error! Wrong class form! Valid classes are: %s" % ', '.join(repr_valid_form_classes),
        }
    
    def __init__(self, form=None):
        self.email_from= None
        self.email_to= None
        self.form= form

    def __validate_form(self, form):
        if form is None:
            if self.form is None:
                return False, message['FormNotSpecified']
            else:
                form= self.form
        try:
            form_class= form.__class__
        except:
            return False, message['WrongObject']
        if form_class not in self.valid_form_classes:
            return False, message['WrongClass']
        
        return True, form

    def __get_obj(self, m, i):
        _id= lambda x: x[0] if isinstance(x, list) else x
        return m.objects.get(id= int(_id(i)))

    def __extract_id(self, d):
        """
        Returns list of ids (even if one).
        """
        try:
            return [int(i.id) for i in d]
        except:
            return [int(d.id)]

    def __get_data(self, fo, fi):
        """
        Extract data from a field, be it initial or bound data.
        """
        if fo.instance.id is not None:
            try: # ManyRelatedManager?
                return getattr(fo.instance, fi).all()
            except: # RelatedManager?
                return getattr(fo.instance, fi)
        elif fo.initial:
            return fo.fields[fi].initial
        elif fo.data:
            return fo.data[fi]

    def __get_model(self, fo, fi):
        """
        Figure out the model from a field.
        """
        if fo.instance.id is not None:
            m= getattr(fo.instance, fi)
            try: # ModelMultipleChoiceField?
                return m.model
            except: pass
            try: # ModelChoiceField?
                return m.__class__
            except: pass
        elif fo.initial:
            try: # Initial can be a list.
                return fo.initial[fi][0].__class__
            except:
                return fo.initial[fi].__class__
        # If none of the above worked.
        return None

    def update_querysets(self, form=None, **kwargs):
        """
        All model choice fields in the form are hidden -
        no need to extract all data for a form, only those
        that define initials.
        """
        # Check if form parameter is correct.
        is_ok, response= self.__validate_form(form)
        if not is_ok:
            return response
        f= response

        fields= kwargs.get('fields', f.fields.keys())
        for field in fields:
            if f.fields[field].__class__ in [
                    forms.ModelMultipleChoiceField, forms.ModelChoiceField]:                
                model= self.__get_model(f, field)
                if model:
                    data= self.__get_data(f, field)
                    if data:
                        f.fields[field].queryset= model.objects.filter(
                            id__in=self.__extract_id(data))
        return 'OK'

    def ensure_emails(self, form=None, **kwargs):
        """
        Ensures that `email_from` and `email_to` fields are filled with
        data from Authority or User.
        """
        # Check if form parameter is correct.
        is_ok, response= self.__validate_form(form)
        if not is_ok:
            return response

        # Specify the 'material'.
        f= response
        email_from, email_to= None, None

        # If the form has an instance, there is no need to fill out emails.
        if f.instance.id is not None:
            return 'OK'

        # Filling emails on form submit.
        if f.data:
            try: # Check user's email.
                email_from= f.data['email_from']
            except: pass
            if (email_from is None) or (email_from.strip() == ''):
                user= self.__get_obj(User, f.data['user'])
                email_from= user.email

            try: # Check Authority email.
                email_to= f.data['email_to']
            except: pass
            if (email_to is None) or (email_to.strip() == ''):
                authority= self.__get_obj(AuthorityProfile, f.data['authority'])
                email_to= authority.email

            f.data['email_from'], f.data['email_to']= email_from, email_to

        # Filling emails on form open.
        elif f.initial:
            try: # Check user's email.
                email_from= f.fields['email_from'].initial
            except: pass
            if (email_from is None) or (email_from.strip() == ''):
                try:
                    email_from= f.initial['user'].email
                except AttributeError:
                    user= self.__get_obj(User, f.initial['user'])
                    email_from= user.email

            try: # Check Authority's email.
                email_to= f.fields['email_to'].initial
            except: pass
            if (email_to is None) or (email_to.strip() == ''):
                try:
                    email_to= f.initial['authority'][0].email
                except AttributeError:
                    authority= self.__get_obj(AuthorityProfile, f.initial['authority'])
                    email_to= authority.email

            f.fields['email_from'].initial, f.fields['email_to'].initial= email_from, email_to

        # Fill the attributes.
        self.form= f
        self.email_to= email_to
        self.email_from= email_from
        if f.fields['is_response']:
            # Swapping emails in case it's a manually entered reply.
            self.email_to= email_from
            self.email_from= email_to

        return 'OK'
