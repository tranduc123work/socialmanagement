"""
Multi-Platform Social Media Models
Currently supports: Facebook Pages
Coming soon: Instagram, Zalo, TikTok, etc.
"""
from django.db import models
from django.utils import timezone


class PlatformType(models.TextChoices):
    """Supported social media platforms"""
    FACEBOOK = 'facebook', 'Facebook'
    # Coming soon:
    # INSTAGRAM = 'instagram', 'Instagram'
    # ZALO = 'zalo', 'Zalo'
    # TIKTOK = 'tiktok', 'TikTok'
    # YOUTUBE = 'youtube', 'YouTube'
    # TWITTER = 'twitter', 'Twitter/X'
    # THREADS = 'threads', 'Threads'


class SocialAccount(models.Model):
    """
    Represents a connected social media account/page
    Currently: Facebook Page
    Future: Instagram Business, Zalo OA, TikTok, etc.
    """
    user = models.ForeignKey(
        'custom_auth.User',
        on_delete=models.CASCADE,
        related_name='social_accounts'
    )

    # Platform info
    platform = models.CharField(
        max_length=20,
        choices=PlatformType.choices,
        default=PlatformType.FACEBOOK
    )

    # Account identifiers
    platform_account_id = models.CharField(
        max_length=100,
        help_text='ID of the account on the platform (page_id, ig_user_id, etc.)'
    )
    platform_user_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='User ID who owns this account (for Facebook user who owns page)'
    )

    # Account info
    name = models.CharField(max_length=500)
    username = models.CharField(max_length=255, blank=True)
    profile_picture_url = models.TextField(blank=True, null=True)  # No limit for long Facebook URLs
    category = models.CharField(max_length=255, blank=True)

    # Tokens
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # For Instagram linked to Facebook Page
    linked_facebook_page_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Facebook Page ID that Instagram is connected to'
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional platform-specific data'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'social_accounts'
        ordering = ['-created_at']
        unique_together = ['platform', 'platform_account_id']
        indexes = [
            models.Index(fields=['user', 'platform']),
            models.Index(fields=['platform', 'platform_account_id']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_platform_display()})"

    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expires_at:
            return False
        return timezone.now() >= self.token_expires_at

    def get_platform_icon(self):
        """Return icon name for frontend"""
        icons = {
            'facebook': 'Facebook',
            'instagram': 'Instagram',
            'zalo': 'MessageCircle',
            'tiktok': 'Music',
            'youtube': 'Youtube',
            'twitter': 'Twitter',
            'threads': 'AtSign',
        }
        return icons.get(self.platform, 'Globe')


class SocialPost(models.Model):
    """
    Represents a post that can be published to multiple platforms
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('publishing', 'Publishing'),
        ('published', 'Published'),
        ('partial', 'Partially Published'),
        ('failed', 'Failed'),
    ]

    # Owner
    created_by = models.ForeignKey(
        'custom_auth.User',
        on_delete=models.CASCADE,
        related_name='social_posts'
    )

    # Content
    content = models.TextField()
    title = models.CharField(max_length=255, blank=True)

    # Media
    media_urls = models.JSONField(default=list, blank=True)
    media_type = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Media'),
            ('image', 'Image'),
            ('video', 'Video'),
            ('carousel', 'Carousel'),
        ],
        default='none'
    )

    # Link
    link_url = models.URLField(blank=True, null=True)

    # Target accounts (many-to-many with status tracking)
    target_accounts = models.ManyToManyField(
        SocialAccount,
        through='PostPublishStatus',
        related_name='posts'
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # AI
    ai_generated = models.BooleanField(default=False)
    original_content = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'social_posts'
        ordering = ['-created_at']

    def __str__(self):
        return f"Post {self.id} - {self.status}"


class PostPublishStatus(models.Model):
    """
    Tracks publish status for each account a post is sent to
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('publishing', 'Publishing'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='publish_statuses')
    account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Platform-specific post ID after publishing
    platform_post_id = models.CharField(max_length=100, blank=True, null=True)
    platform_post_url = models.URLField(blank=True, null=True)

    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    # Timestamps
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'post_publish_status'
        unique_together = ['post', 'account']

    def __str__(self):
        return f"{self.post.id} -> {self.account.name}: {self.status}"


class PlatformWebhook(models.Model):
    """
    Store webhook events from platforms
    """
    platform = models.CharField(max_length=20, choices=PlatformType.choices)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'platform_webhooks'
        ordering = ['-created_at']
