"""
Task Manager for Async AI Tasks
Handles task state management in Redis for real-time updates
Falls back to database-only mode if Redis is unavailable
"""
import json
import uuid
import logging
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Manages async task state in Redis cache (optional)
    Provides fast access to task status without hitting database
    Falls back gracefully if Redis is not available
    """

    TASK_PREFIX = "ai_task:"
    TASK_EXPIRY = 86400  # 24 hours in seconds
    REDIS_AVAILABLE = True  # Track Redis availability

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
        Create new task (optionally in Redis)

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

        # Try to cache in Redis, but don't fail if Redis is unavailable
        try:
            cache_key = cls._get_cache_key(task_id)
            cache.set(cache_key, json.dumps(task_data), timeout=cls.TASK_EXPIRY)
        except Exception as e:
            logger.warning(f"Redis unavailable, operating in database-only mode: {e}")
            cls.REDIS_AVAILABLE = False

        return task_id

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task data from Redis (if available)

        Args:
            task_id: Task identifier

        Returns:
            Task data dictionary or None if not found
        """
        try:
            cache_key = cls._get_cache_key(task_id)
            task_json = cache.get(cache_key)

            if task_json:
                return json.loads(task_json)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            cls.REDIS_AVAILABLE = False

        return None

    @classmethod
    def update_task(cls, task_id: str, **updates) -> bool:
        """
        Update task data in Redis (if available)

        Args:
            task_id: Task identifier
            **updates: Fields to update

        Returns:
            True if updated, False if task not found or Redis unavailable
        """
        try:
            task_data = cls.get_task(task_id)
            if not task_data:
                return False

            # Update fields
            for key, value in updates.items():
                if key in task_data:
                    task_data[key] = value

            # Save back to Redis
            cache_key = cls._get_cache_key(task_id)
            cache.set(cache_key, json.dumps(task_data), timeout=cls.TASK_EXPIRY)
            return True
        except Exception as e:
            logger.warning(f"Redis update failed: {e}")
            cls.REDIS_AVAILABLE = False
            return False

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
        Delete task from Redis (if available)

        Args:
            task_id: Task identifier

        Returns:
            True if deleted successfully
        """
        try:
            cache_key = cls._get_cache_key(task_id)
            cache.delete(cache_key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            cls.REDIS_AVAILABLE = False
            return False

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
