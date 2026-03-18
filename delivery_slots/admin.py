from django.contrib import admin
from django.utils.html import format_html
from datetime import date
from .models import DeliverySlot, SlotBooking


@admin.register(DeliverySlot)
class DeliverySlotAdmin(admin.ModelAdmin):
    list_display = [
        'label', 'start_time', 'end_time', 'max_orders',
        'today_bookings', 'extra_charge', 'is_active'
    ]
    list_editable = ['is_active', 'max_orders']
    search_fields = ['label']
    list_filter = ['is_active']

    def today_bookings(self, obj):
        count = obj.booked_count(date.today())
        pct = count / obj.max_orders if obj.max_orders else 0
        color = 'red' if pct >= 1 else ('orange' if pct >= 0.7 else 'green')
        return format_html(
            '<span style="color:{};font-weight:600">{}/{}</span>',
            color, count, obj.max_orders
        )
    today_bookings.short_description = "Today Booked"


@admin.register(SlotBooking)
class SlotBookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'slot', 'delivery_date', 'created_at']
    list_filter = ['delivery_date', 'slot']
    search_fields = ['order__id', 'order__user__email']
    date_hierarchy = 'delivery_date'
    readonly_fields = ['order', 'slot', 'delivery_date', 'created_at']
