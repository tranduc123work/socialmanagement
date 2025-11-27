from django.db import models


class FacebookPage(models.Model):
    user = models.ForeignKey('custom_auth.User', on_delete=models.CASCADE, related_name='facebook_pages')
    facebook_page_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    access_token = models.TextField()
    picture_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'facebook_pages'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
