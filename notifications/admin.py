from django.contrib import admin
from .models import Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['event', 'is_active', 'has_email', 'has_sms', 'has_whatsapp', 'has_push']
    list_editable = ['is_active']
    list_filter = ['is_active']

    def has_email(self, obj): return bool(obj.email_body)
    def has_sms(self, obj): return bool(obj.sms_body)
    def has_whatsapp(self, obj): return bool(obj.whatsapp_body)
    def has_push(self, obj): return bool(obj.push_title)
    has_email.boolean = True
    has_sms.boolean = True
    has_whatsapp.boolean = True
    has_push.boolean = True


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'channel', 'subject', 'status', 'created_at', 'sent_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['user__email', 'subject', 'message']
    readonly_fields = ['user', 'channel', 'subject', 'message', 'status', 'error', 'created_at', 'sent_at']
    date_hierarchy = 'created_at'
