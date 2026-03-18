"""
Payment models — Razorpay + COD, idempotency, audit trail.
"""
from django.conf import settings
from django.db import models
from orders.models import Order


class Payment(models.Model):
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    METHOD_CHOICES = (
        ('razorpay', 'Razorpay'),
        ('cod', 'Cash on Delivery'),
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='razorpay')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)

    # Idempotency — prevent duplicate payment processing
    idempotency_key = models.CharField(max_length=100, blank=True, db_index=True)

    # Metadata
    gateway_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} — Order #{self.order_id} — {self.status}"

    @property
    def is_paid(self):
        return self.status == 'success'


class PaymentWebhookLog(models.Model):
    """Raw webhook events from Razorpay for auditing."""
    event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.event_type} — {self.event_id}"
