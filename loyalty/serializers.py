from rest_framework import serializers
from .models import LoyaltyAccount, PointTransaction


class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTransaction
        fields = ['id', 'points', 'transaction_type', 'description', 'created_at']


class LoyaltyAccountSerializer(serializers.ModelSerializer):
    transactions = PointTransactionSerializer(many=True, read_only=True)
    rupee_value = serializers.SerializerMethodField()

    class Meta:
        model = LoyaltyAccount
        fields = ['points', 'lifetime_points', 'tier', 'rupee_value', 'transactions']

    def get_rupee_value(self, obj):
        return obj.points / 2  # 2 points = ₹1
