"""
notifications/tasks.py
~~~~~~~~~~~~~~~~~~~~~~
Background notification tasks — uses threading instead of Celery.
Drop-in replacement: same .delay() interface, no broker needed.
Works on PythonAnywhere free tier.
"""
import logging
from core.thread_tasks import async_task

logger = logging.getLogger('notifications')


def _send_notification_sync(user_id: int, event: str, context: dict):
    """Core logic — runs in background thread or synchronously."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        from notifications.services import send_notification
        send_notification(user, event, context)
    except Exception as e:
        logger.error(
            "send_notification_task failed: user=%s event=%s error=%s",
            user_id, event, e
        )
        raise


@async_task
def send_notification_task(user_id: int, event: str, context: dict = None):
    """
    Send a notification asynchronously in a background thread.
    Usage: send_notification_task.delay(user_id, event, context)
    """
    _send_notification_sync(user_id, event, context or {})
