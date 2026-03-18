from django.contrib import admin
from .models import OTPCode

@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'otp_type', 'is_used', 'created_at', 'expires_at')
    list_filter = ('otp_type', 'is_used')
    search_fields = ('phone', 'code')
    readonly_fields = ('created_at', 'expires_at')
    ordering = ('-created_at',)
