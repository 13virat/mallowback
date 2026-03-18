"""
Centralised exception handler — consistent error envelope across all endpoints.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception — 500
        logger.exception(f"Unhandled exception in {context.get('view')}: {exc}")
        return Response(
            {'error': 'An unexpected error occurred. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Wrap DRF errors in a consistent envelope
    if isinstance(response.data, dict) and 'detail' in response.data:
        response.data = {'error': str(response.data['detail'])}
    elif isinstance(response.data, list):
        response.data = {'error': response.data}
    # Keep dict errors as-is (field validation errors already have good structure)

    return response
