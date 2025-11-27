"""
Auth Permissions
"""
from api.exceptions import PermissionDenied


def require_facebook_connection(user):
    """Require user to have Facebook connected"""
    if not user.is_facebook_connected:
        raise PermissionDenied("Facebook account connection required")
    if not user.is_token_valid():
        raise PermissionDenied("Facebook token expired. Please reconnect")
    return True


def require_admin(user):
    """Require admin privileges"""
    if not user.is_staff:
        raise PermissionDenied("Admin privileges required")
    return True


def can_manage_post(user, post):
    """Check if user can manage a specific post"""
    if user.is_staff:
        return True
    if post.created_by_id == user.id:
        return True
    raise PermissionDenied("You don't have permission to manage this post")
