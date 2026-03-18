"""
Analytics models.
OrderAnalyticsEvent stores a lightweight record per placed order
for quick KPI queries without hitting the orders table repeatedly.
"""
from django.db import models
from django.conf import settings


class OrderAnalyticsEvent(models.Model):
    """Lightweight analytics record created when an order is placed."""
    order_id = models.IntegerField(db_index=True)
    user_id = models.IntegerField(db_index=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_id} — ₹{self.total}"
