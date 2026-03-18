from rest_framework import serializers
from .models import DeliverySlot, SlotBooking


class DeliverySlotSerializer(serializers.ModelSerializer):
    available_count = serializers.SerializerMethodField()

    class Meta:
        model = DeliverySlot
        fields = ['id', 'label', 'start_time', 'end_time', 'max_orders',
                  'extra_charge', 'available_days', 'available_count']

    def get_available_count(self, obj):
        date_str = self.context.get('date')
        if date_str:
            from datetime import date as date_cls
            try:
                d = date_cls.fromisoformat(date_str)
                return obj.max_orders - obj.booked_count(d)
            except ValueError:
                pass
        return obj.max_orders


class SlotBookingSerializer(serializers.ModelSerializer):
    slot_label = serializers.CharField(source='slot.label', read_only=True)

    class Meta:
        model = SlotBooking
        fields = ['id', 'order', 'slot', 'slot_label', 'delivery_date']
