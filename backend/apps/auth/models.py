"""
Authentication Models
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Custom User Model"""

    email = models.EmailField(unique=True)
    facebook_user_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    facebook_access_token = models.TextField(blank=True, null=True)
    facebook_token_expires_at = models.DateTimeField(blank=True, null=True)
    avatar = models.URLField(blank=True, null=True)
    is_facebook_connected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Override to avoid reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    def is_token_valid(self):
        """Check if Facebook token is still valid"""
        if not self.facebook_token_expires_at:
            return False
        return self.facebook_token_expires_at > timezone.now()


class RefreshToken(models.Model):
    """JWT Refresh Token"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)

    class Meta:
        db_table = 'refresh_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"RefreshToken for {self.user.email}"

    def is_valid(self):
        """Check if token is still valid"""
        return not self.is_revoked and self.expires_at > timezone.now()
