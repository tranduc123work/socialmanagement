"""
Agent Admin Configuration
"""
from django.contrib import admin
from .models import AgentPost, AgentConversation, AgentTask


@admin.register(AgentPost)
class AgentPostAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['content', 'user__username']
    readonly_fields = ['created_at', 'completed_at']


@admin.register(AgentConversation)
class AgentConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'role', 'message_preview', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['message', 'user__username']

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'task_type', 'status', 'progress', 'created_at']
    list_filter = ['task_type', 'status', 'created_at']
    search_fields = ['description', 'user__username']
