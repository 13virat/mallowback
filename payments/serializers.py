from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    is_custom_advance = serializers.BooleanField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'method', 'status', 'amount',
            'advance_amount', 'remaining_amount', 'remaining_paid',
            'razorpay_order_id', 'razorpay_payment_id',
            'is_custom_advance', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class PaymentVerifySerializer(serializers.Serializer):
    razorpay_order_id  = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature  = serializers.CharField(max_length=255)