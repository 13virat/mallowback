from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from .models import CustomCakeRequest
from .serializers import CustomCakeSerializer
import logging

logger = logging.getLogger('customization')


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_cake_request(request):
    serializer = CustomCakeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user if request.user.is_authenticated else None
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_custom_cake_requests(request):
    reqs = CustomCakeRequest.objects.filter(user=request.user)
    serializer = CustomCakeSerializer(reqs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_custom_cake_requests(request):
    """Admin: list all custom cake requests across all users."""
    reqs = CustomCakeRequest.objects.select_related('user').all()
    serializer = CustomCakeSerializer(reqs, many=True, context={'request': request})
    return Response(serializer.data)


def _create_order_from_custom_cake(req, performed_by=None):
    """
    Auto-create an Order when a custom cake request is accepted.
    Parses price from admin_notes if possible (e.g. "Total: ₹1200 ...").
    """
    from orders.models import Order, OrderItem
    import re

    # Try to extract price from admin_notes e.g. "Total: ₹1,200" or "Price: 1200"
    price = 0
    if req.admin_notes:
        match = re.search(r'[₹Rs\.]*\s*([0-9,]+)', req.admin_notes.replace(',', ''))
        if match:
            try:
                price = float(match.group(1).replace(',', ''))
            except ValueError:
                price = 0

    order = Order.objects.create(
        user=req.user,
        address=None,               # No address for custom orders initially
        order_type='custom',
        custom_cake_request=req,
        total_amount=price,
        discount_amount=0,
        delivery_charge=0,
        final_amount=price,
        delivery_date=req.delivery_date,
        notes=f"Custom cake order. Quote: {req.admin_notes}",
        status='confirmed',
        )

    # Create a single line item describing the custom cake
    OrderItem.objects.create(
        order=order,
        product=None,
        variant=None,
        quantity=1,
        price=price,
        custom_item_name=f"Custom {req.cake_type} — {req.flavour} ({req.weight})",
        message_on_cake=req.message or '',
    )

    # Log the confirmed transition in history
    from orders.models import OrderStatusHistory
    OrderStatusHistory.objects.create(
        order=order,
        old_status='',
        new_status='confirmed',
        changed_by=performed_by,
        notes='Auto-created from accepted custom cake request.',
    )

    logger.info(f"Order #{order.id} created from custom cake request #{req.id}")
    return order


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_custom_cake_request(request, pk):
    """Admin: update status and admin_notes."""
    try:
        req = CustomCakeRequest.objects.get(id=pk)
    except CustomCakeRequest.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    old_status = req.status

    if 'status' in request.data:
        req.status = request.data['status']
    if 'admin_notes' in request.data:
        req.admin_notes = request.data['admin_notes']
    req.save()

    # ── Quoted: notify customer ───────────────────────────────────────────────
    if request.data.get('status') == 'quoted' and req.user:
        try:
            from notifications.models import Notification
            Notification.objects.create(
                user=req.user,
                title="Your custom cake quote is ready! 🎂",
                message="We've prepared a quote for your custom cake. Check it to accept or decline.",
                notification_type="custom_cake",
            )
        except Exception as e:
            logger.warning(f"Notification failed for req #{req.id}: {e}")

    # ── Accepted: auto-create order ───────────────────────────────────────────
    if request.data.get('status') == 'accepted' and old_status != 'accepted' and req.user:
        # Only create if order doesn't already exist
        if not hasattr(req, 'order') or req.order is None:
            try:
                order = _create_order_from_custom_cake(req, performed_by=request.user)
                # Notify customer
                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        user=req.user,
                        title="Custom cake order confirmed! 🎂",
                        message=f"Your custom cake has been accepted. Order #{order.id} confirmed for {req.delivery_date}.",
                        notification_type="order",
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Order creation failed for req #{req.id}: {e}")
                # Don't fail the status update — order can be created manually

    # ── Rejected: notify customer ─────────────────────────────────────────────
    if request.data.get('status') == 'rejected' and req.user:
        try:
            from notifications.models import Notification
            Notification.objects.create(
                user=req.user,
                title="Update on your custom cake request",
                message=req.admin_notes or "Unfortunately we are unable to fulfill your custom cake request.",
                notification_type="custom_cake",
            )
        except Exception as e:
            logger.warning(f"Rejection notification failed for req #{req.id}: {e}")

    return Response(CustomCakeSerializer(req, context={'request': request}).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def respond_to_quote(request, pk):
    """Customer accepts or rejects a quote."""
    try:
        req = CustomCakeRequest.objects.get(id=pk, user=request.user)
    except CustomCakeRequest.DoesNotExist:
        return Response({'error': 'Not found.'}, status=404)

    if req.status != 'quoted':
        return Response({'error': 'Can only respond to quoted requests.'}, status=400)

    response = request.data.get('response')
    if response not in ('accepted', 'rejected'):
        return Response({'error': 'response must be "accepted" or "rejected".'}, status=400)

    req.status = response
    req.save()

    # If customer accepted, create the order and return payment info
    if response == 'accepted':
        order = None
        # Check if order already exists
        try:
            order = req.order
        except Exception:
            pass

        if order is None:
            try:
                order = _create_order_from_custom_cake(req)
            except Exception as e:
                logger.error(f"Order creation failed on customer accept, req #{req.id}: {e}")

        if order:
            total = float(order.final_amount or order.total_amount)
            advance = round(total * 0.5, 2)
            remaining = round(total - advance, 2)
            data = CustomCakeSerializer(req, context={'request': request}).data
            data['order_id'] = order.id
            data['payment'] = {
                'total_amount':     total,
                'advance_amount':   advance,
                'remaining_amount': remaining,
                'advance_percent':  50,
                'initiate_url':     f'/api/payments/advance/{order.id}/',
                'verify_url':       '/api/payments/advance/verify/',
                'message':          f'Pay ₹{advance:.0f} now (50% advance) to confirm your order. ₹{remaining:.0f} due on delivery.',
            }
            return Response(data)

    return Response(CustomCakeSerializer(req, context={'request': request}).data)