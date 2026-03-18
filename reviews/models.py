from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from products.models import Product


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user')   # one review per user per product
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.product} ({self.rating}★)"
