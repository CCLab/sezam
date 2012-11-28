from django.contrib import admin
from apps.pia_request.models import PIARequest

class PIARequestAdmin(admin.ModelAdmin):
    list_display= ('created', 'user', 'email_from', 'authority', 'email_to',
                   'subject', 'status',)

    search_fields= ('email_from', 'email_to', 'subject', 'body',)

    list_filter= ('authority',)

    fields= (('request_id', 'is_response',), ('user', 'email_from',), ('authority', 'email_to',),
        'subject', 'body', 'status',)

    ordering= ('-created',)

admin.site.register(PIARequest, PIARequestAdmin)
