from rest_framework import serializers
from .models import CustomCakeRequest


class CustomCakeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CustomCakeRequest
        fields = ['id', 'name', 'phone', 'email', 'cake_type', 'flavour',
                  'weight', 'reference_image', 'message', 'delivery_date',
                  'status', 'status_display', 'admin_notes', 'created_at']
        read_only_fields = ['status', 'admin_notes', 'created_at']
