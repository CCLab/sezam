from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.views.generic.simple import direct_to_template
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.http import HttpResponse, Http404
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.template import RequestContext
from django.conf import settings

from haystack.query import SearchQuerySet

from datetime import datetime
import os, time, sys

from apps.browser.forms import ModelSearchForm
from apps.authority.forms import AuthorityProfileForm
from apps.vocabulary.models import AuthorityCategory, Territory, AuthorityProfile
from apps.pia_request.forms import MakeRequestForm, PIAFilterForm
from apps.pia_request.models import PIARequest, PIAThread, PIA_REQUEST_STATUS
from apps.backend import AppMessage, UnicodeWriter
from apps.backend.models import TaggedItem, EventNotification
from apps.backend.utils import process_filter_request, update_user_message,\
    send_mail_managers, get_domain_name

def autocomplete(request):
    """
    Autocomplete Authority names.
    """
    query= request.GET.get('q', '')
    sqs= SearchQuerySet().autocomplete(content_auto=query)
    suggestions= [result.content_auto for result in sqs][:15]
    the_data= json.dumps({'results': suggestions})
    return HttpResponse(the_data, content_type='application/json')

def display_authority(request, **kwargs):
    """
    Display the list of authorities, filtered.
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
    data= {'form': form,
           'search_only': search_only,
           'user_message': user_message,
           'page_title': _(u'Public Authorities')}
    return render_to_response(template, data, context_instance=RequestContext(request))

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
    """
    Retrieve the list of Authorities from the db, depending on whether
    a Category id specified or not.
    """
    if id:
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
    """
    Display the list of authority, filtered.
    """
    template= kwargs.get('template', 'includes/authority_list')
    if request.method == 'POST':
        raise Http404

    if id: # `id` is a node id here.
        try: # And it can only be int!
            id= int(id)
        except:
            raise Http404

    result= retrieve_authority_list(id)

    if result is None:
        raise Http404

    items= result.count()

    paginator= Paginator(result, settings.PAGINATE_BY)
    try:
        page= int(request.GET.get('page', '1'))
    except ValueError:
        page= 1
    try:
        results= paginator.page(page)
    except (EmptyPage, InvalidPage):
        results= paginator.page(paginator.num_pages)

    # Pagination depends on the current node.
    pageURI= '?page=%d' % page
    if id:
        pageURI= '/'.join([str(id), pageURI])        

    return render_to_response(template,
                              {'id': id,
                               'page': results,
                               'current': page,
                               'pageURI': pageURI,
                               'total_item': items,
                               'per_page': settings.PAGINATE_BY},
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

    # Check if the user is following the authority.
    following= False
    if not request.user.is_anonymous():
        content_type_id= ContentType.objects.get_for_model(authority.__class__).id
        try:
            item= TaggedItem.objects.get(object_id=authority.id,
                                         content_type_id=content_type_id)
        except TaggedItem.DoesNotExist:
            pass
        else:
            following= item.is_followed_by(request.user)

    # Fill requests list.
    initial, query, urlparams= process_filter_request(
        request, PIA_REQUEST_STATUS)

    query.update({'authority': authority})
    try: # Query db.
        pia_requests= PIARequest.objects.filter(**query)
    except Exception as e:
        pia_requests= list()

    paginator= Paginator(pia_requests, settings.PAGINATE_BY)
    try:
        page= int(request.GET.get('page', '1'))
    except ValueError:
        page= 1
    try:
        results= paginator.page(page)
    except (EmptyPage, InvalidPage):
        results= paginator.page(paginator.num_pages)

    return render_to_response(template,
                              {'authority': authority,
                               'following': following,
                               'page': results,
                               'categories': categories,
                               'form': PIAFilterForm(initial=initial),
                               'user_message': user_message,
                               'page_title': authority.name,
                               'urlparams': urlparams},
        context_instance=RequestContext(request))

def find_authority(request, **kwargs):
    """ Look for the Authority to make request to.
        """
    template= kwargs.get('template', 'index.html')
    return render_to_response(template, {
        'page_title': _(u'Look for the authority')},
        context_instance=RequestContext(request))

def add_authority(request, slug=None, **kwargs):
    """
    Add new Authority in case if it can't be found in the database.
    """
    user_message= request.session.pop('user_message', {})
    template= kwargs.get('template', 'add_record.html')
    admin_mail_template= 'emails/authority_added.txt'
    from_link= None

    # Show the form to enter Authority data.
    if request.method == 'GET':
        from_link= request.GET.get('from', None)
        initial= {'slug': 'slug', 'order': 100}
        form= AuthorityProfileForm(initial=initial)

    # Check if the form is correct, save Authority in the db.
    elif request.method == 'POST':
        form= AuthorityProfileForm(request.POST)
        if form.is_valid():
            data= form.cleaned_data
            authority= AuthorityProfile(**data)
            try:
                authority.save()
            except Exception as e:
                print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)
                user_message= update_user_message({}, e.args[0], 'fail')
                form= AuthorityProfileForm(instance=authority)
            if authority.id: # Added successfully.
                user_message= update_user_message(user_message,
                    AppMessage('AuthSavedInactive').message % authority.name,
                    'success')

                # Send notification to managers.
                subject= _(u'New authority in the db: ') + authority.name
                content= render_to_string(admin_mail_template, {
                    'authority': authority, 'user': request.user,
                    'domain': get_domain_name()})
                try:
                    send_mail_managers(subject, content, fail_silently=False,
                                       headers={'Reply-To': request.user.email})
                except Exception as e:
                    print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), e)

                # Create notifier.
                item= TaggedItem.objects.create(name=authority.name,
                                                content_object=authority)
                evnt= EventNotification.objects.create(
                    item=item, action='active', receiver=request.user,
                    summary='Authority %s becomes active' % authority.name)

                request.session['user_message']= user_message
                return redirect(reverse('display_authorities'))

    return render_to_response(template,
                              {'form': form,
                               'from': from_link,
                               'mode': 'authority',
                               'user_message': user_message,
                               'page_title': _(u'Add authority')},
        context_instance=RequestContext(request))

@login_required
def follow_authority(request, slug=None, **kwargs):
    """
    Add an item for a notification - any activity of the Authority:
    *PIA request to
    *response from.
    """
    # Show the form to enter Authority data.
    if request.method == 'POST':
        raise Http404
    try:
        authority= AuthorityProfile.objects.get(slug=slug)
    except:
        raise Http404

    # Create notifier.
    try:
        item= TaggedItem.objects.get(object_id=authority.id, name=authority.name,
            content_type_id=ContentType.objects.get_for_model(authority.__class__).id)
    except TaggedItem.DoesNotExist:
        item= TaggedItem.objects.create(name=authority.name,
                                        content_object=authority)
    for k, v in authority_events(authority).iteritems():
        try:
            evnt, created= EventNotification.objects.get_or_create(
                item=item, action=k, receiver=request.user, summary=v)
        except:
            pass # TO-DO: Log it!
    return redirect(request.META.get('HTTP_REFERER'))

@login_required
def unfollow_authority(request, slug=None, **kwargs):
    """
    Removes any activity of the Authority from a notification list
    """
    if request.method == 'POST':
        raise Http404
    try:
        authority= AuthorityProfile.objects.get(slug=slug)
    except:
        raise Http404

    try: # to get notifier.
        item= TaggedItem.objects.get(object_id=authority.id, name=authority.name,
            content_type_id=ContentType.objects.get_for_model(authority.__class__).id)
    except TaggedItem.DoesNotExist:
        return redirect(request.META.get('HTTP_REFERER'))

    for k, v in authority_events(authority).iteritems():
        try:
            evnt= EventNotification.objects.get(item=item, action=k,
                                                receiver=request.user, summary=v)
        except EventNotification.DoesNotExist:
            continue
        evnt.delete()

    # Check if there is any notification connected to this item.
    if not EventNotification.objects.filter(item=item):
        try: # to wipe it out.
            item.delete()
        except: pass
    return redirect(request.META.get('HTTP_REFERER'))

def download_authority_list(request, ext=None, **kwargs):
    """
    Download Authority vocabulary in a given format.

    The csv isn't created on each request, but taken from site_media.
    It is created new only in one case - if the file was created before
    the last change in the vocabulary.
    """
    if ext is None:
        return redirect(request.META.get('HTTP_REFERER'))
    if ext not in settings.DOWNLOAD_FORMATS.keys():
        raise Http404

    filename= '.'.join(['authorities', ext])
    response = HttpResponse()
    response['Content-Type']= settings.DOWNLOAD_FORMATS[ext]
    response['Content-Disposition']= 'attachment; filename=%s' % filename
    file_exist= True
    try:
        f= open(settings.DOWNLOAD_ROOT + filename).read()
    except IOError:
        file_exist= False

    if file_exist:
        # Update if it's older than the newest record.
        lastupdated_f= os.path.getmtime(settings.DOWNLOAD_ROOT + filename)
        lastupdated_a= AuthorityProfile.objects.all().order_by('-created')[0].created
        # Convert datetimefield to number of seconds since epoch.
        lastupdated_a= time.mktime(lastupdated_a.timetuple())
        if lastupdated_f < lastupdated_a:
            # If the file is updated last time earlier than the newest Authority
            # is enetered in the system, it is considered as if it didn't exist.
            file_exist= False

    if not file_exist:
        if ext == 'csv':
            f= authority2csv(filename)
        elif ext == 'pdf':
            f= authority2pdf(filename)

    response.write(f)
    return response

def authority2pdf(filename):
    """
    Writes a queryset of AuthorityProfile to PDF file.

    Returns open file descriptor.
    """
    return None

def authority2csv(filename):
    """
    Writes a queryset of AuthorityProfile to csv file.

    Returns open file descriptor.
    """
    def _get_category_field(field, category):
        if field == 'category_id':
            return str(category.id)
        elif field == 'category':
            return category.name
        elif field == 'category_parent':
            try:
                return str(category.parent.id)
            except AttributeError:
                return ''

    report_fields= authority_extract_fields()
    authority_list= [list(report_fields[:])] # Injecting header.

    categories= AuthorityCategory.objects.all().order_by('order', 'lft')

    for category in categories:

        # Ordering Authorities by slug, because it is a downcoded name.
        # If ordered by name, those records whose name start with
        # national symbols appear at the end of the list.
        category_authorities= AuthorityProfile.objects.filter(active=True,
            category=category).order_by('slug').values()
        if category_authorities:
            # Fill a line of Authority.
            for auth in category_authorities:
                line= []
                for field in report_fields:
                    if 'category' in field:
                        # Fill category.
                        line.append(_get_category_field(field, category))
                    elif field == 'created':
                        # Convert from date to readable string.
                        line.append(datetime.strftime(auth[field], '%d.%m.%Y'))
                    else:
                        if auth[field] is None:
                            # There should not be NoneFields.
                            line.append('')
                        else:
                            line.append(auth[field])
                authority_list.append(line)
        else:
            # Fill category data and leave the rest of fields blank.
            line= []
            for field in report_fields:
                if 'category' in field:
                    # Fill category.
                    line.append(_get_category_field(field, category))
                else:
                    line.append('')
            authority_list.append(line)

    f= open(settings.DOWNLOAD_ROOT + filename, 'w')
    writer= UnicodeWriter(f)
    for row in authority_list:
        writer.writerow(row)
    f.close()
    f= open(settings.DOWNLOAD_ROOT + filename).read()
    return f

def authority_extract_fields():
    return ('category_id', 'category_parent', 'category', 'name', 'created',
            'official', 'official_name', 'official_lastname', 'address_street',
            'address_num', 'address_line1', 'address_line2',
            'address_postalcode', 'address_city', 'tel_code', 'tel_number',
            'tel_internal', 'tel1_code', 'tel1_number', 'tel2_code',
            'tel2_number', 'fax_code', 'fax_number', 'web_site', 'web_site1',
            'description', 'notes')

def authority_events(authority):
    return {'request_to': 'Request to the Authority %s' % authority.name,
            'response_from': 'Response from the Authority %s' % authority.name}
