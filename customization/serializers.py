from rest_framework import serializers
from .models import CustomCakeRequest


class CustomCakeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # use_url=True builds a full absolute URL using the request context
    reference_image = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = CustomCakeRequest
        fields = ['id', 'name', 'phone', 'email', 'cake_type', 'flavour',
                  'weight', 'reference_image', 'message', 'delivery_date',
                  'status', 'status_display', 'admin_notes', 'created_at']
        read_only_fields = ['status', 'admin_notes', 'created_at']