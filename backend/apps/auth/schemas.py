"""
Authentication Schemas
"""
from ninja import Schema
from typing import Optional
from datetime import datetime


# Request Schemas
class LoginSchema(Schema):
    email: str
    password: str


class RegisterSchema(Schema):
    email: str
    username: str
    password: str
    confirm_password: str


class FacebookLoginSchema(Schema):
    facebook_access_token: str


class RefreshTokenSchema(Schema):
    refresh_token: str


# Response Schemas
class UserSchema(Schema):
    id: int
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    is_facebook_connected: bool
    facebook_user_id: Optional[str] = None
    created_at: datetime


class TokenSchema(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class AuthResponseSchema(Schema):
    user: UserSchema
    tokens: TokenSchema


class FacebookTokenStatusSchema(Schema):
    is_valid: bool
    expires_at: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    needs_refresh: bool


class MessageSchema(Schema):
    message: str
    success: bool = True
