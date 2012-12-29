from haystack import indexes

from django.utils.timezone import utc

from apps.vocabulary.models import AuthorityProfile
from apps.pia_request.models import PIAMessage, PIAThread, PIARequest

# WARNING! `clean_text_for_search` not only cleanse the text, but also
# downcodes all non-ASCII symbols from national alphabets.
# Do the same before searching!
from apps.backend.utils import clean_text_for_search

from datetime import datetime


class AuthorityProfileIndex(indexes.SearchIndex, indexes.Indexable):
    text= indexes.CharField(document=True, use_template=True)
    name= indexes.CharField(model_attr='name')
    address_full= indexes.CharField(model_attr='address_full')
    official_full_name= indexes.CharField(model_attr='official_full_name')
    report_text= indexes.CharField(null=True, model_attr='description')

    def get_model(self):
        return AuthorityProfile

    def prepare(self, object):
        self.prepared_data = super(AuthorityProfileIndex, self).prepare(object)
        # Clean the text.
        if self.prepared_data['text']:
            self.prepared_data['text']= clean_text_for_search(
                self.prepared_data['text'])
        if self.prepared_data['report_text'] is None:
            self.prepared_data['report_text']= ''
        return self.prepared_data

    def index_queryset(self):
        """
        Used when the entire index for model is updated.
        """
        return self.get_model().objects.filter(active=True)


class PIARequestIndex(indexes.SearchIndex, indexes.Indexable):
    text= indexes.CharField(document=True, use_template=True)
    user= indexes.CharField(model_attr='user__get_full_name')
    authority= indexes.CharField(model_attr='authority__name')
    summary= indexes.CharField(model_attr='summary')
    report_text= indexes.CharField(default='')

    def _till_now(self):
        return datetime.utcnow().replace(tzinfo=utc)
    
    def get_model(self):
        return PIARequest

    def prepare_thread(self, obj):
        return [msg.id for msg in obj.thread.filter(created__lte=self._till_now())]

    def prepare(self, object):
        self.prepared_data = super(PIARequestIndex, self).prepare(object)

        # Clean the text.
        if self.prepared_data['text']:

            # Clean what is ready.
            self.prepared_data['text']= clean_text_for_search(
                self.prepared_data['text'])

            # Extract all the messages from the PIAThread,
            # attach message pk with and escape sequence and
            # and append them to the end of `text`.
            for msg in object.thread.filter(
                    created__lte=self._till_now()).order_by('created'):

                # Marked with message id, append to the text.
                self.prepared_data['text'] += ' __msg__%s__ %s' % (
                    msg.id, clean_text_for_search(msg.body))

                # For reporting purposes storing a duplicate of the thread,
                # cleaned, but not downcoded.
                self.prepared_data['report_text'] += clean_text_for_search(
                    msg.body, perform_downcode=False)

        return self.prepared_data    

    def index_queryset(self):
        return self.get_model().objects.filter(created__lte=self._till_now())
