"""
AI App Admin Configuration
"""
from django.contrib import admin
from .models import PostingSchedule, ScheduledContent


@admin.register(PostingSchedule)
class PostingScheduleAdmin(admin.ModelAdmin):
    list_display = ['business_type', 'start_date', 'duration', 'total_posts', 'user', 'created_at']
    list_filter = ['duration', 'start_date', 'created_at']
    search_fields = ['business_type', 'goals']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Schedule Info', {
            'fields': ('user', 'business_type', 'goals', 'start_date', 'duration', 'posts_per_day', 'total_posts')
        }),
        ('AI Strategy', {
            'fields': ('strategy_overview', 'hashtag_suggestions', 'engagement_tips')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ScheduledContent)
class ScheduledContentAdmin(admin.ModelAdmin):
    list_display = ['schedule_date', 'schedule_time', 'title', 'content_type', 'status', 'user']
    list_filter = ['status', 'content_type', 'goal', 'schedule_date']
    search_fields = ['title', 'hook', 'body', 'business_type']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Schedule Info', {
            'fields': ('user', 'business_type', 'schedule_date', 'schedule_time', 'day_of_week')
        }),
        ('Content Classification', {
            'fields': ('content_type', 'title', 'goal', 'media_type')
        }),
        ('Content Sections', {
            'fields': ('hook', 'body', 'engagement', 'cta', 'hashtags')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
