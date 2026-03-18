from django.db import models


class DeliverySlot(models.Model):
    DAYS_OF_WEEK = (
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    )

    label = models.CharField(max_length=100)           # e.g. "Morning (10am–1pm)"
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_orders = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    available_days = models.JSONField(default=list)    # e.g. [0,1,2,3,4,5,6]
    extra_charge = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return self.label

    def booked_count(self, date):
        return self.slot_bookings.filter(delivery_date=date).count()

    def is_available_on(self, date):
        return (
            self.is_active
            and date.weekday() in self.available_days
            and self.booked_count(date) < self.max_orders
        )


class SlotBooking(models.Model):
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='slot_booking')
    slot = models.ForeignKey(DeliverySlot, on_delete=models.CASCADE, related_name='slot_bookings')
    delivery_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.order_id} — {self.slot.label} on {self.delivery_date}"
