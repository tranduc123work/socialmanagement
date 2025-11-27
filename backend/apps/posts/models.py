"""
Posts Models
"""
from django.db import models
from django.utils import timezone


class Post(models.Model):
    """Post Model"""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    POST_TYPES = [
        ('text', 'Text Only'),
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('carousel', 'Carousel'),
        ('link', 'Link'),
    ]

    # Basic info
    created_by = models.ForeignKey('custom_auth.User', on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255, blank=True)

    # Content
    content = models.TextField()
    original_content = models.TextField(blank=True, help_text="Original content before AI rewrite")
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='text')

    # Media
    media_urls = models.JSONField(default=list, blank=True, help_text="List of media URLs")
    link_url = models.URLField(blank=True, null=True)

    # Hashtags and AI
    hashtags = models.JSONField(default=list, blank=True)
    ai_generated = models.BooleanField(default=False)
    ai_provider = models.CharField(max_length=50, blank=True)  # openai, gemini, claude

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # Facebook
    facebook_post_id = models.CharField(max_length=100, blank=True, null=True)
    facebook_pages = models.ManyToManyField('pages.FacebookPage', related_name='posts', blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'posts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['created_by', 'status']),
        ]

    def __str__(self):
        return f"{self.title or 'Post'} - {self.status}"

    def can_retry(self):
        """Check if post can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries


class PostVersion(models.Model):
    """Store post versions for AI rewrites"""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='versions')
    content = models.TextField()
    ai_provider = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'post_versions'
        ordering = ['-created_at']
