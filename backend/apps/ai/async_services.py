"""
Async AI Services - Background task execution for AI operations
"""
import asyncio
import threading
from typing import Optional, Dict, Any, List
from asgiref.sync import sync_to_async
from django.utils import timezone
from .services import AIContentService, AIImageService
from .task_manager import TaskManager
from .models import AsyncAITask


class AsyncAIService:
    """
    Service for running AI generation tasks in background
    """

    @staticmethod
    def _run_async_in_thread(coro):
        """
        Run an async coroutine in a background thread with its own event loop
        This is needed because Django WSGI doesn't have an event loop
        """
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

    @staticmethod
    async def _save_task_to_db(task_id: str, user, task_type: str, input_params: dict):
        """Save task to database"""
        @sync_to_async
        def create_task():
            return AsyncAITask.objects.create(
                task_id=task_id,
                user=user,
                task_type=task_type,
                input_params=input_params,
                status='pending'
            )
        return await create_task()

    @staticmethod
    async def _update_db_task(task_id: str, **updates):
        """Update task in database"""
        @sync_to_async
        def update_task():
            try:
                task = AsyncAITask.objects.get(task_id=task_id)
                for key, value in updates.items():
                    setattr(task, key, value)
                task.save()
                return True
            except AsyncAITask.DoesNotExist:
                return False
        return await update_task()

    @staticmethod
    async def generate_content_async(
        task_id: str,
        user,
        prompt: str,
        tone: str = 'professional',
        include_hashtags: bool = True,
        include_emoji: bool = True,
        language: str = 'vi'
    ):
        """
        Run content generation in background

        Args:
            task_id: Task identifier from TaskManager
            user: User instance
            prompt: Content prompt
            tone: Content tone
            include_hashtags: Include hashtags flag
            include_emoji: Include emoji flag
            language: Language code
        """
        db_task = None
        start_time = timezone.now()

        try:
            # Save task to database
            db_task = await AsyncAIService._save_task_to_db(
                task_id, user, 'content',
                {
                    'prompt': prompt,
                    'tone': tone,
                    'include_hashtags': include_hashtags,
                    'include_emoji': include_emoji,
                    'language': language
                }
            )

            # Mark as started in both Redis and DB
            TaskManager.mark_started(task_id)
            if db_task:
                await sync_to_async(db_task.mark_started)()

            # Update progress
            TaskManager.update_progress(task_id, 20)

            # Run AI generation in thread pool (sync function)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                AIContentService.generate_content,
                prompt,
                tone,
                include_hashtags,
                include_emoji,
                language
            )

            # Update progress
            TaskManager.update_progress(task_id, 90)

            # Mark as completed
            TaskManager.mark_completed(task_id, result)
            if db_task:
                await sync_to_async(db_task.mark_completed)(result)

            # Calculate duration
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            # Update duration in database
            await AsyncAIService._update_db_task(
                task_id,
                duration_seconds=duration
            )

        except Exception as e:
            error_msg = str(e)
            TaskManager.mark_failed(task_id, error_msg)
            if db_task:
                await sync_to_async(db_task.mark_failed)(error_msg)

            # Still record duration even on failure
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            await AsyncAIService._update_db_task(
                task_id,
                duration_seconds=duration
            )

    @staticmethod
    async def generate_image_async(
        task_id: str,
        user,
        prompt: str,
        size: str,
        creativity: str,
        reference_image_paths: List[str] = None
    ):
        """
        Run image generation in background

        Args:
            task_id: Task identifier from TaskManager
            user: User instance
            prompt: Image prompt
            size: Image size
            creativity: Creativity level
            reference_image_paths: List of reference image paths
        """
        db_task = None
        start_time = timezone.now()

        try:
            # Save task to database
            db_task = await AsyncAIService._save_task_to_db(
                task_id, user, 'image',
                {
                    'prompt': prompt,
                    'size': size,
                    'creativity': creativity,
                    'has_references': bool(reference_image_paths)
                }
            )

            # Mark as started
            TaskManager.mark_started(task_id)
            if db_task:
                await sync_to_async(db_task.mark_started)()

            # Update progress
            TaskManager.update_progress(task_id, 10)

            # Run AI image generation in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                AIImageService.generate_image,
                prompt,
                user,
                size,
                creativity,
                reference_image_paths
            )

            # Update progress
            TaskManager.update_progress(task_id, 80)

            # Create media record if needed
            if result and 'file_url' in result:
                # Import here to avoid circular dependency
                from apps.media.services import MediaService

                file_info = {
                    'file_path': result['file_path'],
                    'file_url': result['file_url'],
                    'file_size': result['file_size'],
                    'width': result['width'],
                    'height': result['height'],
                }

                # Create media record
                media = await loop.run_in_executor(
                    None,
                    MediaService.create_media_record,
                    user,
                    file_info,
                    'image',
                    None  # folder
                )

                # Add media info to result
                result['media_id'] = media.id

            TaskManager.update_progress(task_id, 95)

            # Mark as completed
            TaskManager.mark_completed(task_id, result)
            if db_task:
                await sync_to_async(db_task.mark_completed)(result)

            # Calculate duration
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            # Update duration in database
            await AsyncAIService._update_db_task(
                task_id,
                duration_seconds=duration
            )

            # Cleanup reference images
            if reference_image_paths:
                await loop.run_in_executor(
                    None,
                    AIImageService.cleanup_reference_images,
                    reference_image_paths
                )

        except Exception as e:
            error_msg = str(e)
            TaskManager.mark_failed(task_id, error_msg)
            if db_task:
                await sync_to_async(db_task.mark_failed)(error_msg)

            # Still record duration even on failure
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            await AsyncAIService._update_db_task(
                task_id,
                duration_seconds=duration
            )

            # Cleanup reference images even on failure
            if reference_image_paths:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    AIImageService.cleanup_reference_images,
                    reference_image_paths
                )

    @staticmethod
    async def generate_schedule_async(
        task_id: str,
        user,
        business_type: str,
        goals: str,
        start_date: str,
        duration: str = '1_week',
        posts_per_day: int = 2,
        language: str = 'vi'
    ):
        """
        Run schedule generation in background

        Args:
            task_id: Task identifier from TaskManager
            user: User instance
            business_type: Business type
            goals: Marketing goals
            start_date: Start date
            duration: Schedule duration
            posts_per_day: Posts per day
            language: Language code
        """
        db_task = None
        start_time = timezone.now()

        try:
            # Save task to database
            db_task = await AsyncAIService._save_task_to_db(
                task_id, user, 'schedule',
                {
                    'business_type': business_type,
                    'goals': goals,
                    'start_date': start_date,
                    'duration': duration,
                    'posts_per_day': posts_per_day,
                    'language': language
                }
            )

            # Mark as started
            TaskManager.mark_started(task_id)
            if db_task:
                await sync_to_async(db_task.mark_started)()

            # Update progress
            TaskManager.update_progress(task_id, 15)

            # Run AI schedule generation in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                AIContentService.generate_posting_schedule,
                business_type,
                goals,
                start_date,
                duration,
                posts_per_day,
                language
            )

            # Update progress
            TaskManager.update_progress(task_id, 90)

            # Mark as completed
            TaskManager.mark_completed(task_id, result)
            if db_task:
                await sync_to_async(db_task.mark_completed)(result)

            # Calculate duration
            end_time = timezone.now()
            duration_seconds = (end_time - start_time).total_seconds()

            # Update duration in database
            await AsyncAIService._update_db_task(
                task_id,
                duration_seconds=duration_seconds
            )

        except Exception as e:
            error_msg = str(e)
            TaskManager.mark_failed(task_id, error_msg)
            if db_task:
                await sync_to_async(db_task.mark_failed)(error_msg)

            # Still record duration even on failure
            end_time = timezone.now()
            duration_seconds = (end_time - start_time).total_seconds()
            await AsyncAIService._update_db_task(
                task_id,
                duration_seconds=duration_seconds
            )

    @staticmethod
    def submit_content_task(user, **kwargs) -> str:
        """
        Submit content generation task

        Returns:
            task_id: Task identifier for status polling
        """
        # Create task in Redis
        task_id = TaskManager.create_task(
            user_id=user.id,
            task_type='content',
            input_params=kwargs
        )

        # Start async task in background thread
        AsyncAIService._run_async_in_thread(
            AsyncAIService.generate_content_async(task_id, user, **kwargs)
        )

        return task_id

    @staticmethod
    def submit_image_task(user, **kwargs) -> str:
        """
        Submit image generation task

        Returns:
            task_id: Task identifier for status polling
        """
        # Create task in Redis
        task_id = TaskManager.create_task(
            user_id=user.id,
            task_type='image',
            input_params=kwargs
        )

        # Start async task in background thread
        AsyncAIService._run_async_in_thread(
            AsyncAIService.generate_image_async(task_id, user, **kwargs)
        )

        return task_id

    @staticmethod
    def submit_schedule_task(user, **kwargs) -> str:
        """
        Submit schedule generation task

        Returns:
            task_id: Task identifier for status polling
        """
        # Create task in Redis
        task_id = TaskManager.create_task(
            user_id=user.id,
            task_type='schedule',
            input_params=kwargs
        )

        # Start async task in background thread
        AsyncAIService._run_async_in_thread(
            AsyncAIService.generate_schedule_async(task_id, user, **kwargs)
        )

        return task_id
