"""
products/tasks.py
~~~~~~~~~~~~~~~~~
Inventory background tasks — uses threading instead of Celery.
Works on PythonAnywhere free tier with no broker.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from core.thread_tasks import async_task

logger = logging.getLogger('products')


def _send_low_stock_alert_sync(variant_id: int):
    """Core logic for low-stock email alert."""
    try:
        from .models import ProductVariant
        variant = ProductVariant.objects.select_related('product').get(id=variant_id)

        subject = f"[Cakemallow] Low Stock Alert: {variant.product.name} ({variant.weight})"
        message = (
            f"Low stock alert!\n\n"
            f"Product: {variant.product.name}\n"
            f"Variant: {variant.weight}\n"
            f"Current Stock: {variant.stock} units\n"
            f"Threshold: {variant.low_stock_threshold} units\n\n"
            f"Please restock soon to avoid lost sales."
        )

        from django.contrib.auth import get_user_model
        admin_emails = list(
            get_user_model()
            .objects.filter(is_staff=True, email__isnull=False)
            .exclude(email='')
            .values_list('email', flat=True)[:5]
        )

        if admin_emails:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=True,
            )
            logger.info("Low-stock alert sent for variant #%s to %s", variant_id, admin_emails)
        else:
            logger.warning("Low-stock alert: no admin emails found for variant #%s", variant_id)

    except Exception as e:
        logger.error("Low-stock alert failed for variant #%s: %s", variant_id, e)


@async_task
def send_low_stock_alert_task(variant_id: int):
    """
    Send low-stock email alert in a background thread.
    Usage: send_low_stock_alert_task.delay(variant_id)
    """
    _send_low_stock_alert_sync(variant_id)
