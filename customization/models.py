from django.conf import settings
from django.db import models


class CustomCakeRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('quoted', 'Quoted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='custom_cake_requests')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    cake_type = models.CharField(max_length=100)
    flavour = models.CharField(max_length=100)
    weight = models.CharField(max_length=50)
    reference_image = models.ImageField(upload_to='custom_cakes/', blank=True, null=True)
    message = models.CharField(max_length=500)
    delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)     # bakery staff notes/quote
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Custom Cake — {self.name} ({self.delivery_date})"
