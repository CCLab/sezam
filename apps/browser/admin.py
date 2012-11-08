from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from apps.vocabulary.models import TerritoryType, Territory, AuthorityCategory, AuthorityProfile

class TerritoryTypeAdmin(admin.ModelAdmin):
    pass

admin.site.register(TerritoryType, TerritoryTypeAdmin)

admin.site.register(AuthorityCategory, MPTTModelAdmin)

admin.site.register(AuthorityProfile)
