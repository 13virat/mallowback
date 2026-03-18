"""
Order models — full lifecycle with history tracking and timestamp logging.
"""
from django.conf import settings
from django.db import models, transaction
from products.models import Product, ProductVariant


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}, {self.city}"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Use atomic + select_for_update to prevent race conditions where two
            # concurrent requests both set a different address as default,
            # potentially leaving no default address.
            with transaction.atomic():
                Address.objects.select_for_update().filter(
                    user=self.user, is_default=True
                ).update(is_default=False)
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    # Valid forward transitions — prevents illegal state jumps
    VALID_TRANSITIONS = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['out_for_delivery', 'cancelled'],
        'out_for_delivery': ['delivered'],
        'delivered': [],
        'cancelled': [],
    }

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    store = models.ForeignKey(
        'store_locations.StoreLocation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    delivery_date = models.DateField()
    notes = models.TextField(blank=True)

    # ── Timestamp logging per status ──────────────────────────────────────────
    confirmed_at = models.DateTimeField(null=True, blank=True)
    preparing_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} — {self.user} — {self.status}"

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status: str, performed_by=None, notes: str = ''):
        """
        Move order to new_status, validate the transition, stamp the timestamp,
        and record the history entry.
        Raises ValueError on invalid transition.
        """
        from django.utils import timezone

        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition order #{self.id} from '{self.status}' to '{new_status}'."
            )

        old_status = self.status
        self.status = new_status

        # Stamp the relevant timestamp
        ts_map = {
            'confirmed': 'confirmed_at',
            'preparing': 'preparing_at',
            'out_for_delivery': 'out_for_delivery_at',
            'delivered': 'delivered_at',
            'cancelled': 'cancelled_at',
        }
        if new_status in ts_map:
            setattr(self, ts_map[new_status], timezone.now())

        self.save()

        OrderStatusHistory.objects.create(
            order=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=performed_by,
            notes=notes,
        )

        return self


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    message_on_cake = models.CharField(max_length=255, blank=True)

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


class OrderStatusHistory(models.Model):
    """Immutable audit trail for every order status transition."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['changed_at']
        verbose_name_plural = 'order status history'

    def __str__(self):
        return f"Order #{self.order_id}: {self.old_status} → {self.new_status}"
