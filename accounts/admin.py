from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'phone', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'phone']
    fieldsets = UserAdmin.fieldsets + (
        ('Extended Profile', {
            'fields': ('phone', 'address', 'profile_picture', 'date_of_birth', 'fcm_token')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extended Profile', {
            'fields': ('phone', 'email')
        }),
    )
    readonly_fields = ['last_login', 'date_joined']
