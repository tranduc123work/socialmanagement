"""
Task Manager for Async AI Tasks
Handles task state management in Redis for real-time updates
Falls back to database-only mode if Redis is unavailable or disabled
"""
import os
import json
import uuid
import logging
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


def _is_redis_enabled() -> bool:
    """Check if Redis is enabled via environment variable"""
    redis_enabled = os.environ.get('REDIS_ENABLED', 'false').lower()
    enabled = redis_enabled in ('true', '1', 'yes')
    if enabled:
        logger.info("[TaskManager] Redis caching is ENABLED")
    else:
        logger.info("[TaskManager] Redis caching is DISABLED, using database-only mode")
    return enabled


class TaskManager:
    """
    Manages async task state in Redis cache (optional)
    Provides fast access to task status without hitting database
    Falls back gracefully if Redis is not available or disabled

    Set REDIS_ENABLED=true in .env to enable Redis caching
    """

    TASK_PREFIX = "ai_task:"
    TASK_EXPIRY = 86400  # 24 hours in seconds
    REDIS_ENABLED = _is_redis_enabled()  # Check env on startup

    @staticmethod
    def generate_task_id() -> str:
        """Generate unique task ID"""
        return str(uuid.uuid4())

    @staticmethod
    def _get_cache_key(task_id: str) -> str:
        """Get Redis cache key for task"""
        return f"{TaskManager.TASK_PREFIX}{task_id}"

    @classmethod
    def create_task(
        cls,
        user_id: int,
        task_type: str,
        input_params: Dict[str, Any]
    ) -> str:
        """
        Create new task in both Redis (if available) and database

        Args:
            user_id: User ID who created the task
            task_type: Type of task (content, image, schedule)
            input_params: Task input parameters

        Returns:
            task_id: Unique task identifier
        """
        task_id = cls.generate_task_id()

        task_data = {
            'task_id': task_id,
            'user_id': user_id,
            'task_type': task_type,
            'input_params': input_params,
            'status': 'pending',
            'progress': 0,
            'result': None,
            'error_message': None,
            'created_at': timezone.now().isoformat(),
            'started_at': None,
            'completed_at': None,
        }

        # Try to cache in Redis if enabled
        if cls.REDIS_ENABLED:
            try:
                cache_key = cls._get_cache_key(task_id)
                cache.set(cache_key, json.dumps(task_data), timeout=cls.TASK_EXPIRY)
            except Exception as e:
                logger.warning(f"Redis unavailable: {e}")
                cls.REDIS_ENABLED = False  # Disable Redis for this session

        # Always save to database as permanent storage
        try:
            from .models import AsyncAITask
            from apps.auth.models import User
            user = User.objects.get(id=user_id)
            AsyncAITask.objects.create(
                task_id=task_id,
                user=user,
                task_type=task_type,
                input_params=input_params,
                status='pending',
                progress=0
            )
        except Exception as e:
            # Ignore async context errors
            if "async context" not in str(e).lower():
                logger.error(f"Database create failed: {e}")

        return task_id

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task data from Redis (if available), fallback to database

        Args:
            task_id: Task identifier

        Returns:
            Task data dictionary or None if not found
        """
        # Try Redis first if enabled
        if cls.REDIS_ENABLED:
            try:
                cache_key = cls._get_cache_key(task_id)
                task_json = cache.get(cache_key)

                if task_json:
                    return json.loads(task_json)
            except Exception as e:
                logger.warning(f"Redis get failed, falling back to database: {e}")
                cls.REDIS_ENABLED = False  # Disable Redis for this session

        # Fallback to database
        try:
            from .models import AsyncAITask
            task = AsyncAITask.objects.filter(task_id=task_id).first()
            if task:
                return {
                    'task_id': task.task_id,
                    'user_id': task.user_id,
                    'task_type': task.task_type,
                    'input_params': task.input_params,
                    'status': task.status,
                    'progress': task.progress,
                    'result': task.result,
                    'error_message': task.error_message,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                }
        except Exception as e:
            # Ignore async context errors
            if "async context" not in str(e).lower():
                logger.error(f"Database get failed: {e}")

        return None

    @classmethod
    def update_task(cls, task_id: str, **updates) -> bool:
        """
        Update task data in Redis (if available), fallback to database

        Args:
            task_id: Task identifier
            **updates: Fields to update

        Returns:
            True if updated, False if task not found
        """
        updated_redis = False
        updated_db = False

        # Try Redis first if enabled
        if cls.REDIS_ENABLED:
            try:
                cache_key = cls._get_cache_key(task_id)
                task_json = cache.get(cache_key)

                if task_json:
                    task_data = json.loads(task_json)
                    # Update fields
                    for key, value in updates.items():
                        if key in task_data:
                            task_data[key] = value

                    # Save back to Redis
                    cache.set(cache_key, json.dumps(task_data), timeout=cls.TASK_EXPIRY)
                    updated_redis = True
            except Exception as e:
                logger.warning(f"Redis update failed: {e}")
                cls.REDIS_ENABLED = False  # Disable Redis for this session

        # Always try to update database as backup
        try:
            from .models import AsyncAITask
            task = AsyncAITask.objects.filter(task_id=task_id).first()
            if task:
                # Map updates to model fields
                update_fields = []
                if 'status' in updates:
                    task.status = updates['status']
                    update_fields.append('status')
                if 'progress' in updates:
                    task.progress = updates['progress']
                    update_fields.append('progress')
                if 'result' in updates:
                    task.result = updates['result']
                    update_fields.append('result')
                if 'error_message' in updates:
                    task.error_message = updates['error_message']
                    update_fields.append('error_message')
                if 'started_at' in updates:
                    from django.utils import timezone
                    task.started_at = timezone.now()
                    update_fields.append('started_at')
                if 'completed_at' in updates:
                    from django.utils import timezone
                    task.completed_at = timezone.now()
                    # Calculate duration
                    if task.started_at:
                        task.duration_seconds = (task.completed_at - task.started_at).total_seconds()
                        update_fields.append('duration_seconds')
                    update_fields.append('completed_at')

                if update_fields:
                    task.save(update_fields=update_fields)
                    updated_db = True
        except Exception as e:
            # Ignore async context errors - these happen when called from polling endpoints
            if "async context" not in str(e).lower():
                logger.error(f"Database update failed: {e}")

        return updated_redis or updated_db

    @classmethod
    def mark_started(cls, task_id: str) -> bool:
        """Mark task as started"""
        return cls.update_task(
            task_id,
            status='processing',
            started_at=timezone.now().isoformat()
        )

    @classmethod
    def mark_completed(cls, task_id: str, result: Any) -> bool:
        """Mark task as completed with result"""
        return cls.update_task(
            task_id,
            status='completed',
            result=result,
            progress=100,
            completed_at=timezone.now().isoformat()
        )

    @classmethod
    def mark_failed(cls, task_id: str, error_message: str) -> bool:
        """Mark task as failed with error message"""
        return cls.update_task(
            task_id,
            status='failed',
            error_message=error_message,
            completed_at=timezone.now().isoformat()
        )

    @classmethod
    def update_progress(cls, task_id: str, progress: int) -> bool:
        """
        Update task progress percentage

        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)

        Returns:
            True if updated successfully
        """
        progress = min(100, max(0, progress))
        return cls.update_task(task_id, progress=progress)

    @classmethod
    def delete_task(cls, task_id: str) -> bool:
        """
        Delete task from Redis (if enabled) and database

        Args:
            task_id: Task identifier

        Returns:
            True if deleted successfully
        """
        deleted = False

        # Try Redis if enabled
        if cls.REDIS_ENABLED:
            try:
                cache_key = cls._get_cache_key(task_id)
                cache.delete(cache_key)
                deleted = True
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
                cls.REDIS_ENABLED = False

        # Also delete from database
        try:
            from .models import AsyncAITask
            AsyncAITask.objects.filter(task_id=task_id).delete()
            deleted = True
        except Exception as e:
            # Ignore async context errors
            if "async context" not in str(e).lower():
                logger.error(f"Database delete failed: {e}")

        return deleted

    @classmethod
    def get_user_tasks(cls, user_id: int, status: Optional[str] = None) -> list:
        """
        Get all tasks for a user (Note: This requires iterating cache keys)
        For production use, consider maintaining a separate user task index

        Args:
            user_id: User identifier
            status: Optional status filter

        Returns:
            List of task data dictionaries
        """
        # Note: This is a simplified implementation
        # For production, maintain a separate index of user tasks
        # using Redis sets or sorted sets for better performance

        # This is a placeholder - actual implementation would need
        # to track user tasks separately
        return []
