"""
Facebook API Models
"""
from django.db import models
from apps.auth.models import User


class FacebookAPILog(models.Model):
    """Log all Facebook API calls"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='facebook_logs')
    endpoint = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    request_data = models.JSONField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    status_code = models.IntegerField(null=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facebook_api_logs'
        ordering = ['-created_at']
