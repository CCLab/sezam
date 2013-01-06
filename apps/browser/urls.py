from django.conf import settings
from django.conf.urls import patterns, url
from apps.browser.forms import ModelSearchForm
from haystack.query import SearchQuerySet
from haystack.views import SearchView

sqs= SearchQuerySet().all()

urlpatterns= patterns('haystack.views',
    url(r'^$', SearchView(
        template='search/search.html',
        searchqueryset=sqs,
        form_class=ModelSearchForm
    ), name='haystack_search'),
)
