"""
Order views — create, list, cancel, with stock validation and full workflow.

LOYALTY POINT RULES (summary):
- Online payment: awarded in payments/views.py after verify succeeds
- COD: awarded HERE when admin marks status → 'delivered'
"""
import logging
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from .models import Order, OrderItem, Address
from .serializers import OrderSerializer, AddressSerializer, CreateOrderSerializer
from cart.models import Cart

logger = logging.getLogger('orders')


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def address_list(request):
    if request.method == 'GET':
        addresses = Address.objects.filter(user=request.user)
        return Response(AddressSerializer(addresses, many=True).data)

    serializer = AddressSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def address_detail(request, pk):
    try:
        address = Address.objects.get(id=pk, user=request.user)
    except Address.DoesNotExist:
        return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(AddressSerializer(address).data)

    if request.method == 'PUT':
        serializer = AddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    address.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    POST /api/orders/create/
    Creates an order from the user's cart.
    """
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        address = Address.objects.get(
            id=serializer.validated_data['address_id'],
            user=request.user
        )
    except Address.DoesNotExist:
        return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        cart = Cart.objects.prefetch_related('items__variant__product').get(user=request.user)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

    cart_items = cart.items.all()
    if not cart_items.exists():
        return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

    from products.services import check_cart_stock
    stock_errors = check_cart_stock(cart)
    if stock_errors:
        return Response({'error': 'Stock issues', 'details': stock_errors}, status=status.HTTP_400_BAD_REQUEST)

    total          = sum(item.variant.price * item.quantity for item in cart_items)
    discount       = 0
    coupon_code    = serializer.validated_data.get('coupon_code', '')
    applied_coupon = None

    if coupon_code:
        try:
            from coupons.models import Coupon, CouponUsage
            coupon = Coupon.objects.get(code=coupon_code.upper())
            if coupon.is_valid():
                user_uses = CouponUsage.objects.filter(coupon=coupon, user=request.user).count()
                if user_uses < coupon.max_uses_per_user:
                    discount       = coupon.calculate_discount(total)
                    applied_coupon = coupon
        except Coupon.DoesNotExist:
            return Response({'error': f"Coupon '{coupon_code}' not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.warning(f"Coupon error: {e}")

    # Delivery charge from pincode settings
    delivery_charge = 0
    nearest_store   = None
    try:
        from store_locations.models import ServiceablePincode
        sp = ServiceablePincode.objects.select_related('store').filter(
            pincode=address.pincode, store__is_active=True
        ).first()
        if sp:
            delivery_charge = 0 if total >= sp.min_order_for_free_delivery else sp.delivery_charge
            nearest_store   = sp.store
        else:
            return Response(
                {'error': f"Delivery not available to pincode {address.pincode}."},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.warning(f"Pincode check failed: {e}")

    final_amount = total - discount + delivery_charge

    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            address=address,
            store=nearest_store,
            total_amount=total,
            discount_amount=discount,
            delivery_charge=delivery_charge,
            final_amount=final_amount,
            coupon_code=coupon_code.upper() if coupon_code else '',
            delivery_date=serializer.validated_data['delivery_date'],
            notes=serializer.validated_data.get('notes', ''),
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                quantity=item.quantity,
                price=item.variant.price,
                message_on_cake=item.message_on_cake,
            )

        if applied_coupon and discount > 0:
            from coupons.models import CouponUsage
            CouponUsage.objects.create(
                coupon=applied_coupon,
                user=request.user,
                order=order,
                discount_applied=discount,
            )
            applied_coupon.used_count += 1
            applied_coupon.save()

        cart.items.all().delete()

    try:
        from orders.tasks import send_order_confirmation, log_order_analytics
        send_order_confirmation.delay(order.id, request.user.id)
        log_order_analytics.delay(order.id)
    except Exception as e:
        logger.warning(f"Task dispatch failed (non-critical): {e}")

    logger.info(f"Order #{order.id} created for user #{request.user.id}")
    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items__product', 'items__variant', 'history'
    )
    return Response(OrderSerializer(orders, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, pk):
    try:
        order = Order.objects.prefetch_related(
            'items__product', 'items__variant', 'history'
        ).get(id=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(OrderSerializer(order).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, pk):
    try:
        order = Order.objects.get(id=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if order.status not in ('pending', 'confirmed'):
        return Response(
            {'error': f"Cannot cancel an order with status '{order.status}'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        order.status = 'cancelled'
        order.save()
        for item in order.items.select_related('variant').all():
            item.variant.restore_stock(item.quantity)

    try:
        from notifications.tasks import send_notification_task
        send_notification_task.delay(request.user.id, 'order_cancelled', {'order_id': order.id})
    except Exception:
        pass

    return Response(OrderSerializer(order).data)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def admin_update_order_status(request, pk):
    """
    Admin endpoint to update order status.

    LOYALTY POINTS FOR COD:
    When admin changes a COD order status to 'delivered', loyalty points
    are awarded at that moment. This is the ONLY place COD loyalty points
    are awarded — never at order creation or COD confirmation.
    """
    try:
        order = Order.objects.get(id=pk)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if not new_status:
        return Response({'error': 'status is required.'}, status=status.HTTP_400_BAD_REQUEST)

    valid_statuses = ['pending', 'confirmed', 'preparing', 'out_for_delivery', 'delivered', 'cancelled']
    if new_status not in valid_statuses:
        return Response(
            {'error': f"Invalid status. Choose from: {valid_statuses}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    old_status = order.status
    order.status = new_status
    order.save()

    # ── Award loyalty points for COD orders ONLY on delivery ──────────────────
    # Online payments: points already awarded in payments/views.py::verify_payment
    # COD: points awarded here when admin marks as delivered
    if new_status == 'delivered' and old_status != 'delivered':
        try:
            payment = order.payment
            if payment.method == 'cod':
                from loyalty.services import award_points_for_payment
                amount = order.final_amount or order.total_amount
                points = award_points_for_payment(order.user, amount, order.id)
                # Mark COD payment as complete on delivery
                payment.status = 'success'
                payment.save()
                logger.info(
                    f"COD order #{order.id} delivered — awarded {points} loyalty points "
                    f"to user #{order.user_id}"
                )
            else:
                logger.info(
                    f"Order #{order.id} delivered (online payment) — "
                    f"loyalty points already awarded at payment time"
                )
        except Exception as e:
            logger.warning(f"Could not award loyalty points for order #{order.id}: {e}")

    # Notify customer
    event_map = {
        'confirmed':        'order_confirmed',
        'preparing':        'order_preparing',
        'out_for_delivery': 'order_out_for_delivery',
        'delivered':        'order_delivered',
        'cancelled':        'order_cancelled',
    }
    if new_status in event_map:
        try:
            from notifications.tasks import send_notification_task
            send_notification_task.delay(order.user_id, event_map[new_status], {
                'order_id': order.id,
                'status':   new_status,
            })
        except Exception:
            pass

    return Response(OrderSerializer(order).data)