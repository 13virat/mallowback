from rest_framework import serializers
from .models import Coupon


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'coupon_type', 'discount_value',
            'min_order_amount', 'max_discount_amount', 'description',
            'valid_from', 'valid_until', 'is_active',
            'max_uses', 'used_count', 'max_uses_per_user',
        ]


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField()
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
