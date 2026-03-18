"""
Orders admin — full operational control, status management, bulk actions.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction
from .models import Order, OrderItem, Address, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'variant', 'quantity', 'price', 'subtotal', 'message_on_cake']
    can_delete = False

    def subtotal(self, obj):
        return f"₹{obj.subtotal()}"


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'changed_by', 'notes', 'changed_at']
    can_delete = False
    ordering = ['changed_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'status_badge', 'final_amount', 'payment_status_badge',
        'delivery_date', 'created_at'
    ]
    list_filter = ['status', 'delivery_date', 'created_at', 'store']
    search_fields = ['id', 'user__email', 'user__phone', 'address__pincode']
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    readonly_fields = [
        'total_amount', 'discount_amount', 'delivery_charge', 'final_amount',
        'created_at', 'updated_at', 'confirmed_at', 'preparing_at',
        'out_for_delivery_at', 'delivered_at', 'cancelled_at',
    ]
    date_hierarchy = 'created_at'
    actions = [
        'mark_confirmed', 'mark_preparing', 'mark_out_for_delivery', 'mark_delivered'
    ]

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'confirmed': '#3b82f6',
            'preparing': '#8b5cf6',
            'out_for_delivery': '#f97316',
            'delivered': '#10b981',
            'cancelled': '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def payment_status_badge(self, obj):
        try:
            ps = obj.payment.status
            color = '#10b981' if ps == 'success' else ('#f59e0b' if ps == 'pending' else '#ef4444')
            return format_html(
                '<span style="color:{};font-weight:600">{}</span>', color, ps.upper()
            )
        except Exception:
            return format_html('<span style="color:#6b7280">—</span>')
    payment_status_badge.short_description = 'Payment'

    def _bulk_transition(self, request, queryset, new_status):
        success, errors = 0, 0
        for order in queryset:
            try:
                with transaction.atomic():
                    order.transition_to(new_status, performed_by=request.user, notes='Bulk admin action')
                success += 1
            except ValueError:
                errors += 1
        msg = f"{success} order(s) transitioned to '{new_status}'."
        if errors:
            msg += f" {errors} skipped (invalid transitions)."
        self.message_user(request, msg)

    def mark_confirmed(self, request, queryset):
        self._bulk_transition(request, queryset, 'confirmed')
    mark_confirmed.short_description = "Mark selected orders as Confirmed"

    def mark_preparing(self, request, queryset):
        self._bulk_transition(request, queryset, 'preparing')
    mark_preparing.short_description = "Mark selected orders as Preparing"

    def mark_out_for_delivery(self, request, queryset):
        self._bulk_transition(request, queryset, 'out_for_delivery')
    mark_out_for_delivery.short_description = "Mark selected orders as Out for Delivery"

    def mark_delivered(self, request, queryset):
        self._bulk_transition(request, queryset, 'delivered')
    mark_delivered.short_description = "Mark selected orders as Delivered"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'city', 'pincode', 'is_default']
    search_fields = ['user__email', 'name', 'pincode', 'city']
    list_filter = ['city', 'is_default']


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'old_status', 'new_status', 'changed_by', 'changed_at']
    list_filter = ['new_status', 'changed_at']
    readonly_fields = ['order', 'old_status', 'new_status', 'changed_by', 'notes', 'changed_at']
    search_fields = ['order__id']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
