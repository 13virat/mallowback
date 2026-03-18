from rest_framework import serializers
from .models import StoreLocation, ServiceablePincode


class ServiceablePincodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceablePincode
        fields = ['pincode', 'delivery_charge', 'min_order_for_free_delivery', 'estimated_delivery_time']


class StoreLocationSerializer(serializers.ModelSerializer):
    pincodes = ServiceablePincodeSerializer(many=True, read_only=True)
    distance_km = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = StoreLocation
        fields = [
            'id', 'name', 'address', 'city', 'pincode', 'phone', 'email',
            'latitude', 'longitude', 'opening_time', 'closing_time',
            'is_open_sunday', 'is_active', 'image', 'pincodes', 'distance_km',
        ]
