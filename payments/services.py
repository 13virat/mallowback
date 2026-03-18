"""
Razorpay payment service — all Razorpay interactions live here.
No business logic leaks into views.
"""
import hmac
import hashlib
import logging
import uuid
from django.conf import settings

logger = logging.getLogger('payments')


def _get_client():
    """Return a Razorpay client. Lazy import so missing package doesn't crash on startup."""
    try:
        import razorpay
        return razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    except ImportError:
        raise RuntimeError(
            "razorpay package not installed. Run: pip install razorpay"
        )


def create_razorpay_order(order_id: int, amount_inr: float) -> dict:
    """
    Create a Razorpay order and return the response dict.
    amount_inr: rupees (will be converted to paise).
    Returns: {'id': 'order_xxx', 'amount': 50000, 'currency': 'INR', ...}
    """
    client = _get_client()
    amount_paise = int(float(amount_inr) * 100)
    receipt = f"cakemallow_order_{order_id}"

    try:
        rz_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': receipt,
            'payment_capture': 1,  # auto-capture
            'notes': {
                'order_id': str(order_id),
                'platform': 'cakemallow',
            },
        })
        logger.info(f"Razorpay order created: {rz_order['id']} for order #{order_id}")
        return rz_order
    except Exception as e:
        logger.error(f"Razorpay order creation failed for order #{order_id}: {e}")
        raise


def verify_razorpay_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """
    Verify Razorpay payment signature using HMAC-SHA256.
    Returns True if signature is valid.
    """
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '').encode('utf-8')
    if not key_secret:
        logger.error("RAZORPAY_KEY_SECRET not configured.")
        return False

    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
    expected = hmac.new(key_secret, message, hashlib.sha256).hexdigest()
    result = hmac.compare_digest(expected, razorpay_signature)

    if not result:
        logger.warning(
            f"Signature mismatch for order {razorpay_order_id} payment {razorpay_payment_id}"
        )
    return result


def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    """
    Verify Razorpay webhook signature.
    payload_body: raw request body bytes.

    FIX: In production (DEBUG=False) a missing RAZORPAY_WEBHOOK_SECRET raises
    RuntimeError instead of silently allowing all webhook requests through.
    """
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '').encode('utf-8')
    if not webhook_secret:
        if not getattr(settings, 'DEBUG', True):
            # Production — missing secret is a misconfiguration, not a dev shortcut
            raise RuntimeError(
                "RAZORPAY_WEBHOOK_SECRET is not configured. "
                "Set it in your environment to enable webhook signature verification."
            )
        # Development only — allow without secret so devs can test locally
        logger.warning("RAZORPAY_WEBHOOK_SECRET not set — webhook verification skipped (dev mode).")
        return True

    expected = hmac.new(webhook_secret, payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def generate_idempotency_key(order_id: int) -> str:
    return f"payment-order-{order_id}-{uuid.uuid4().hex[:8]}"
