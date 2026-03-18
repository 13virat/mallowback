from django.contrib import admin
from django.utils.html import format_html
from .models import Coupon, CouponUsage


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'coupon_type', 'discount_value', 'min_order_amount',
        'usage_display', 'validity_badge', 'is_active'
    ]
    list_filter = ['coupon_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'description']
    list_editable = ['is_active']
    filter_horizontal = ['applicable_categories']
    readonly_fields = ['used_count']
    actions = ['activate_coupons', 'deactivate_coupons']
    fieldsets = (
        ('Coupon Info', {
            'fields': ('code', 'description', 'coupon_type', 'discount_value',
                       'max_discount_amount', 'min_order_amount')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'used_count', 'max_uses_per_user')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until', 'is_active')
        }),
        ('Restrictions', {
            'fields': ('applicable_categories',)
        }),
    )

    def usage_display(self, obj):
        pct = (obj.used_count / obj.max_uses * 100) if obj.max_uses else 0
        color = 'red' if pct > 80 else ('orange' if pct > 50 else 'green')
        return format_html(
            '<span style="color:{}">{}/{}</span>', color, obj.used_count, obj.max_uses
        )
    usage_display.short_description = 'Used/Max'

    def validity_badge(self, obj):
        valid = obj.is_valid()
        color = 'green' if valid else 'red'
        label = 'VALID' if valid else 'EXPIRED/INACTIVE'
        return format_html('<span style="color:{};font-weight:600">{}</span>', color, label)
    validity_badge.short_description = 'Status'

    def activate_coupons(self, request, queryset):
        queryset.update(is_active=True)
    activate_coupons.short_description = 'Activate selected coupons'

    def deactivate_coupons(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_coupons.short_description = 'Deactivate selected coupons'


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'user', 'order', 'discount_applied', 'used_at']
    list_filter = ['coupon', 'used_at']
    search_fields = ['user__email', 'coupon__code']
    readonly_fields = ['coupon', 'user', 'order', 'discount_applied', 'used_at']
