"""
thread_tasks.py
~~~~~~~~~~~~~~~
A lightweight threading-based async task runner — Celery replacement.
Works perfectly on PythonAnywhere (free tier) with NO external dependencies.

Usage (same interface as Celery):
    from core.thread_tasks import run_async
    run_async(my_function, arg1, arg2, kwarg=value)

Or wrap a function with the @async_task decorator:
    from core.thread_tasks import async_task

    @async_task
    def send_email(user_id, message):
        ...

    send_email.delay(user_id=1, message="hello")   # fires in background thread
    send_email(user_id=1, message="hello")          # runs synchronously
"""

import threading
import logging
import traceback
import functools

logger = logging.getLogger(__name__)


def run_async(fn, *args, **kwargs):
    """
    Run `fn(*args, **kwargs)` in a daemon background thread.
    Exceptions are caught and logged — they never crash the request thread.
    """
    def _wrapper():
        try:
            fn(*args, **kwargs)
        except Exception as e:
            logger.error(
                "Background task %s failed: %s\n%s",
                getattr(fn, '__name__', repr(fn)),
                e,
                traceback.format_exc(),
            )

    t = threading.Thread(target=_wrapper, daemon=True)
    t.start()
    return t


class _AsyncTaskWrapper:
    """
    Wraps a plain function so it behaves like a Celery task with .delay().
    Provides: task.delay(*args, **kwargs)  → runs in background thread
               task(*args, **kwargs)        → runs synchronously
    """
    def __init__(self, fn):
        self._fn = fn
        functools.update_wrapper(self, fn)

    def delay(self, *args, **kwargs):
        """Fire-and-forget in a background thread."""
        return run_async(self._fn, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        """Synchronous call — used in tests or eager mode."""
        return self._fn(*args, **kwargs)


def async_task(fn):
    """
    Decorator: turns a plain function into an async-capable task.

    @async_task
    def send_notification(user_id, event, context):
        ...

    send_notification.delay(1, 'order_placed', {})  # background thread
    send_notification(1, 'order_placed', {})         # synchronous
    """
    return _AsyncTaskWrapper(fn)
