from ninja import Router, File, Form
from ninja.files import UploadedFile
from typing import Optional, List
from api.dependencies import AuthBearer
from .services import MediaService
from .schemas import MediaSchema, MediaUploadResponseSchema
from django.http import Http404

router = Router()


@router.get("/", auth=AuthBearer(), response=list[MediaSchema])
def list_media(request, folder_id: Optional[int] = None):
    """List all media files for authenticated user"""
    from .models import Media

    queryset = Media.objects.filter(user=request.auth)

    if folder_id:
        queryset = queryset.filter(folder_id=folder_id)

    return queryset.order_by('-created_at')


@router.post("/upload", auth=AuthBearer(), response=MediaUploadResponseSchema)
def upload_media(
    request,
    file: UploadedFile = File(...),
    file_type: str = Form(...),
    folder_id: Optional[int] = Form(None),
):
    """
    Upload a file (image or video) to local storage

    Args:
        file: The file to upload
        file_type: Type of file ('image' or 'video')
        folder_id: Optional folder ID to organize media

    Returns:
        MediaUploadResponseSchema: Uploaded media information
    """
    from .models import MediaFolder

    # Get folder if specified
    folder = None
    if folder_id:
        try:
            folder = MediaFolder.objects.get(id=folder_id, user=request.auth)
        except MediaFolder.DoesNotExist:
            raise Http404("Folder not found")

    # Save file to local storage
    file_info = MediaService.save_file(
        file=file,
        user=request.auth,
        file_type=file_type
    )

    # Create database record
    media = MediaService.create_media_record(
        user=request.auth,
        file_info=file_info,
        file_type=file_type,
        folder=folder
    )

    # Build absolute URL for external services (Facebook, Instagram, etc.)
    absolute_url = request.build_absolute_uri(media.file_url)

    return {
        "id": media.id,
        "file_url": absolute_url,  # Return absolute URL for external APIs
        "file_type": media.file_type,
        "file_size": media.file_size,
        "width": media.width,
        "height": media.height,
        "created_at": media.created_at,
        "message": "File uploaded successfully"
    }


@router.get("/{media_id}", auth=AuthBearer(), response=MediaSchema)
def get_media(request, media_id: int):
    """Get specific media file details"""
    from .models import Media

    try:
        media = Media.objects.get(id=media_id, user=request.auth)
        return media
    except Media.DoesNotExist:
        raise Http404("Media not found")


@router.delete("/{media_id}", auth=AuthBearer())
def delete_media(request, media_id: int):
    """Delete media file from storage and database"""
    from .models import Media

    try:
        media = Media.objects.get(id=media_id, user=request.auth)

        # Delete file from storage
        MediaService.delete_file(media.file_path)

        # Delete database record
        media.delete()

        return {"message": "Media deleted successfully", "success": True}
    except Media.DoesNotExist:
        raise Http404("Media not found")


@router.get("/stats/storage", auth=AuthBearer())
def get_storage_stats(request):
    """Get user's storage statistics"""
    stats = MediaService.get_user_media_stats(request.auth)
    return stats


@router.post("/cleanup/orphaned", auth=AuthBearer())
def cleanup_orphaned_files(request):
    """Clean up orphaned files (files on disk but not in database)"""
    deleted_count = MediaService.cleanup_orphaned_files(request.auth)
    return {
        "message": f"Cleaned up {deleted_count} orphaned files",
        "deleted_count": deleted_count
    }


@router.get("/list-test", response=list[MediaSchema])
def list_media_test(request, folder: Optional[str] = None):
    """
    List all media files (TEST MODE - no auth required)
    For development purposes only
    """
    from .models import Media, MediaFolder

    queryset = Media.objects.all()

    if folder and folder != 'Tất cả':
        # Filter by folder name
        folder_obj = MediaFolder.objects.filter(name=folder).first()
        if folder_obj:
            queryset = queryset.filter(folder=folder_obj)

    return queryset.order_by('-created_at')
