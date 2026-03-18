from django.db import models


class StoreLocation(models.Model):
    name = models.CharField(max_length=100)         # e.g. "Cakemallow – Hazratganj"
    address = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_open_sunday = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='stores/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['city', 'name']

    def __str__(self):
        return f"{self.name} ({self.city})"


class ServiceablePincode(models.Model):
    store = models.ForeignKey(StoreLocation, on_delete=models.CASCADE, related_name='pincodes')
    pincode = models.CharField(max_length=10)
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    min_order_for_free_delivery = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_delivery_time = models.CharField(max_length=50, default='2-4 hours')

    class Meta:
        unique_together = ('store', 'pincode')

    def __str__(self):
        return f"{self.pincode} → {self.store.name}"
