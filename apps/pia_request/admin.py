from django.contrib import admin
from apps.pia_request.models import PIAMessage, PIARequest, PIAThread


class PIARequestAdmin(admin.ModelAdmin):
    list_display= ('user', 'authority', 'summary', 'status',
        'latest_thread_post')
    search_fields= ('summary',)
    list_filter= ('authority', 'user', 'created',)
    fields= ('status', ('user', 'authority',), 'summary',)
    ordering= ('-created',)


class PIAThreadAdmin(admin.ModelAdmin):
    list_display= ('id', 'request', 'created', 'is_response',
        'email_from', 'email_to', 'subject',)
    search_fields= ('email_from', 'email_to', 'subject', 'body',)
    list_filter= ('email_to', 'email_from',)
    fields= ('request', 'is_response', 'email_from', 'email_to',
        'subject', 'body',)
    ordering= ('-created',)


class PIAMessageAdmin(admin.ModelAdmin):
    list_display= ('created', 'email_to', 'email_from', 'subject',)
    search_fields= ('email_from', 'email_to', 'subject', 'body',)
    list_filter= ('email_to', 'email_from',)
    fields= ('email_from', 'email_to', 'subject', 'body',)
    ordering= ('-created',)


admin.site.register(PIARequest, PIARequestAdmin)

admin.site.register(PIAThread, PIAThreadAdmin)

admin.site.register(PIAMessage, PIAMessageAdmin)
