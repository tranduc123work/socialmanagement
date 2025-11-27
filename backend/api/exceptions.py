"""
Global Exception Handlers
"""
from ninja import NinjaAPI
from django.http import JsonResponse
import traceback
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(request, exc):
    """
    Custom exception handler for Django Ninja API
    """
    # Only log full traceback for unexpected errors (500)
    # ValidationError, PermissionDenied, NotFound are expected errors
    if isinstance(exc, (ValidationError, PermissionDenied, NotFound)):
        # Don't log validation errors - they're handled by auth logger
        pass
    else:
        logger.error(f"API Error: {str(exc)}\n{traceback.format_exc()}")

    # Handle different types of exceptions
    if hasattr(exc, 'status_code'):
        status_code = exc.status_code
    elif isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, PermissionDenied):
        status_code = 403
    elif isinstance(exc, NotFound):
        status_code = 404
    else:
        status_code = 500

    # Build error response
    error_response = {
        "error": True,
        "message": str(exc),
        "type": exc.__class__.__name__,
    }

    # Add details in debug mode
    from django.conf import settings
    if settings.DEBUG:
        error_response["traceback"] = traceback.format_exc()

    return JsonResponse(error_response, status=status_code)


# Custom Exception Classes
class ValidationError(Exception):
    status_code = 400


class PermissionDenied(Exception):
    status_code = 403


class NotFound(Exception):
    status_code = 404


class FacebookAPIError(Exception):
    status_code = 502


class AIServiceError(Exception):
    status_code = 503
