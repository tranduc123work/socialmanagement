"""
Auth Admin Configuration
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, RefreshToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'is_facebook_connected', 'is_staff', 'created_at']
    list_filter = ['is_facebook_connected', 'is_staff', 'is_active']
    search_fields = ['email', 'username', 'facebook_user_id']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'avatar')}),
        ('Facebook', {'fields': ('facebook_user_id', 'facebook_access_token', 'facebook_token_expires_at', 'is_facebook_connected')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'expires_at', 'is_revoked']
    list_filter = ['is_revoked', 'created_at']
    search_fields = ['user__email', 'token']
    ordering = ['-created_at']
