from haystack.forms import HighlightedModelSearchForm
from django import forms
from django.utils.translation import ugettext_lazy as _

from apps.pia_request.models import PIAThread
from apps.backend.utils import downcode

MODELS= {'piarequest': ['pia_request.piarequest'],
         'authority': ['vocabulary.authorityprofile'],
         'all': ['pia_request.piarequest', 'vocabulary.authorityprofile']}


class ModelSearchForm(HighlightedModelSearchForm):
    q= forms.CharField(required=False, label=_('Search'),
        widget=forms.TextInput(
            attrs={'class': 'search-query', 'placeholder': _(u'Search')}))

    def search(self):
        # Before-search processing goes here (downcode the phrase).
        # Preserve original `q` to put it back to the form after search.
        original_q= self.cleaned_data['q']
        self.cleaned_data['q']= downcode(self.cleaned_data['q'])

        # Figure out models based on the form data keys.
        models= []
        for k in dict(self.data).keys():
            if k != 'q':
                try:
                    models.extend(MODELS[k])
                except:
                    continue
        if len(models) == 0:
            models= MODELS['all']
        self.cleaned_data.update({'models': list(set(models))}) # Remove duplicates.

        # Based on `models` list, figure out filter status
        # to update the template.
        filter_status= [k for k, v in MODELS.iteritems() if models == v][0]
        self.cleaned_data.update({'model_filter': filter_status})

        # Search!
        lQuerySet= super(ModelSearchForm, self).search()

        # Set back the original value of the form's search field - 
        # it must be displayed correctly in the form.
        self.cleaned_data['q']= original_q

        return lQuerySet


class AppSearchForm(HighlightedModelSearchForm):
    piarequest= forms.ModelChoiceField(
        queryset=PIAThread.objects.all(), required=False)

    def search(self):
        lQuerySet= super(AppSearchForm, self).search()

        if ('pia_request.piarequest' in self.cleaned_data['models']) \
                or (len(self.cleaned_data['models']) == 0):
            lQuerySet= lQuerySet.filter(
                piarequest=self.cleaned_data['pia_request.piarequest'])

        return lQuerySet
