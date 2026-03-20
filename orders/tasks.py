"""
orders/tasks.py
~~~~~~~~~~~~~~~
Order background tasks — uses threading instead of Celery.
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
    logger.info("send_order_confirmation started | order=%s user=%s", order_id, user_id)
    try:
        order = _get_order(order_id)
        user  = order.user
        logger.info(
            "ORDER CONFIRMED | id=%s user=%s amount=₹%s delivery=%s store=%s",
            order.id, user.get_full_name() or getattr(user, 'phone', ''),
            order.final_amount, order.delivery_date,
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
    logger.info("log_order_analytics started | order=%s", order_id)
    try:
        order = _get_order(order_id)
        items = list(order.items.select_related('product', 'variant').values(
            'product__name', 'variant__weight', 'quantity', 'price'
        ))
        logger.info(
            "ANALYTICS | order=%s user=%s amount=₹%s discount=₹%s coupon=%s items=%s",
            order.id, order.user_id, order.final_amount,
            order.discount_amount, order.coupon_code or 'none', items,
        )
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
            pass
    except ValueError as exc:
        logger.error("log_order_analytics FAIL | %s", exc)
    except Exception as exc:
        logger.error("log_order_analytics ERROR | order=%s error=%r", order_id, exc)
        raise


def _award_loyalty_on_delivery_sync(order_id: int):
    """
    Award loyalty points for COD orders — called ONLY when order is marked 'delivered'.
    For online payments, points are awarded immediately in payments/views.py after
    payment verification succeeds.
    """
    logger.info("award_loyalty_on_delivery started | order=%s", order_id)
    try:
        order = _get_order(order_id)

        # Only award for COD orders — online payments are handled in payments/views.py
        try:
            payment = order.payment
            is_cod  = payment.method == 'cod'
        except Exception:
            is_cod = False

        if not is_cod:
            logger.info(
                "award_loyalty_on_delivery SKIPPED (not COD) | order=%s", order_id
            )
            return

        # Only award once — check if already awarded
        if order.loyalty_points_awarded:
            logger.info(
                "award_loyalty_on_delivery SKIPPED (already awarded) | order=%s", order_id
            )
            return

        from loyalty.services import award_points_for_payment
        points = award_points_for_payment(order.user, order.final_amount, order_id)

        # Mark as awarded to prevent double-awarding
        order.loyalty_points_awarded = True
        order.save(update_fields=['loyalty_points_awarded'])

        logger.info(
            "award_loyalty_on_delivery DONE | order=%s points=%s", order_id, points
        )
    except ValueError as exc:
        logger.error("award_loyalty_on_delivery FAIL | %s", exc)
    except AttributeError:
        # loyalty_points_awarded field may not exist yet — award anyway
        try:
            order = _get_order(order_id)
            try:
                payment = order.payment
                if payment.method == 'cod':
                    from loyalty.services import award_points_for_payment
                    award_points_for_payment(order.user, order.final_amount, order_id)
                    logger.info("award_loyalty_on_delivery DONE (no flag field) | order=%s", order_id)
            except Exception:
                pass
        except Exception as exc:
            logger.error("award_loyalty_on_delivery ERROR | order=%s error=%r", order_id, exc)
    except Exception as exc:
        logger.error("award_loyalty_on_delivery ERROR | order=%s error=%r", order_id, exc)
        raise


@async_task
def send_order_confirmation(order_id: int, user_id: int):
    _send_order_confirmation_sync(order_id, user_id)


@async_task
def log_order_analytics(order_id: int):
    _log_order_analytics_sync(order_id)


@async_task
def award_loyalty_on_delivery(order_id: int):
    """Called when a COD order is marked as delivered."""
    _award_loyalty_on_delivery_sync(order_id)