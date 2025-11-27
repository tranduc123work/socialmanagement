"""
Authentication API Endpoints
"""
from ninja import Router
from django.http import HttpRequest
from .schemas import (
    LoginSchema, RegisterSchema, FacebookLoginSchema,
    RefreshTokenSchema, AuthResponseSchema, FacebookTokenStatusSchema,
    MessageSchema, UserSchema
)
from .services import AuthService
from api.dependencies import AuthBearer, get_current_user

router = Router()


@router.post("/login", response=AuthResponseSchema, tags=["Auth"])
def login(request: HttpRequest, data: LoginSchema):
    """
    Login with email and password
    """
    result = AuthService.login(data.email, data.password)
    return result


@router.post("/register", response=AuthResponseSchema, tags=["Auth"])
def register(request: HttpRequest, data: RegisterSchema):
    """
    Register new user
    """
    result = AuthService.register(
        email=data.email,
        username=data.username,
        password=data.password,
        confirm_password=data.confirm_password
    )
    return result


@router.post("/facebook/login", response=AuthResponseSchema, tags=["Auth"])
def facebook_login(request: HttpRequest, data: FacebookLoginSchema):
    """
    Login/Register with Facebook
    """
    result = AuthService.facebook_login(data.facebook_access_token)
    return result


@router.post("/refresh", response={200: dict}, tags=["Auth"])
def refresh_token(request: HttpRequest, data: RefreshTokenSchema):
    """
    Refresh access token
    """
    tokens = AuthService.refresh_access_token(data.refresh_token)
    return tokens


@router.get("/me", response=UserSchema, auth=AuthBearer(), tags=["Auth"])
def get_current_user_info(request: HttpRequest):
    """
    Get current authenticated user info
    """
    return request.auth


@router.get("/status", response=FacebookTokenStatusSchema, auth=AuthBearer(), tags=["Auth"])
def get_token_status(request: HttpRequest):
    """
    Get Facebook token status
    """
    user = request.auth
    status = AuthService.get_facebook_token_status(user)
    return status


@router.post("/logout", response=MessageSchema, auth=AuthBearer(), tags=["Auth"])
def logout(request: HttpRequest):
    """
    Logout user (revoke refresh tokens)
    """
    user = request.auth
    # Revoke all refresh tokens for this user
    from .models import RefreshToken
    RefreshToken.objects.filter(user=user, is_revoked=False).update(is_revoked=True)

    return {"message": "Logged out successfully", "success": True}


@router.post("/facebook/connect", response=MessageSchema, auth=AuthBearer(), tags=["Auth"])
def connect_facebook(request: HttpRequest, data: FacebookLoginSchema):
    """
    Connect Facebook account to existing user
    """
    user = request.auth
    result = AuthService.facebook_login(data.facebook_access_token)

    # Update current user with Facebook data
    fb_user = result['user']
    user.facebook_user_id = fb_user.facebook_user_id
    user.facebook_access_token = fb_user.facebook_access_token
    user.facebook_token_expires_at = fb_user.facebook_token_expires_at
    user.is_facebook_connected = True
    user.save()

    return {"message": "Facebook account connected successfully", "success": True}
