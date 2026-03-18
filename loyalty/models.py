from django.conf import settings
from django.db import models


class LoyaltyAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loyalty')
    points = models.PositiveIntegerField(default=0)
    lifetime_points = models.PositiveIntegerField(default=0)
    tier = models.CharField(max_length=20, default='Bronze')
    updated_at = models.DateTimeField(auto_now=True)

    TIERS = {
        'Bronze': 0,
        'Silver': 500,
        'Gold': 1500,
        'Platinum': 5000,
    }

    def __str__(self):
        return f"{self.user} — {self.points} pts ({self.tier})"

    def recalculate_tier(self):
        for tier, threshold in reversed(list(self.TIERS.items())):
            if self.lifetime_points >= threshold:
                self.tier = tier
                break

    def add_points(self, points, description=''):
        self.points += points
        self.lifetime_points += points
        self.recalculate_tier()
        self.save()
        PointTransaction.objects.create(
            account=self,
            points=points,
            transaction_type='earned',
            description=description,
        )

    def redeem_points(self, points, description=''):
        if self.points < points:
            raise ValueError('Insufficient points.')
        self.points -= points
        self.save()
        PointTransaction.objects.create(
            account=self,
            points=-points,
            transaction_type='redeemed',
            description=description,
        )
        return points / 2  # 2 points = ₹1 discount


class PointTransaction(models.Model):
    TYPE_CHOICES = (
        ('earned', 'Earned'),
        ('redeemed', 'Redeemed'),
        ('expired', 'Expired'),
        ('bonus', 'Bonus'),
    )

    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE, related_name='transactions')
    points = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account.user} — {self.points} pts ({self.transaction_type})"
