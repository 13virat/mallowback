from django.contrib import admin
from .models import Payment, PaymentWebhookLog


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'user', 'method', 'status', 'amount', 'created_at']
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['razorpay_order_id', 'razorpay_payment_id', 'user__email', 'order__id']
    readonly_fields = [
        'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature',
        'gateway_response', 'idempotency_key', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'


@admin.register(PaymentWebhookLog)
class PaymentWebhookLogAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'event_type', 'processed', 'received_at']
    list_filter = ['event_type', 'processed']
    readonly_fields = ['event_id', 'event_type', 'payload', 'processed', 'error', 'received_at']
    search_fields = ['event_id', 'event_type']
