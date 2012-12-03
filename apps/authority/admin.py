from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from apps.vocabulary.models import TerritoryType, Territory, AuthorityCategory, AuthorityProfile

class TerritoryTypeAdmin(admin.ModelAdmin):
    list_display= ('name', 'display_name',)
    search_fields= ('name', 'display_name',)
    ordering= ('name',)


class AuthorityCategoryAdmin(MPTTModelAdmin):
    list_display= ('name', 'slug',)
    fields= ('name', 'parent', 'order',)


class AuthorityProfileAdmin(admin.ModelAdmin):
    list_display= ('name', 'created', 'address_city', 'category', 'tel_code',
        'tel_number', 'tel_internal', 'email', 'official', 'official_name',
        'official_lastname',)

    search_fields= ('description', 'notes', 'address_street',
        'address_postalcode', 'address_city', 'tel_number', 'tel1_number',
        'tel2_number', 'fax_number', 'email', 'email_secretary', 'email_info',
        'web_site', 'web_site1', 'official', 'official_name',
        'official_lastname',)

    list_filter= ('created', 'category',)

    fields= (('name', 'category', 'parent',),
        ('official', 'official_name', 'official_lastname',),
        'order', 'description',
        ('address_street', 'address_num',), ('address_line1', 'address_line2',),
        ('address_postalcode', 'address_city',),
        ('tel_code', 'tel_number', 'tel_internal',),
        ('tel1_code', 'tel1_number',), ('tel2_code', 'tel2_number',),
        ('fax_code', 'fax_number',), ('email', 'email_secretary', 'email_info',),
        ('web_site', 'web_site1'), 'notes',)

admin.site.register(TerritoryType, TerritoryTypeAdmin)

admin.site.register(AuthorityCategory, AuthorityCategoryAdmin)

admin.site.register(AuthorityProfile, AuthorityProfileAdmin)
