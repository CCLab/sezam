from django.contrib import admin
from apps.backend.models import EventNotification

class EventNotificationAdmin(admin.ModelAdmin):
    list_display= ('item', 'action', 'awaiting', 'receiver', 'receiver_email',)
    search_fields= ('item', 'receiver', 'receiver_email',)
    list_filter= ('action', 'awaiting',)
    fields= ('item', 'action', 'awaiting', 'receiver', 'receiver_email',)
    ordering= ('-created',)

admin.site.register(EventNotification, EventNotificationAdmin)
