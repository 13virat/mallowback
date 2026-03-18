from django.contrib import admin
from .models import OrderAnalyticsEvent


@admin.register(OrderAnalyticsEvent)
class OrderAnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user_id', 'total', 'discount', 'coupon', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order_id', 'user_id', 'coupon')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
