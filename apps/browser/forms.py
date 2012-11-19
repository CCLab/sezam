from django.utils.translation import ugettext_lazy as _
from django import forms

REQUEST_BODY_TEMPLATE= _(u"Dear %(name)s, %(space3)sYours faithfully, %(space1)s%(user_name)s")
SPACER="""
"""

class MakeRequestForm(forms.Form):
    authority_name= forms.CharField(max_length=1000,
        widget=forms.TextInput(attrs={'class': 'span5', 'readonly':''}),
        label=_(u'You are sending a request to'))
    request_subject= forms.CharField(max_length=1000, widget=forms.TextInput(
        attrs={'class': 'span5', 'placeholder': _(u'Subject')}),
        label=_(u'Request summary'))
    request_body= forms.CharField(widget=forms.Textarea(attrs={'class': 'span4'}),
        label=_(u'Your request'))

    def __init__(self, *args, **kwargs):
        initial= kwargs.pop('initial', None)
        super(MakeRequestForm, self).__init__(*args, **kwargs)
        self.fields['request_body'].initial= REQUEST_BODY_TEMPLATE % {
            'name': initial['authority_name'], 'user_name': initial['user_name'],
            'space3': SPACER*3, 'space1': SPACER,}
