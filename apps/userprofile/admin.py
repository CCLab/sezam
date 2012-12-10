from django.contrib import admin

from apps.vocabulary.models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display= ('user', 'created',)
    
admin.site.register(UserProfile, UserProfileAdmin)
