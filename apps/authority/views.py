from django.shortcuts import render_to_response
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse, Http404
from django.views.generic.simple import direct_to_template
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.template import RequestContext

from apps.vocabulary.models import AuthorityCategory, Territory, AuthorityProfile
from apps.pia_request.forms import MakeRequestForm, PIAFilterForm
from apps.pia_request.models import PIARequest, PIAThread, PIA_REQUEST_STATUS
from apps.backend.utils import process_filter_request
from apps.browser.forms import ModelSearchForm
from sezam.settings import PAGINATE_BY


def display_authority(request, **kwargs):
    """
    Display the list of authority, filtered.
    """
    if request.method == 'POST':
        raise Http404
    user_message= request.session.pop('user_message', {})
    template= kwargs.get('template', 'authorities.html')
    search_only= kwargs.get('search_only', True)
    try:
        q= request.GET['q']
        form= ModelSearchForm(request.GET)
    except:
        form= ModelSearchForm()

    return render_to_response(template, {'form': form,
        'user_message': user_message, 'search_only': search_only,
        'page_title': _(u'Public Authorities')},
        context_instance=RequestContext(request))


def get_authority_tree(request, **kwargs):
    """
    Display authority tree.
    """
    # Request mode for tree load_on_demand, don't load a page without it.
    rq= request.GET.get('_', None)
    if not rq:
        raise Http404
    data= []
    node_id= request.GET.get('node', None)
    if node_id:
        # Return subtree of the requested node.
        try:
            node= AuthorityCategory.objects.get(id=int(node_id))
        except AuthorityCategory.DoesNotExist:
            raise Http404
        for child in node.get_children().order_by('name'):
            append= True
            if child.is_leaf_node():
                if AuthorityProfile.objects.filter(
                        category=child, active=True).count() == 0:
                    append= False
            if append:
                data.append({'label': child.name, 'id': child.id,
                    'load_on_demand': False if child.is_leaf_node() else True})
    else:
        # The first 2 levels by default.
        for root in AuthorityCategory.objects.root_nodes().order_by('order', 'name'):
            root_dict= {'label': '<h4>%s</h4>' % root.name, 'id': root.id,
                        'children': []}
            for child in root.get_children():
                root_dict['children'].append({'load_on_demand': True,
                    'label': child.name, 'id': child.id})
            data.append(root_dict)
    return HttpResponse(json.dumps(data))


def retrieve_authority_list(id=None):
    """ Retrieve the list of Authorities from the db, depending on whether
        a Category id specified or not.
        """
    if id:
        try:
            id= int(id)
        except:
            return None

        try:
            category= AuthorityCategory.objects.get(id=id)
        except AuthorityCategory.MultipleObjectsReturned:
            category= AuthorityCategory.objects.filter(id=id)[0]
        except AuthorityCategory.DoesNotExist:
            return None

        category= [category]
        if not category[0].is_leaf_node():
            try:
                category.extend(category[0].get_descendants())
            except Exception as e:
                pass
        return AuthorityProfile.objects.filter(
            category__in=category, active=True).order_by('name')
    else:
        return AuthorityProfile.objects.filter(active=True).order_by('name')


def get_authority_list(request, id=None, **kwargs):
    """ Display the list of authority, filtered.
        """
    template= kwargs.get('template', 'includes/authority_list')
    if request.method == 'POST':
        raise Http404

    result= retrieve_authority_list(id)
    if result is None:
        raise Http404
    items= result.count()

    paginator= Paginator(result, PAGINATE_BY)
    try:
        page= int(request.GET.get('page', '1'))
    except ValueError:
        page= 1
    try:
        results= paginator.page(page)
    except (EmptyPage, InvalidPage):
        results= paginator.page(paginator.num_pages)

    # Pagination depends on the current node.
    if id:
        pageURI= '%s/?page=' % str(id)
    else:
        pageURI= '?page='

    return render_to_response(template, {'page': results,
        'total_item': items, 'current': page,
        'pageURI': pageURI, 'per_page': PAGINATE_BY},
        context_instance=RequestContext(request))
    # TO-DO: Implement URI Generator for pageURI: http://www.djangosnippets.org/snippets/1734/


def get_authority(slug):
    """
    Extract Authority from the model by its slug.
    """
    query= {'slug': slug, 'active': True}
    try:
        return AuthorityProfile.objects.get(**query)
    except AuthorityProfile.MultipleObjectsReturned:
        return AuthorityProfile.objects.filter(**query).order_by('name')[0]
    except AuthorityCategory.DoesNotExist:
        return None


def get_authority_info(request, slug, **kwargs):
    """
    Display the details on the selected authority:
    * Authority info (contacts, description, etc.)
    * Authority requests
    * Fill the Breadcrumb by category.
    """
    template= kwargs.get('template', 'authority.html')
    user_message= request.session.pop('user_message', {})
    if request.method == 'POST':
        raise Http404

    authority= get_authority(slug)
    if authority is None:
        raise Http404

    # Fill categories for breadcrumbs.
    category, categories= None, []
    try:
        category= authority.category
    except:
        category= None
    if category:
        try:
            categories= list(category.get_ancestors())
        except:
            categories= []
        categories.append(category)

    # Fill requests list.
    initial, query, urlparams= process_filter_request(
        request, PIA_REQUEST_STATUS)

    query.update({'authority': authority})

    try: # Query db.
        pia_requests= PIARequest.objects.filter(**query)
    except Exception as e:
        pia_requests= list()

    paginator= Paginator(pia_requests, PAGINATE_BY)
    try:
        page= int(request.GET.get('page', '1'))
    except ValueError:
        page= 1
    try:
        results= paginator.page(page)
    except (EmptyPage, InvalidPage):
        results= paginator.page(paginator.num_pages)

    return render_to_response(template, {'authority': authority,
        'page': results, 'categories': categories,
        'form': PIAFilterForm(initial=initial), 'user_message': user_message,
        'page_title': authority.name, 'urlparams': urlparams},
        context_instance=RequestContext(request))


def find_authority(request, **kwargs):
    """ Look for the Authority to make request to.
        """
    template= kwargs.get('template', 'index.html')
    return render_to_response(template, {
        'page_title': _(u'Look for the authority')},
        context_instance=RequestContext(request))
