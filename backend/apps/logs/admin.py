from django.contrib import admin
from .models import APILog


@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'method', 'status_code', 'user', 'created_at']
    list_filter = ['method', 'status_code', 'created_at']
    search_fields = ['endpoint', 'user__email', 'error_message']
    ordering = ['-created_at']
