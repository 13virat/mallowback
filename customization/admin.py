from django.contrib import admin
from .models import CustomCakeRequest


@admin.register(CustomCakeRequest)
class CustomCakeRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'cake_type', 'delivery_date', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'phone', 'email']
