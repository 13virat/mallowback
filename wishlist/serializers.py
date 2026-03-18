from rest_framework import serializers
from .models import WishlistItem
from products.serializers import ProductSerializer


class WishlistItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = WishlistItem
        fields = ['id', 'product', 'product_detail', 'added_at']
