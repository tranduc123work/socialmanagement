"""
Base Platform Service - Abstract class for all social media platforms
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PostResult:
    """Result of publishing a post"""
    success: bool
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class AccountInfo:
    """Information about a social media account"""
    platform_account_id: str
    name: str
    username: Optional[str] = None
    profile_picture_url: Optional[str] = None
    category: Optional[str] = None
    followers_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class BasePlatformService(ABC):
    """
    Abstract base class for social media platform services.
    Currently implemented: Facebook
    Future platforms: Instagram, Zalo, TikTok, etc.
    """

    PLATFORM_NAME: str = "base"
    API_VERSION: str = "v1"

    @abstractmethod
    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """
        Generate OAuth authorization URL for the platform

        Args:
            redirect_uri: URL to redirect after authorization
            state: State parameter for CSRF protection

        Returns:
            str: Authorization URL
        """
        pass

    @abstractmethod
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in auth request

        Returns:
            Dict containing access_token, refresh_token (if any), expires_at
        """
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token

        Args:
            refresh_token: Refresh token

        Returns:
            Dict containing new access_token and expires_at
        """
        pass

    @abstractmethod
    def get_account_info(self, access_token: str, account_id: Optional[str] = None) -> AccountInfo:
        """
        Get account/page information

        Args:
            access_token: Valid access token
            account_id: Optional account ID (for pages)

        Returns:
            AccountInfo object
        """
        pass

    @abstractmethod
    def get_accounts_list(self, access_token: str) -> List[AccountInfo]:
        """
        Get list of accounts/pages the user can manage

        Args:
            access_token: Valid access token

        Returns:
            List of AccountInfo objects
        """
        pass

    @abstractmethod
    def publish_post(
        self,
        access_token: str,
        account_id: str,
        content: str,
        media_urls: Optional[List[str]] = None,
        media_type: str = 'none',
        link_url: Optional[str] = None,
        scheduled_time: Optional[datetime] = None,
        **kwargs
    ) -> PostResult:
        """
        Publish a post to the platform

        Args:
            access_token: Valid access token
            account_id: Account/Page ID to post to
            content: Post content/caption
            media_urls: List of media URLs (images/videos)
            media_type: Type of media ('none', 'image', 'video', 'carousel')
            link_url: Optional link to share
            scheduled_time: Optional time to schedule the post
            **kwargs: Platform-specific options

        Returns:
            PostResult object with success status and post details
        """
        pass

    @abstractmethod
    def delete_post(self, access_token: str, post_id: str) -> bool:
        """
        Delete a post from the platform

        Args:
            access_token: Valid access token
            post_id: Platform-specific post ID

        Returns:
            bool: True if deleted successfully
        """
        pass

    def validate_content(self, content: str, media_type: str = 'none') -> Dict[str, Any]:
        """
        Validate post content before publishing.
        Override in subclass for platform-specific rules.

        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []

        if not content and media_type == 'none':
            errors.append("Content is required for text posts")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def get_rate_limit_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get current rate limit status.
        Override in subclass if platform supports this.

        Returns:
            Dict with rate limit information
        """
        return {
            'supported': False,
            'message': 'Rate limit info not available for this platform'
        }
