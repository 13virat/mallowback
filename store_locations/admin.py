from django.contrib import admin
from .models import StoreLocation, ServiceablePincode


class ServiceablePincodeInline(admin.TabularInline):
    model = ServiceablePincode
    extra = 1


@admin.register(StoreLocation)
class StoreLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'pincode', 'phone', 'is_active', 'pincode_count']
    list_filter = ['city', 'is_active']
    search_fields = ['name', 'city', 'pincode']
    list_editable = ['is_active']
    inlines = [ServiceablePincodeInline]

    def pincode_count(self, obj):
        return obj.pincodes.count()
    pincode_count.short_description = 'Pincodes Served'
