"""
User model — extended with FCM push token and profile fields.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    # ── FCM Push Notification Token ──────────────────────────────────────────
    fcm_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="Firebase Cloud Messaging device token for push notifications."
    )

    # ── Profile extras ───────────────────────────────────────────────────────
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return self.email or self.username
