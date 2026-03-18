"""
Products admin — full inventory management, bulk actions, low-stock highlighting.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Category, Product, ProductVariant, StockAuditLog
from .services import adjust_stock_manually


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['weight', 'price', 'stock', 'low_stock_threshold', 'track_inventory', 'is_available']
    readonly_fields = []


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'is_eggless', 'is_available',
        'is_featured', 'total_stock_display', 'created_at'
    ]
    list_filter = ['category', 'is_eggless', 'is_available', 'is_featured']
    search_fields = ['name', 'description']
    inlines = [ProductVariantInline]
    list_editable = ['is_available', 'is_featured']
    actions = ['mark_available', 'mark_unavailable']
    date_hierarchy = 'created_at'

    def total_stock_display(self, obj):
        total = obj.variants.aggregate(t=Sum('stock'))['t'] or 0
        color = 'red' if total == 0 else ('orange' if total <= 10 else 'green')
        return format_html('<span style="color:{}">{} units</span>', color, total)
    total_stock_display.short_description = 'Total Stock'

    def mark_available(self, request, queryset):
        queryset.update(is_available=True)
    mark_available.short_description = 'Mark selected products as available'

    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False)
    mark_unavailable.short_description = 'Mark selected products as unavailable'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'weight', 'price', 'stock', 'available_stock',
        'stock_status', 'track_inventory', 'is_available'
    ]
    list_filter = ['track_inventory', 'is_available', 'product__category']
    search_fields = ['product__name', 'weight']
    list_editable = ['stock', 'is_available']
    actions = ['restock_50', 'restock_100']

    def stock_status(self, obj):
        if not obj.track_inventory:
            return format_html('<span style="color:gray">Untracked</span>')
        if obj.stock == 0:
            return format_html('<span style="color:red;font-weight:bold">OUT OF STOCK</span>')
        if obj.is_low_stock:
            return format_html('<span style="color:orange;font-weight:bold">LOW ({} left)</span>', obj.stock)
        return format_html('<span style="color:green">OK</span>')
    stock_status.short_description = 'Status'

    def available_stock(self, obj):
        return obj.available_stock
    available_stock.short_description = 'Available'

    def restock_50(self, request, queryset):
        for variant in queryset:
            adjust_stock_manually(variant.id, 50, request.user, 'Admin bulk restock +50')
        self.message_user(request, f"Restocked {queryset.count()} variants by 50 units each.")
    restock_50.short_description = 'Restock selected variants by +50'

    def restock_100(self, request, queryset):
        for variant in queryset:
            adjust_stock_manually(variant.id, 100, request.user, 'Admin bulk restock +100')
        self.message_user(request, f"Restocked {queryset.count()} variants by 100 units each.")
    restock_100.short_description = 'Restock selected variants by +100'


@admin.register(StockAuditLog)
class StockAuditLogAdmin(admin.ModelAdmin):
    list_display = ['variant', 'action', 'quantity_change', 'stock_before', 'stock_after', 'order', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['variant__product__name', 'order__id']
    readonly_fields = ['variant', 'action', 'quantity_change', 'stock_before', 'stock_after',
                       'order', 'performed_by', 'notes', 'created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
