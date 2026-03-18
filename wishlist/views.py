from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import WishlistItem
from .serializers import WishlistItemSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product')
    return Response(WishlistItemSerializer(items, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_wishlist(request, product_id):
    """Add if not present, remove if already present."""
    item = WishlistItem.objects.filter(user=request.user, product_id=product_id).first()
    if item:
        item.delete()
        return Response({'status': 'removed', 'product_id': product_id})
    WishlistItem.objects.create(user=request.user, product_id=product_id)
    return Response({'status': 'added', 'product_id': product_id}, status=status.HTTP_201_CREATED)
