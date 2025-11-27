"""
Schemas for Platforms API
"""
from ninja import Schema
from typing import Optional, List, Dict, Any
from datetime import datetime


class SocialAccountSchema(Schema):
    """Schema for social account response"""
    id: int
    platform: str
    platform_account_id: str
    name: str
    username: Optional[str] = None
    profile_picture_url: Optional[str] = None
    category: Optional[str] = None
    is_active: bool
    is_token_expired: bool = False
    created_at: datetime

    @staticmethod
    def resolve_is_token_expired(obj):
        return obj.is_token_expired()


class SocialAccountCreateSchema(Schema):
    """Schema for creating/connecting social account"""
    platform: str
    code: str  # OAuth authorization code
    redirect_uri: str


class SocialPostSchema(Schema):
    """Schema for social post response"""
    id: int
    content: str
    title: Optional[str] = None
    media_urls: List[str] = []
    media_type: str
    link_url: Optional[str] = None
    status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime


class SocialPostCreateSchema(Schema):
    """Schema for creating a social post"""
    content: str
    title: Optional[str] = None
    media_urls: List[str] = []
    media_type: str = 'none'
    link_url: Optional[str] = None
    target_account_ids: List[int]  # IDs of SocialAccount
    scheduled_at: Optional[datetime] = None


class PublishStatusSchema(Schema):
    """Schema for publish status response"""
    account_id: int
    account_name: str
    platform: str
    status: str
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None


class PostDetailSchema(Schema):
    """Detailed post with publish statuses"""
    id: int
    content: str
    title: Optional[str] = None
    media_urls: List[str] = []
    media_type: str
    status: str
    scheduled_at: Optional[datetime] = None
    publish_statuses: List[PublishStatusSchema] = []
    created_at: datetime


class OAuthUrlSchema(Schema):
    """Schema for OAuth URL response"""
    auth_url: str
    state: str


class PlatformInfoSchema(Schema):
    """Schema for platform information"""
    id: str
    name: str
    icon: str
    connected_accounts: int = 0
    supported_features: List[str] = []


class ValidationResultSchema(Schema):
    """Schema for content validation result"""
    valid: bool
    errors: List[str] = []
