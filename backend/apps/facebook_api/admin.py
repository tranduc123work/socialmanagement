from django.contrib import admin
from .models import FacebookAPILog


@admin.register(FacebookAPILog)
class FacebookAPILogAdmin(admin.ModelAdmin):
    list_display = ['user', 'endpoint', 'method', 'status_code', 'created_at']
    list_filter = ['method', 'status_code', 'created_at']
    search_fields = ['endpoint', 'user__email']
    ordering = ['-created_at']
