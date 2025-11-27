"""
Custom Middleware
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all API requests"""

    def process_request(self, request):
        request.start_time = time.time()
        return None

    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(
                f"{request.method} {request.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {duration:.2f}s"
            )
        return response


class FacebookTokenMiddleware(MiddlewareMixin):
    """Check Facebook token validity"""

    def process_request(self, request):
        # Skip token check for certain endpoints
        skip_paths = ['/api/auth/', '/api/health', '/admin/', '/api/docs']
        if any(request.path.startswith(path) for path in skip_paths):
            return None

        # Add custom logic for token validation
        return None
