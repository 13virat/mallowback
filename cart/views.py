"""
Cart views — with stock validation on add/update to prevent adding unavailable items.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_cart(request):
    cart = get_or_create_cart(request.user)
    return Response(CartSerializer(cart, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    """
    POST /api/cart/add/
    { variant, product, quantity, message_on_cake }
    Validates stock availability before adding.
    """
    cart = get_or_create_cart(request.user)
    variant_id = request.data.get('variant')
    quantity   = int(request.data.get('quantity', 1))
    message    = request.data.get('message_on_cake', '')

    if not variant_id:
        return Response({'error': 'variant is required.'}, status=status.HTTP_400_BAD_REQUEST)

    if quantity < 1:
        return Response({'error': 'quantity must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)

    # ── Stock validation ──────────────────────────────────────────────────────
    from products.models import ProductVariant
    try:
        variant = ProductVariant.objects.select_related('product').get(id=variant_id)
    except ProductVariant.DoesNotExist:
        return Response({'error': 'Product variant not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not variant.is_available or not variant.product.is_available:
        return Response(
            {'error': f"'{variant.product.name} ({variant.weight})' is currently unavailable."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if already in cart — total requested quantity matters
    existing_qty = 0
    try:
        existing_item = CartItem.objects.get(cart=cart, variant=variant)
        existing_qty = existing_item.quantity
    except CartItem.DoesNotExist:
        pass

    if variant.track_inventory:
        total_needed = existing_qty + quantity
        if variant.available_stock < total_needed:
            return Response(
                {
                    'error': f"Only {variant.available_stock} unit(s) available for "
                             f"'{variant.product.name} ({variant.weight})'. "
                             f"You already have {existing_qty} in cart."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    # Add or increment
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant_id=variant_id,
        defaults={
            'product_id': variant.product_id,
            'quantity': quantity,
            'message_on_cake': message,
        }
    )
    if not created:
        item.quantity += quantity
        item.save()

    return Response(
        CartSerializer(cart, context={'request': request}).data,
        status=status.HTTP_200_OK
    )


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def cart_item_detail(request, item_id):
    try:
        item = CartItem.objects.select_related('variant__product').get(
            id=item_id, cart__user=request.user
        )
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH — update quantity
    quantity = request.data.get('quantity')
    if quantity is not None:
        quantity = int(quantity)
        if quantity <= 0:
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # Stock check on update
        variant = item.variant
        if variant.track_inventory and variant.available_stock < quantity:
            return Response(
                {
                    'error': f"Only {variant.available_stock} unit(s) available for "
                             f"'{variant.product.name} ({variant.weight})'."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        item.quantity = quantity
        item.save()

    return Response(CartItemSerializer(item, context={'request': request}).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_cart(request):
    cart = get_or_create_cart(request.user)
    cart.items.all().delete()
    return Response({'message': 'Cart cleared.'}, status=status.HTTP_200_OK)
