"""
Common API Dependencies
"""
from ninja.security import HttpBearer
from typing import Optional
from django.http import HttpRequest


class AuthBearer(HttpBearer):
    """JWT Bearer Authentication"""

    def authenticate(self, request: HttpRequest, token: str) -> Optional[any]:
        from apps.auth.services import AuthService
        try:
            user = AuthService.verify_token(token)
            return user
        except Exception:
            return None


# Dependency functions
def get_current_user(request):
    """Get current authenticated user"""
    if hasattr(request, 'auth') and request.auth:
        return request.auth
    return None


def require_auth(request):
    """Require authentication"""
    user = get_current_user(request)
    if not user:
        from api.exceptions import PermissionDenied
        raise PermissionDenied("Authentication required")
    return user


def require_admin(request):
    """Require admin privileges"""
    user = require_auth(request)
    if not user.is_staff:
        from api.exceptions import PermissionDenied
        raise PermissionDenied("Admin privileges required")
    return user
