"""
Payment views — Razorpay create, verify, webhook, COD.
Webhook fully handles: stock deduction, loyalty points, notifications.

LOYALTY POINT RULES:
- Online (Razorpay): awarded immediately after payment.verify succeeds
- COD: awarded ONLY after admin marks order as 'delivered'
  (triggered in orders/views.py::admin_update_order_status)
"""
import json
import logging
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle

from orders.models import Order
from .models import Payment, PaymentWebhookLog
from .serializers import PaymentSerializer, PaymentVerifySerializer
from .services import (
    create_razorpay_order,
    verify_razorpay_signature,
    verify_webhook_signature,
    generate_idempotency_key,
)

logger = logging.getLogger('payments')


class PaymentThrottle(ScopedRateThrottle):
    scope = 'payment'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentThrottle])
def initiate_payment(request, order_id):
    """
    POST /api/payments/initiate/<order_id>/
    Creates Razorpay order. Idempotent — returns existing if already pending.
    """
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(order, 'payment') and order.payment.is_paid:
            return Response({'error': 'Order is already paid.'}, status=status.HTTP_400_BAD_REQUEST)

        # Idempotency: return existing pending Razorpay order
        if hasattr(order, 'payment') and order.payment.razorpay_order_id:
            p = order.payment
            if p.status in ('initiated', 'pending'):
                return Response({
                    'razorpay_order_id': p.razorpay_order_id,
                    'amount': int(p.amount * 100),
                    'currency': 'INR',
                    'key': settings.RAZORPAY_KEY_ID,
                    'order_id': order.id,
                    'idempotency_key': p.idempotency_key,
                })

        try:
            rz_order = create_razorpay_order(
                order.id, float(order.final_amount or order.total_amount)
            )
        except Exception as e:
            logger.error(f"Payment initiation failed for order #{order_id}: {e}")
            return Response(
                {'error': 'Payment gateway error. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        idempotency_key = generate_idempotency_key(order.id)
        Payment.objects.update_or_create(
            order=order,
            defaults={
                'user': request.user,
                'amount': order.final_amount or order.total_amount,
                'method': 'razorpay',
                'status': 'initiated',
                'razorpay_order_id': rz_order['id'],
                'idempotency_key': idempotency_key,
                'gateway_response': rz_order,
            }
        )

    return Response({
        'razorpay_order_id': rz_order['id'],
        'amount': rz_order['amount'],
        'currency': 'INR',
        'key': settings.RAZORPAY_KEY_ID,
        'order_id': order.id,
        'idempotency_key': idempotency_key,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentThrottle])
def verify_payment(request):
    """
    POST /api/payments/verify/
    Verifies HMAC-SHA256 signature. Idempotent — safe to call twice.
    Awards loyalty points immediately for online payments.
    """
    serializer = PaymentVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    rz_order_id   = data['razorpay_order_id']
    rz_payment_id = data['razorpay_payment_id']
    rz_signature  = data['razorpay_signature']

    try:
        payment = Payment.objects.select_related('order').get(
            razorpay_order_id=rz_order_id,
            user=request.user
        )
    except Payment.DoesNotExist:
        return Response({'error': 'Payment record not found.'}, status=status.HTTP_404_NOT_FOUND)

    if payment.is_paid:
        return Response({'message': 'Payment already verified.', 'order_id': payment.order.id})

    if not verify_razorpay_signature(rz_order_id, rz_payment_id, rz_signature):
        with transaction.atomic():
            payment.status = 'failed'
            payment.failure_reason = 'Invalid signature'
            payment.save()
        logger.warning(f"Invalid payment signature — order #{payment.order_id} payment {rz_payment_id}")
        return Response(
            {'error': 'Payment verification failed. Invalid signature.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        payment.razorpay_payment_id = rz_payment_id
        payment.razorpay_signature  = rz_signature
        payment.status = 'success'
        payment.save()

        order = payment.order
        order.transition_to('confirmed', performed_by=request.user, notes='Payment verified')

        # Online payment: award loyalty points IMMEDIATELY
        _post_online_payment_success(order, request.user, payment.amount)

    try:
        from notifications.tasks import send_notification_task
        send_notification_task.delay(request.user.id, 'payment_success', {
            'order_id': order.id,
            'amount': str(payment.amount),
        })
    except Exception as e:
        logger.warning(f"Notification dispatch failed (non-critical): {e}")

    logger.info(f"Payment verified: order #{order.id} payment {rz_payment_id}")
    return Response({
        'message': 'Payment verified successfully.',
        'order_id': order.id,
        'payment_id': rz_payment_id,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cod_payment(request, order_id):
    """
    POST /api/payments/cod/<order_id>/
    Mark order as Cash on Delivery.

    IMPORTANT: Loyalty points are NOT awarded here.
    For COD, points are awarded ONLY when admin marks order as 'delivered'
    in admin_update_order_status() in orders/views.py.
    This prevents awarding points for orders that may never be delivered.
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if hasattr(order, 'payment') and order.payment.is_paid:
        return Response(
            {'error': 'Order already has a completed payment.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        Payment.objects.update_or_create(
            order=order,
            defaults={
                'user': request.user,
                'amount': order.final_amount or order.total_amount,
                'method': 'cod',
                'status': 'pending',   # stays pending until delivery
            }
        )
        order.transition_to('confirmed', performed_by=request.user, notes='COD confirmed')

        # ── Stock deduction only — NO loyalty points for COD ──────────────────
        # Points awarded after delivery in orders/views.py::admin_update_order_status
        try:
            from products.services import deduct_stock_for_order
            deduct_stock_for_order(order)
        except Exception as e:
            logger.error(f"Stock deduction failed for COD order #{order.id}: {e}")

    try:
        from notifications.tasks import send_notification_task
        send_notification_task.delay(request.user.id, 'order_confirmed', {
            'order_id': order.id,
            'delivery_date': str(order.delivery_date),
        })
    except Exception:
        pass

    logger.info(f"COD order #{order.id} confirmed. Loyalty points pending delivery.")
    return Response({'message': 'Order confirmed with Cash on Delivery.', 'order_id': order.id})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    """
    POST /api/payments/webhook/razorpay/
    Razorpay server-to-server webhook. Verified via RAZORPAY_WEBHOOK_SECRET.
    Idempotent — duplicate events skipped via PaymentWebhookLog.
    """
    signature = request.headers.get('X-Razorpay-Signature', '')
    raw_body  = request.body

    if not verify_webhook_signature(raw_body, signature):
        logger.warning("Webhook rejected: invalid signature.")
        return Response({'error': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return Response({'error': 'Invalid JSON.'}, status=status.HTTP_400_BAD_REQUEST)

    event_type = payload.get('event', 'unknown')
    event_id   = (
        payload.get('payload', {})
               .get('payment', {})
               .get('entity', {})
               .get('id', '')
    )

    if PaymentWebhookLog.objects.filter(event_id=event_id, processed=True).exists():
        logger.info(f"Webhook event {event_id} already processed — skipping.")
        return Response({'status': 'already_processed'})

    log = PaymentWebhookLog.objects.create(
        event_id=event_id or f"evt_{event_type}_{id(payload)}",
        event_type=event_type,
        payload=payload,
    )

    try:
        _handle_webhook_event(event_type, payload)
        log.processed = True
        log.save()
    except Exception as e:
        log.error = str(e)
        log.save()
        logger.error(f"Webhook handler error for {event_id}: {e}")

    return Response({'status': 'ok'})


# ── Webhook event handlers ────────────────────────────────────────────────────

def _handle_webhook_event(event_type: str, payload: dict):
    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    refund_entity  = payload.get('payload', {}).get('refund',  {}).get('entity', {})

    handlers = {
        'payment.captured': lambda: _handle_payment_captured(payment_entity),
        'payment.failed':   lambda: _handle_payment_failed(payment_entity),
        'refund.created':   lambda: _handle_refund_created(refund_entity),
    }

    handler = handlers.get(event_type)
    if handler:
        handler()
    else:
        logger.info(f"Unhandled webhook event type: {event_type}")


def _handle_payment_captured(payment_entity: dict):
    """
    Webhook backup for online payments only.
    Awards loyalty points immediately (same as verify_payment).
    Never called for COD payments.
    """
    rz_order_id   = payment_entity.get('order_id')
    rz_payment_id = payment_entity.get('id')

    if not rz_order_id:
        logger.warning("Webhook payment.captured missing order_id")
        return

    try:
        payment = Payment.objects.select_related('order__user').get(
            razorpay_order_id=rz_order_id
        )
    except Payment.DoesNotExist:
        logger.warning(f"Webhook: no Payment for Razorpay order {rz_order_id}")
        return

    if payment.is_paid:
        logger.info(f"Webhook: order #{payment.order_id} already paid — skipping.")
        return

    with transaction.atomic():
        payment.razorpay_payment_id = rz_payment_id
        payment.status = 'success'
        payment.gateway_response = payment_entity
        payment.save()

        order = payment.order
        order.transition_to('confirmed', notes='Confirmed via Razorpay webhook')

        # Online payment via webhook — award points immediately
        _post_online_payment_success(order, order.user, payment.amount)

    try:
        from notifications.tasks import send_notification_task
        send_notification_task.delay(order.user_id, 'payment_success', {
            'order_id': order.id,
            'amount': str(payment.amount),
        })
    except Exception:
        pass

    logger.info(f"Webhook confirmed payment: order #{payment.order_id}")


def _handle_payment_failed(payment_entity: dict):
    rz_order_id = payment_entity.get('order_id')
    error_desc  = payment_entity.get('error_description', 'Unknown error')

    if not rz_order_id:
        return

    try:
        payment = Payment.objects.get(razorpay_order_id=rz_order_id)
        if payment.status != 'success':
            payment.status = 'failed'
            payment.failure_reason = error_desc
            payment.save()
            logger.info(f"Webhook marked payment failed: order #{payment.order_id}")
    except Payment.DoesNotExist:
        pass


def _handle_refund_created(refund_entity: dict):
    rz_payment_id = refund_entity.get('payment_id')
    try:
        payment = Payment.objects.get(razorpay_payment_id=rz_payment_id)
        payment.status = 'refunded'
        payment.save()
        logger.info(f"Webhook processed refund for payment {rz_payment_id}")
    except Payment.DoesNotExist:
        pass


# ── Shared post-payment logic ─────────────────────────────────────────────────

def _post_online_payment_success(order, user, amount):
    """
    Called ONLY for online (Razorpay) payments after successful verification.
    Deducts stock AND awards loyalty points immediately.

    NOT called for COD — COD points are awarded after delivery in orders/views.py.
    """
    try:
        from products.services import deduct_stock_for_order
        deduct_stock_for_order(order)
    except Exception as e:
        logger.error(f"Stock deduction failed for order #{order.id}: {e}")

    # Award loyalty points immediately for online payment
    try:
        from loyalty.services import award_points_for_payment
        points = award_points_for_payment(user, amount, order.id)
        logger.info(f"Awarded {points} loyalty points for online payment — order #{order.id}")
    except Exception as e:
        logger.error(f"Loyalty points failed for order #{order.id}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CAKE ADVANCE PAYMENT
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_advance_payment(request, order_id):
    """
    POST /api/payments/advance/<order_id>/
    Creates a Razorpay order for 50% advance on a custom cake order.
    Returns razorpay_order_id + amount (50% of total) for frontend to open Razorpay.
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if order.order_type != 'custom':
        return Response({'error': 'Advance payment is only for custom cake orders.'}, status=400)

    if hasattr(order, 'payment') and order.payment.is_paid:
        return Response({'error': 'Advance already paid.'}, status=400)

    total     = float(order.final_amount or order.total_amount)
    advance   = round(total * 0.5, 2)   # 50%
    remaining = round(total - advance, 2)

    # Idempotency — return existing if already initiated
    if hasattr(order, 'payment') and order.payment.razorpay_order_id:
        p = order.payment
        if p.status in ('initiated', 'pending'):
            return Response({
                'razorpay_order_id': p.razorpay_order_id,
                'advance_amount':    int(p.advance_amount * 100),
                'remaining_amount':  float(p.remaining_amount),
                'total_amount':      float(total),
                'currency':          'INR',
                'key':               settings.RAZORPAY_KEY_ID,
                'order_id':          order.id,
            })

    try:
        rz_order = create_razorpay_order(order.id, advance)
    except Exception as e:
        logger.error(f"Advance payment initiation failed for order #{order_id}: {e}")
        return Response({'error': 'Payment gateway error. Please try again.'}, status=502)

    idempotency_key = generate_idempotency_key(order.id)
    Payment.objects.update_or_create(
        order=order,
        defaults={
            'user':              request.user,
            'method':            'custom_advance',
            'status':            'initiated',
            'amount':            total,         # full order amount
            'advance_amount':    advance,        # 50% — what's being paid now
            'remaining_amount':  remaining,      # 50% — due on delivery
            'razorpay_order_id': rz_order['id'],
            'idempotency_key':   idempotency_key,
            'gateway_response':  rz_order,
        }
    )

    logger.info(f"Advance payment initiated: order #{order_id}, advance ₹{advance}, remaining ₹{remaining}")
    return Response({
        'razorpay_order_id': rz_order['id'],
        'advance_amount':    int(advance * 100),   # paise for Razorpay
        'remaining_amount':  remaining,
        'total_amount':      total,
        'currency':          'INR',
        'key':               settings.RAZORPAY_KEY_ID,
        'order_id':          order.id,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_advance_payment(request):
    """
    POST /api/payments/advance/verify/
    Verifies Razorpay signature for advance payment.
    Marks order as confirmed with advance_paid status.
    Awards HALF loyalty points now, rest on delivery.
    """
    serializer = PaymentVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    rz_order_id   = data['razorpay_order_id']
    rz_payment_id = data['razorpay_payment_id']
    rz_signature  = data['razorpay_signature']

    try:
        payment = Payment.objects.select_related('order').get(
            razorpay_order_id=rz_order_id,
            user=request.user,
            method='custom_advance',
        )
    except Payment.DoesNotExist:
        return Response({'error': 'Payment record not found.'}, status=404)

    if payment.is_paid:
        return Response({
            'message':          'Advance already verified.',
            'order_id':         payment.order.id,
            'remaining_amount': float(payment.remaining_amount),
        })

    if not verify_razorpay_signature(rz_order_id, rz_payment_id, rz_signature):
        payment.status = 'failed'
        payment.failure_reason = 'Invalid signature'
        payment.save()
        logger.warning(f"Invalid advance payment signature — order #{payment.order_id}")
        return Response({'error': 'Payment verification failed. Invalid signature.'}, status=400)

    with transaction.atomic():
        payment.razorpay_payment_id = rz_payment_id
        payment.razorpay_signature  = rz_signature
        payment.status = 'success'
        payment.save()

        order = payment.order
        # Transition to preparing — advance paid, bakery can start
        if order.status == 'confirmed':
            order.transition_to(
                'preparing',
                performed_by=request.user,
                notes=f'50% advance of ₹{payment.advance_amount} paid. Remaining ₹{payment.remaining_amount} due on delivery.'
            )

        # Award loyalty points for advance amount only (half now, half on delivery)
        try:
            from loyalty.services import award_points_for_payment
            points = award_points_for_payment(request.user, payment.advance_amount, order.id)
            logger.info(f"Awarded {points} loyalty points for advance — order #{order.id}")
        except Exception as e:
            logger.error(f"Loyalty points failed for advance order #{order.id}: {e}")

    # Notify customer
    try:
        from notifications.models import Notification
        Notification.objects.create(
            user=request.user,
            title="Advance payment confirmed! 🎂",
            message=(
                f"₹{payment.advance_amount} advance received for your custom cake. "
                f"We're now preparing your cake! ₹{payment.remaining_amount} due on delivery."
            ),
            notification_type="payment",
        )
    except Exception:
        pass

    logger.info(f"Advance payment verified: order #{order.id}, advance ₹{payment.advance_amount}")
    return Response({
        'message':          'Advance payment verified. Bakery is now preparing your cake!',
        'order_id':         order.id,
        'advance_paid':     float(payment.advance_amount),
        'remaining_amount': float(payment.remaining_amount),
        'remaining_due':    'on delivery',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_remaining_paid(request, order_id):
    """
    POST /api/payments/advance/<order_id>/mark-paid/
    Admin marks the remaining 50% as collected on delivery.
    Awards remaining loyalty points.
    """
    from rest_framework.permissions import IsAdminUser
    if not request.user.is_staff:
        return Response({'error': 'Admin only.'}, status=403)

    try:
        order = Order.objects.get(id=order_id)
        payment = order.payment
    except (Order.DoesNotExist, Payment.DoesNotExist):
        return Response({'error': 'Order or payment not found.'}, status=404)

    if not payment.is_custom_advance:
        return Response({'error': 'Not a custom advance payment.'}, status=400)

    if payment.remaining_paid:
        return Response({'message': 'Remaining amount already marked as paid.'})

    payment.remaining_paid = True
    payment.save()

    # Award remaining loyalty points
    try:
        from loyalty.services import award_points_for_payment
        points = award_points_for_payment(order.user, payment.remaining_amount, order.id)
        logger.info(f"Awarded {points} remaining loyalty points — order #{order.id}")
    except Exception as e:
        logger.error(f"Remaining loyalty points failed — order #{order.id}: {e}")

    # Notify customer
    try:
        from notifications.models import Notification
        Notification.objects.create(
            user=order.user,
            title="Full payment received! 🎂",
            message=f"₹{payment.remaining_amount} balance received. Thank you!",
            notification_type="payment",
        )
    except Exception:
        pass

    return Response({
        'message':          'Remaining payment marked as collected.',
        'advance_paid':     float(payment.advance_amount),
        'remaining_paid':   float(payment.remaining_amount),
        'total_paid':       float(payment.amount),
    })