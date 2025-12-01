from django.contrib import admin
from .models import Media, MediaFolder, MediaTag


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'file_type', 'file_size', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['user__email', 'file_url']


@admin.register(MediaFolder)
class MediaFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'parent', 'created_at']


@admin.register(MediaTag)
class MediaTagAdmin(admin.ModelAdmin):
    list_display = ['name']
