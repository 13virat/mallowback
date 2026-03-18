from django.contrib import admin
from .models import LoyaltyAccount, PointTransaction


class PointTransactionInline(admin.TabularInline):
    model = PointTransaction
    extra = 0
    readonly_fields = ['points', 'transaction_type', 'description', 'created_at']
    can_delete = False
    ordering = ['-created_at']
    max_num = 20


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'points', 'lifetime_points', 'tier', 'updated_at']
    list_filter = ['tier']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['lifetime_points', 'tier', 'updated_at']
    inlines = [PointTransactionInline]


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'points', 'transaction_type', 'description', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    readonly_fields = ['account', 'points', 'transaction_type', 'description', 'created_at']
