from django.conf import settings
from django.conf.urls import patterns, url
from apps.browser.forms import ModelSearchForm
from haystack.query import SearchQuerySet
from haystack.views import SearchView

# urlpatterns = patterns('apps.browser.views',
#     # Search over models' data, no filter.
#     url(r'^$', 'search_all', {'template': 'search/search.html',
#         'form': ModelSearchForm}, name='search_all'),
# )

sqs= SearchQuerySet().all()

urlpatterns= patterns('haystack.views',
    url(r'^$', SearchView(
        template='search/search.html',
        searchqueryset=sqs,
        form_class=ModelSearchForm
    ), name='haystack_search'),
)
