from rest_framework import serializers
from .models import Order, OrderItem, Address, OrderStatusHistory


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'name', 'phone', 'address', 'city', 'pincode', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']


class OrderItemSerializer(serializers.ModelSerializer):
    product_name  = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    variant_weight = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image',
                  'variant', 'variant_weight', 'quantity', 'price',
                  'message_on_cake', 'custom_item_name', 'subtotal']

    def get_product_name(self, obj):
        if obj.custom_item_name:
            return obj.custom_item_name
        return obj.product.name if obj.product else '—'

    def get_product_image(self, obj):
        if obj.product and obj.product.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.image.url)
            return obj.product.image.url
        return None

    def get_variant_weight(self, obj):
        return obj.variant.weight if obj.variant else None

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
    items          = OrderItemSerializer(many=True, read_only=True)
    history        = OrderStatusHistorySerializer(many=True, read_only=True)
    address_detail = AddressSerializer(source='address', read_only=True)
    payment_status = serializers.SerializerMethodField()
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    # Custom cake request summary (only populated for custom orders)
    custom_cake_summary = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'order_type', 'order_type_display',
            'total_amount', 'discount_amount', 'delivery_charge',
            'final_amount', 'coupon_code', 'delivery_date', 'notes',
            'address', 'address_detail', 'items', 'history',
            'payment_status', 'custom_cake_request', 'custom_cake_summary',
            'confirmed_at', 'preparing_at', 'out_for_delivery_at',
            'delivered_at', 'cancelled_at', 'created_at', 'updated_at',
        ]

    def get_payment_status(self, obj):
        try:
            return obj.payment.status
        except Exception:
            return None

    def get_custom_cake_summary(self, obj):
        if obj.order_type != 'custom' or not obj.custom_cake_request:
            return None
        req = obj.custom_cake_request
        return {
            'id': req.id,
            'name': req.name,
            'phone': req.phone,
            'cake_type': req.cake_type,
            'flavour': req.flavour,
            'weight': req.weight,
            'message': req.message,
            'admin_notes': req.admin_notes,
            'reference_image': (
                self.context['request'].build_absolute_uri(req.reference_image.url)
                if req.reference_image and self.context.get('request') else None
            ),
        }


class CreateOrderSerializer(serializers.Serializer):
    address_id    = serializers.IntegerField()
    delivery_date = serializers.DateField()
    coupon_code   = serializers.CharField(max_length=30, required=False, allow_blank=True)
    notes         = serializers.CharField(max_length=500, required=False, allow_blank=True)
    slot_id       = serializers.IntegerField(required=False)