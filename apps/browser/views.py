from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.generic.simple import direct_to_template
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.template import RequestContext
from django.db.models import Q

from apps.vocabulary.models import AuthorityCategory, AuthorityProfile, Territory
from sezam.settings import PAGINATE_BY


def display_index(request, **kwargs):
    """
    Display index page.
    """
    template= kwargs.get('template', 'index')
    return render_to_response(template, {
        'page_title': _(u'Name')},
        context_instance=RequestContext(request))


def display_authority(request, **kwargs):
    """
    Display the list of authority, filtered.
    """
    if request.method == 'POST':
        raise Http404
    template= kwargs.get('template', 'authority.html')
    data= {'page_title': _(u'Public Authorities')}
    return render_to_response(template, data,
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
                if AuthorityProfile.objects.filter(category=child).count() == 0:
                    append= False
            if append:
                data.append({'label': child.name, 'id': child.id,
                    'load_on_demand': False if child.is_leaf_node() else True})
    else:
        # The first 2 levels by default.
        for root in AuthorityCategory.objects.root_nodes().order_by('order'):
            root_dict= {'label': '<h4>%s</h4>' % root.name, 'id': root.id, 'children': []}
            for child in root.get_children():
                root_dict['children'].append({'load_on_demand': True,
                    'label': child.name, 'id': child.id})
            data.append(root_dict)
    return HttpResponse(json.dumps(data))


def retrieve_authority_list(id=None):
    """
    Retrieve the list of Authorities from the db,
    depending on whether a Category id specified or not.
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
        return AuthorityProfile.objects.filter(category__in=category)\
            .order_by('name')
    else:
        return AuthorityProfile.objects.all().order_by('name')


def get_authority_list(request, id=None, **kwargs):
    """
    Display the list of authority, filtered.
    """
    template= kwargs.get('template', 'authority_list')
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

    print {'results': results,
        'total_item': items, 'current': page,
        'pageURI': pageURI, 'per_page': PAGINATE_BY}

    return render_to_response(template, {'results': results,
        'total_item': items, 'current': page,
        'pageURI': pageURI, 'per_page': PAGINATE_BY},
        context_instance=RequestContext(request))
    # TO-DO: Implement URI Generator for pageURI: http://www.djangosnippets.org/snippets/1734/


def get_authority_info(request, slug, **kwargs):
    """
    Display all the details of a selected authority.
    """
    template= kwargs.get('template', 'authority_list')
    if request.method == 'POST':
        raise Http404
    try:
        result= AuthorityProfile.objects.get(slug=slug)
    except AuthorityProfile.MultipleObjectsReturned:
        result= AuthorityProfile.objects.filter(slug=slug).order_by('name')[0]
    except AuthorityCategory.DoesNotExist:
        raise Http404

    # Fill categories for breadcrumbs.
    category, categories= None, []
    try:
        category= result.category
    except:
        category= None
    if category:
        try:
            categories= list(category.get_ancestors())
        except:
            categories= []
        categories.append(category)

    return render_to_response(template, {'result': result,
                                         'categories': categories,
                                         'page_title': result.name},
        context_instance=RequestContext(request))
