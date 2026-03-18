from rest_framework import serializers
from .models import Order, OrderItem, Address, OrderStatusHistory


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'name', 'phone', 'address', 'city', 'pincode', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True, use_url=True)
    variant_weight = serializers.CharField(source='variant.weight', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image',
                  'variant', 'variant_weight', 'quantity', 'price',
                  'message_on_cake', 'subtotal']

    def get_subtotal(self, obj):
        return obj.subtotal()


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory
        fields = ['old_status', 'new_status', 'changed_by_name', 'notes', 'changed_at']

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.username
        return 'System'


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    history = OrderStatusHistorySerializer(many=True, read_only=True)
    address_detail = AddressSerializer(source='address', read_only=True)
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total_amount', 'discount_amount',
            'delivery_charge', 'final_amount', 'coupon_code',
            'delivery_date', 'notes', 'address', 'address_detail',
            'items', 'history', 'payment_status',
            'confirmed_at', 'preparing_at', 'out_for_delivery_at',
            'delivered_at', 'cancelled_at', 'created_at', 'updated_at',
        ]

    def get_payment_status(self, obj):
        try:
            return obj.payment.status
        except Exception:
            return None


class CreateOrderSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    delivery_date = serializers.DateField()
    coupon_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    slot_id = serializers.IntegerField(required=False)
