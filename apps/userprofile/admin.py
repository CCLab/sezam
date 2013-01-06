from django.contrib import admin

from apps.vocabulary.models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display= ('user', 'created', 'trusted', 'address_city', 'company',)
    search_fields= ('user',)
    ordering= ('user',)

    list_filter= ('created', 'trusted', 'address_city',)

    fields= ('trusted',)
    
admin.site.register(UserProfile, UserProfileAdmin)
