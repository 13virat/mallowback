import random, string
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


class OTPCode(models.Model):
    OTP_TYPE_CHOICES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
    ]

    phone = models.CharField(max_length=15)
    code = models.CharField(max_length=6, default=generate_otp)
    otp_type = models.CharField(max_length=20, choices=OTP_TYPE_CHOICES, default='registration')
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.phone} — {self.code} ({self.otp_type})"

    class Meta:
        ordering = ['-created_at']
