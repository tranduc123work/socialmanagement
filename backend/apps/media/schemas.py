from ninja import Schema
from typing import Optional
from datetime import datetime


class MediaSchema(Schema):
    """Schema for media file response"""
    id: int
    file_url: str
    file_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    folder_id: Optional[int] = None
    folder_name: Optional[str] = None
    created_at: datetime

    @staticmethod
    def resolve_folder_name(obj):
        # Explicitly handle folder name resolution
        if hasattr(obj, 'folder') and obj.folder is not None:
            return obj.folder.name
        return None

    class Config:
        from_attributes = True


class MediaUploadResponseSchema(Schema):
    """Schema for media upload response"""
    id: int
    file_url: str
    file_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime
    message: str


class MediaFolderSchema(Schema):
    """Schema for media folder"""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    media_count: int


class MediaFolderCreateSchema(Schema):
    """Schema for creating media folder"""
    name: str
    description: Optional[str] = None


class MediaStatsSchema(Schema):
    """Schema for media storage statistics"""
    total_files: int
    total_size: int
    total_size_mb: float
    images_count: int
    videos_count: int


class AIImageGenerateSchema(Schema):
    """Schema for AI image generation request"""
    prompt: str
    size: str = "1080x1080"
    creativity: str = "medium"
