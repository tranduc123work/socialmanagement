from django.contrib import admin
from .models import FacebookPage


@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'facebook_page_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'facebook_page_id', 'user__email']
    ordering = ['-created_at']
