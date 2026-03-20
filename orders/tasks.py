"""
orders/tasks.py
~~~~~~~~~~~~~~~
Order background tasks — uses threading instead of Celery.
Same .delay() interface. No broker, no Redis, no cost.
Works perfectly on PythonAnywhere free tier.
"""
import logging
from core.thread_tasks import async_task

logger = logging.getLogger('orders')


def _get_order(order_id: int):
    from orders.models import Order
    try:
        return Order.objects.select_related('user', 'address', 'store').get(id=order_id)
    except Order.DoesNotExist:
        raise ValueError(f"Order #{order_id} does not exist")


def _send_order_confirmation_sync(order_id: int, user_id: int):
    """Send order confirmation via notifications service."""
    logger.info("send_order_confirmation started | order=%s user=%s", order_id, user_id)
    try:
        order = _get_order(order_id)
        user = order.user

        logger.info(
            "ORDER CONFIRMED | id=%s user=%s amount=₹%s delivery=%s store=%s",
            order.id,
            user.get_full_name() or getattr(user, 'phone', ''),
            order.final_amount,
            order.delivery_date,
            getattr(order.store, 'name', 'N/A'),
        )

        from notifications.services import send_notification
        send_notification(user, 'order_placed', {
            'order_id':      order.id,
            'total':         str(order.final_amount),
            'delivery_date': str(order.delivery_date),
            'store_name':    getattr(order.store, 'name', ''),
            'items_count':   order.items.count(),
        })

        logger.info("send_order_confirmation DONE | order=%s", order_id)

    except ValueError as exc:
        logger.error("send_order_confirmation PERMANENT FAIL | %s", exc)
    except Exception as exc:
        logger.error("send_order_confirmation ERROR | order=%s error=%r", order_id, exc)
        raise


def _log_order_analytics_sync(order_id: int):
    """Log order analytics data."""
    logger.info("log_order_analytics started | order=%s", order_id)
    try:
        order = _get_order(order_id)

        items = list(order.items.select_related('product', 'variant').values(
            'product__name', 'variant__weight', 'quantity', 'price'
        ))

        logger.info(
            "ANALYTICS | order=%s user=%s amount=₹%s discount=₹%s coupon=%s items=%s",
            order.id,
            order.user_id,
            order.final_amount,
            order.discount_amount,
            order.coupon_code or 'none',
            items,
        )

        # Optional: write to analytics model
        try:
            from analytics.models import OrderAnalyticsEvent
            OrderAnalyticsEvent.objects.create(
                order_id=order.id,
                user_id=order.user_id,
                total=order.final_amount,
                discount=order.discount_amount,
                coupon=order.coupon_code,
            )
        except Exception:
            pass  # analytics failure must never block order flow

    except ValueError as exc:
        logger.error("log_order_analytics FAIL | %s", exc)
    except Exception as exc:
        logger.error("log_order_analytics ERROR | order=%s error=%r", order_id, exc)
        raise


@async_task
def send_order_confirmation(order_id: int, user_id: int):
    """Send order confirmation in background thread."""
    _send_order_confirmation_sync(order_id, user_id)


@async_task
def log_order_analytics(order_id: int):
    """Log order analytics in background thread."""
    _log_order_analytics_sync(order_id)
