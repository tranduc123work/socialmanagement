"""
Media Service for Local File Storage (On-Premise)
"""
import os
import uuid
from pathlib import Path
from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError


class MediaService:
    """Service for handling local file storage operations"""

    @staticmethod
    def validate_file(file: UploadedFile, file_type: str = 'image'):
        """
        Validate uploaded file for size and type

        Args:
            file: Django UploadedFile object
            file_type: 'image' or 'video'

        Raises:
            ValidationError: If file is invalid
        """
        # Check file size
        if file.size > settings.MAX_UPLOAD_SIZE:
            max_size_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            raise ValidationError(
                f"File size exceeds maximum allowed size of {max_size_mb}MB"
            )

        # Check file type
        if file_type == 'image':
            if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
                raise ValidationError(
                    f"Invalid image type. Allowed types: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
                )
        elif file_type == 'video':
            if file.content_type not in settings.ALLOWED_VIDEO_TYPES:
                raise ValidationError(
                    f"Invalid video type. Allowed types: {', '.join(settings.ALLOWED_VIDEO_TYPES)}"
                )
        else:
            raise ValidationError("Invalid file_type. Must be 'image' or 'video'")

    @staticmethod
    def save_file(file: UploadedFile, user, file_type: str = 'image') -> dict:
        """
        Save file to local storage

        Args:
            file: Django UploadedFile object
            user: User instance
            file_type: 'image' or 'video'

        Returns:
            dict: File information including url, path, size, dimensions
        """
        # Validate file first
        MediaService.validate_file(file, file_type)

        # Generate unique filename
        ext = Path(file.name).suffix
        filename = f"{uuid.uuid4()}{ext}"

        # Create user directory
        user_dir = Path(settings.MEDIA_ROOT) / 'uploads' / str(user.id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = user_dir / filename
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Get image dimensions if it's an image
        width = None
        height = None
        if file_type == 'image':
            try:
                with Image.open(file_path) as img:
                    width, height = img.size

                    # Auto-resize if image is too large
                    if width > 1200 or height > 1200:
                        MediaService.resize_image(str(file_path))
                        with Image.open(file_path) as resized_img:
                            width, height = resized_img.size
            except Exception as e:
                # If image processing fails, delete file and raise error
                os.remove(file_path)
                raise ValidationError(f"Invalid image file: {str(e)}")

        # Return file information
        return {
            'file_url': f"/media/uploads/{user.id}/{filename}",
            'file_path': str(file_path),
            'file_size': file.size,
            'width': width,
            'height': height,
            'filename': filename,
        }

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Delete file from local storage

        Args:
            file_path: Absolute path to file

        Returns:
            bool: True if deleted successfully
        """
        try:
            file_path_obj = Path(file_path)
            if file_path_obj.exists() and file_path_obj.is_file():
                os.remove(file_path_obj)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    @staticmethod
    def resize_image(file_path: str, max_width: int = 1200, max_height: int = 1200):
        """
        Resize image to maximum dimensions while maintaining aspect ratio

        Args:
            file_path: Absolute path to image file
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
        """
        try:
            with Image.open(file_path) as img:
                # Convert RGBA to RGB if necessary
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    img = rgb_img

                # Resize maintaining aspect ratio
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                # Save with optimization
                img.save(file_path, quality=85, optimize=True)
        except Exception as e:
            print(f"Error resizing image: {e}")
            raise

    @staticmethod
    def create_thumbnail(file_path: str, size: tuple = (300, 300)) -> str:
        """
        Create thumbnail for an image

        Args:
            file_path: Absolute path to image file
            size: Thumbnail size as (width, height)

        Returns:
            str: Path to thumbnail file
        """
        try:
            thumb_path = file_path.replace(Path(file_path).suffix, f'_thumb{Path(file_path).suffix}')

            with Image.open(file_path) as img:
                # Convert RGBA to RGB if necessary
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    img = rgb_img

                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumb_path, quality=70, optimize=True)

            return thumb_path
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return file_path

    @staticmethod
    def create_media_record(user, file_info: dict, file_type: str, folder=None):
        """
        Create database record for uploaded media

        Args:
            user: User instance
            file_info: Dictionary from save_file() method
            file_type: 'image' or 'video'
            folder: Optional MediaFolder instance

        Returns:
            Media: Created media instance
        """
        from .models import Media

        media = Media.objects.create(
            user=user,
            file_url=file_info['file_url'],
            file_path=file_info['file_path'],
            file_type=file_type,
            file_size=file_info['file_size'],
            width=file_info.get('width'),
            height=file_info.get('height'),
            folder=folder,
        )

        return media

    @staticmethod
    def get_user_media_stats(user) -> dict:
        """
        Get storage statistics for a user

        Args:
            user: User instance

        Returns:
            dict: Storage statistics
        """
        from .models import Media

        user_media = Media.objects.filter(user=user)
        total_size = sum(m.file_size for m in user_media)

        return {
            'total_files': user_media.count(),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'images_count': user_media.filter(file_type='image').count(),
            'videos_count': user_media.filter(file_type='video').count(),
        }

    @staticmethod
    def cleanup_orphaned_files(user):
        """
        Delete files that exist on disk but not in database

        Args:
            user: User instance

        Returns:
            int: Number of files deleted
        """
        from .models import Media

        user_dir = Path(settings.MEDIA_ROOT) / 'uploads' / str(user.id)
        if not user_dir.exists():
            return 0

        # Get all files in database
        db_files = set(Media.objects.filter(user=user).values_list('file_path', flat=True))

        # Get all files on disk
        disk_files = list(user_dir.glob('*'))

        deleted_count = 0
        for file_path in disk_files:
            if str(file_path) not in db_files:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting orphaned file {file_path}: {e}")

        return deleted_count
