from django.conf import settings
from django.db import models


class Notification(models.Model):
    CHANNEL_CHOICES = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('push', 'Push'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.channel.upper()} to {self.user} — {self.status}"


class NotificationTemplate(models.Model):
    EVENT_CHOICES = (
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_preparing', 'Order Being Prepared'),
        ('order_dispatched', 'Order Dispatched'),
        ('order_out_for_delivery', 'Order Out for Delivery'),
        ('order_delivered', 'Order Delivered'),
        ('order_cancelled', 'Order Cancelled'),
        ('payment_success', 'Payment Success'),
        ('custom_cake_received', 'Custom Cake Request Received'),
        ('custom_cake_quoted', 'Custom Cake Quoted'),
        ('low_stock', 'Low Stock Alert'),
        ('promotional', 'Promotional'),
    )

    event = models.CharField(max_length=50, choices=EVENT_CHOICES, unique=True)
    email_subject = models.CharField(max_length=200, blank=True)
    email_body = models.TextField(blank=True, help_text="Use {variable} for substitution.")
    sms_body = models.CharField(max_length=160, blank=True)
    whatsapp_body = models.TextField(blank=True)
    push_title = models.CharField(max_length=100, blank=True)
    push_body = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.get_event_display()
