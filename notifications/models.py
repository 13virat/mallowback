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


class Campaign(models.Model):
    """
    Marketing campaigns — birthday, festivals, bulk promotions.
    Supports Email + WhatsApp + Push channels.
    Cost: Email=free, Push=free, WhatsApp=₹0.30-0.70/msg
    """
    CHANNEL_CHOICES = (
        ('email',    'Email only (Free)'),
        ('whatsapp', 'WhatsApp only (₹0.30-0.70/msg)'),
        ('both',     'Email + WhatsApp'),
        ('push',     'Push only (Free)'),
    )
    TYPE_CHOICES = (
        ('birthday',    'Birthday'),
        ('festival',    'Festival / Seasonal'),
        ('promotional', 'Promotional'),
        ('custom',      'Custom'),
    )
    STATUS_CHOICES = (
        ('draft',   'Draft'),
        ('sending', 'Sending'),
        ('sent',    'Sent'),
        ('failed',  'Failed'),
    )

    name          = models.CharField(max_length=200)
    campaign_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='promotional')
    channel       = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='email')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Content
    subject      = models.CharField(max_length=200, blank=True, help_text="Email subject line")
    email_body   = models.TextField(blank=True, help_text="Use {name}, {coupon_code}, {discount}, {valid_days}")
    whatsapp_msg = models.TextField(blank=True, help_text="Use {name}, {coupon_code}, {discount}, {valid_days}")
    push_title   = models.CharField(max_length=100, blank=True)
    push_body    = models.CharField(max_length=200, blank=True)

    # Coupon auto-generation per recipient
    include_coupon    = models.BooleanField(default=False)
    coupon_discount   = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    coupon_type       = models.CharField(max_length=20, default='percentage',
                                         choices=[('percentage', 'Percentage'), ('flat', 'Flat')])
    coupon_valid_days = models.PositiveIntegerField(default=7)
    coupon_prefix     = models.CharField(max_length=10, default='CAKE')

    # Stats (filled after send)
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count       = models.PositiveIntegerField(default=0)
    failed_count     = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='campaigns'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"