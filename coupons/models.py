from django.conf import settings
from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('flat', 'Flat Amount'),
        ('free_delivery', 'Free Delivery'),
    )

    code = models.CharField(max_length=30, unique=True)
    coupon_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses = models.PositiveIntegerField(default=100)
    used_count = models.PositiveIntegerField(default=0)
    max_uses_per_user = models.PositiveIntegerField(default=1)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    applicable_categories = models.ManyToManyField('products.Category', blank=True)

    class Meta:
        ordering = ['-valid_from']

    def __str__(self):
        return self.code

    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_until
            and self.used_count < self.max_uses
        )

    def calculate_discount(self, order_amount):
        if order_amount < self.min_order_amount:
            return 0
        if self.coupon_type == 'flat':
            return min(self.discount_value, order_amount)
        if self.coupon_type == 'percentage':
            discount = order_amount * self.discount_value / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        if self.coupon_type == 'free_delivery':
            return 0  # handled at order level
        return 0


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} used {self.coupon.code}"
