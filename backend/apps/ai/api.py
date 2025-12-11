"""
AI Content Generation API Endpoints
"""
from typing import List, Optional
import json
from ninja import Router, Form, Schema, File, UploadedFile
from django.http import StreamingHttpResponse
from api.main import AuthBearer
from .services import AIContentService, AIImageService
from .async_services import AsyncAIService
from .task_manager import TaskManager
from .models import PostingSchedule, ScheduledContent, AsyncAITask
from datetime import datetime
from django.db.models import Avg, Count, Sum

router = Router()


# ============ Schemas ============

class SaveScheduleRequest(Schema):
    posts: List[dict]
    business_type: str
    goals: str = ""
    start_date: str
    duration: str
    posts_per_day: int = 2
    strategy_overview: str = ""
    hashtag_suggestions: List[str] = []
    engagement_tips: str = ""


class PostingScheduleResponse(Schema):
    id: int
    business_type: str
    goals: str
    start_date: str
    duration: str
    posts_per_day: int
    total_posts: int
    strategy_overview: str
    hashtag_suggestions: List[str]
    engagement_tips: str
    created_at: str
    posts_count: int


class ScheduledPostResponse(Schema):
    id: int
    schedule_id: Optional[int] = None
    business_type: str
    schedule_date: str
    schedule_time: str
    day_of_week: str
    content_type: str
    title: str
    goal: str
    hook: str
    body: str
    engagement: str
    cta: str
    hashtags: List[str]
    media_type: str
    status: str
    created_at: str
    full_content: str


class AIImageGenerateSchema(Schema):
    id: int
    file_url: str
    file_type: str
    file_size: int
    width: int
    height: int
    created_at: str
    message: str


class TaskSubmitResponse(Schema):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(Schema):
    task_id: str
    task_type: str
    status: str
    progress: int
    result: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None


class TaskStatsResponse(Schema):
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    avg_duration_content: Optional[float] = None
    avg_duration_image: Optional[float] = None
    avg_duration_schedule: Optional[float] = None
    recent_tasks: List[dict]


# ============ AI Content Generation Endpoints ============

@router.post("/generate", auth=AuthBearer())
def generate_ai_content(
    request,
    prompt: str = Form(...),
    tone: str = Form("professional"),
    include_hashtags: bool = Form(True),
    include_emoji: bool = Form(True),
    language: str = Form("vi")
):
    """
    Generate post content using AI

    Args:
        prompt: Description of the content to generate
        tone: Tone of content ('professional', 'casual', 'funny', 'formal')
        include_hashtags: Whether to include hashtags
        include_emoji: Whether to include emojis
        language: Language code ('vi' or 'en')

    Returns:
        Generated content
    """
    result = AIContentService.generate_content(
        prompt=prompt,
        tone=tone,
        include_hashtags=include_hashtags,
        include_emoji=include_emoji,
        language=language
    )
    return result


@router.post("/hashtags", auth=AuthBearer())
def generate_hashtags(
    request,
    content: str = Form(...),
    count: int = Form(5)
):
    """
    Generate relevant hashtags for content

    Args:
        content: Post content
        count: Number of hashtags to generate

    Returns:
        List of hashtags
    """
    result = AIContentService.generate_hashtags(
        content=content,
        count=count
    )
    return result


@router.post("/schedule", auth=AuthBearer())
def generate_posting_schedule(
    request,
    business_type: str = Form(...),
    goals: str = Form(...),
    start_date: str = Form(...),
    duration: str = Form("1_week"),
    posts_per_day: int = Form(2),
    language: str = Form("vi")
):
    """
    Generate a detailed posting schedule

    Args:
        business_type: Type of business/industry
        goals: Marketing goals
        start_date: Start date (YYYY-MM-DD)
        duration: Schedule duration ('1_week', '2_weeks', '1_month')
        posts_per_day: Number of posts per day
        language: Language code

    Returns:
        Detailed posting schedule
    """
    result = AIContentService.generate_posting_schedule(
        business_type=business_type,
        goals=goals,
        start_date=start_date,
        duration=duration,
        posts_per_day=posts_per_day,
        language=language
    )
    return result


# ============ Scheduled Content Management Endpoints ============

@router.post("/scheduled-posts/save", auth=AuthBearer())
def save_schedule_to_database(request, payload: SaveScheduleRequest):
    """
    Save AI-generated schedule to database

    Args:
        payload: Schedule data with posts array and business_type

    Returns:
        Saved scheduled posts with schedule_id
    """
    user = request.auth

    # Step 1: Create PostingSchedule
    try:
        start_date = datetime.strptime(payload.start_date, '%Y-%m-%d').date()
    except:
        start_date = datetime.now().date()

    posting_schedule = PostingSchedule.objects.create(
        user=user,
        business_type=payload.business_type,
        goals=payload.goals,
        start_date=start_date,
        duration=payload.duration,
        posts_per_day=payload.posts_per_day,
        total_posts=len(payload.posts),
        strategy_overview=payload.strategy_overview,
        hashtag_suggestions=payload.hashtag_suggestions,
        engagement_tips=payload.engagement_tips
    )

    # Step 2: Create all posts linked to this schedule
    saved_posts = []
    for post_data in payload.posts:
        try:
            # Parse date and time
            schedule_date = datetime.strptime(post_data['date'], '%Y-%m-%d').date()
            schedule_time = datetime.strptime(post_data['time'], '%H:%M').time()

            # Create ScheduledContent object with schedule link
            scheduled_post = ScheduledContent.objects.create(
                user=user,
                schedule=posting_schedule,  # Link to PostingSchedule
                business_type=payload.business_type,
                schedule_date=schedule_date,
                schedule_time=schedule_time,
                day_of_week=post_data.get('day_of_week', ''),
                content_type=post_data.get('content_type', 'educational'),
                title=post_data.get('title', ''),
                goal=post_data.get('goal', 'engagement'),
                hook=post_data.get('hook', ''),
                body=post_data.get('body', ''),
                engagement=post_data.get('engagement', ''),
                cta=post_data.get('cta', ''),
                hashtags=post_data.get('hashtags', []),
                media_type=post_data.get('media_type', 'text'),
                status='draft'
            )

            saved_posts.append({
                'id': scheduled_post.id,
                'date': str(scheduled_post.schedule_date),
                'time': str(scheduled_post.schedule_time),
                'title': scheduled_post.title
            })

        except Exception as e:
            # Skip invalid posts but continue with others
            print(f"Error saving post: {str(e)}")
            continue

    return {
        'success': True,
        'schedule_id': posting_schedule.id,
        'saved_count': len(saved_posts),
        'posts': saved_posts
    }


@router.get("/scheduled-posts", auth=AuthBearer(), response=List[ScheduledPostResponse])
def get_scheduled_posts(request, status: str = None):
    """
    Get all scheduled posts for the authenticated user

    Args:
        status: Optional filter by status (draft, approved, scheduled, published, failed)

    Returns:
        List of scheduled posts
    """
    user = request.auth
    queryset = ScheduledContent.objects.filter(user=user)

    if status:
        queryset = queryset.filter(status=status)

    posts = []
    for post in queryset:
        posts.append({
            'id': post.id,
            'schedule_id': post.schedule.id if post.schedule else None,
            'business_type': post.business_type,
            'schedule_date': str(post.schedule_date),
            'schedule_time': str(post.schedule_time),
            'day_of_week': post.day_of_week,
            'content_type': post.content_type,
            'title': post.title,
            'goal': post.goal,
            'hook': post.hook,
            'body': post.body,
            'engagement': post.engagement,
            'cta': post.cta,
            'hashtags': post.hashtags,
            'media_type': post.media_type,
            'status': post.status,
            'created_at': post.created_at.isoformat(),
            'full_content': post.full_content
        })

    return posts


@router.get("/scheduled-posts/{post_id}", auth=AuthBearer())
def get_scheduled_post(request, post_id: int):
    """
    Get a single scheduled post by ID

    Args:
        post_id: Post ID

    Returns:
        Scheduled post details
    """
    user = request.auth
    try:
        post = ScheduledContent.objects.get(id=post_id, user=user)
        return {
            'id': post.id,
            'business_type': post.business_type,
            'schedule_date': str(post.schedule_date),
            'schedule_time': str(post.schedule_time),
            'day_of_week': post.day_of_week,
            'content_type': post.content_type,
            'title': post.title,
            'goal': post.goal,
            'hook': post.hook,
            'body': post.body,
            'engagement': post.engagement,
            'cta': post.cta,
            'hashtags': post.hashtags,
            'media_type': post.media_type,
            'status': post.status,
            'created_at': post.created_at.isoformat(),
            'full_content': post.full_content
        }
    except ScheduledContent.DoesNotExist:
        return {'error': 'Post not found'}, 404


@router.delete("/scheduled-posts/{post_id}", auth=AuthBearer())
def delete_scheduled_post(request, post_id: int):
    """
    Delete a scheduled post

    Args:
        post_id: Post ID to delete

    Returns:
        Success message
    """
    user = request.auth
    try:
        post = ScheduledContent.objects.get(id=post_id, user=user)
        post.delete()
        return {'success': True, 'message': 'Post deleted successfully'}
    except ScheduledContent.DoesNotExist:
        return {'error': 'Post not found'}, 404


@router.put("/scheduled-posts/{post_id}/status", auth=AuthBearer())
def update_post_status(request, post_id: int, status: str = Form(...)):
    """
    Update the status of a scheduled post

    Args:
        post_id: Post ID
        status: New status (draft, approved, scheduled, published, failed)

    Returns:
        Updated post
    """
    user = request.auth
    try:
        post = ScheduledContent.objects.get(id=post_id, user=user)
        post.status = status
        post.save()

        return {
            'success': True,
            'post_id': post.id,
            'new_status': post.status
        }
    except ScheduledContent.DoesNotExist:
        return {'error': 'Post not found'}, 404


# ============ Posting Schedule Management Endpoints ============

@router.get("/schedules", auth=AuthBearer(), response=List[PostingScheduleResponse])
def get_posting_schedules(request):
    """
    Get all posting schedules for the authenticated user

    Returns:
        List of posting schedules with posts count
    """
    user = request.auth
    schedules = PostingSchedule.objects.filter(user=user)

    result = []
    for schedule in schedules:
        result.append({
            'id': schedule.id,
            'business_type': schedule.business_type,
            'goals': schedule.goals,
            'start_date': str(schedule.start_date),
            'duration': schedule.duration,
            'posts_per_day': schedule.posts_per_day,
            'total_posts': schedule.total_posts,
            'strategy_overview': schedule.strategy_overview,
            'hashtag_suggestions': schedule.hashtag_suggestions,
            'engagement_tips': schedule.engagement_tips,
            'created_at': schedule.created_at.isoformat(),
            'posts_count': schedule.posts.count()
        })

    return result


@router.delete("/schedules/{schedule_id}", auth=AuthBearer())
def delete_posting_schedule(request, schedule_id: int):
    """
    Delete a posting schedule and all its related posts

    Args:
        schedule_id: Schedule ID to delete

    Returns:
        Success message with deleted posts count
    """
    user = request.auth
    try:
        schedule = PostingSchedule.objects.get(id=schedule_id, user=user)
        posts_count = schedule.posts.count()
        schedule.delete()  # Cascade delete all related posts

        return {
            'success': True,
            'message': f'Schedule deleted successfully',
            'deleted_posts_count': posts_count
        }
    except PostingSchedule.DoesNotExist:
        return {'error': 'Schedule not found'}, 404


@router.post("/generate-from-images", auth=AuthBearer())
def generate_content_from_images(
    request,
    image_descriptions: List[str] = Form(...),
    user_prompt: str = Form(...),
    tone: str = Form("casual"),
    include_hashtags: bool = Form(True),
    language: str = Form("vi")
):
    """
    Generate content based on image descriptions

    Args:
        image_descriptions: List of image descriptions
        user_prompt: User's content requirements
        tone: Content tone
        include_hashtags: Whether to include hashtags
        language: Language code

    Returns:
        Generated content
    """
    result = AIContentService.generate_content_from_images(
        image_descriptions=image_descriptions,
        user_prompt=user_prompt,
        tone=tone,
        include_hashtags=include_hashtags,
        language=language
    )
    return result


# ============ Test Endpoints (No Auth - Remove in Production) ============

@router.post("/generate-test")
def generate_ai_content_test(
    request,
    prompt: str = Form(...),
    tone: str = Form("professional"),
    include_hashtags: bool = Form(True),
    include_emoji: bool = Form(True),
    language: str = Form("vi")
):
    """
    TEST endpoint - Generate content without authentication
    WARNING: Remove this endpoint in production!
    """
    result = AIContentService.generate_content(
        prompt=prompt,
        tone=tone,
        include_hashtags=include_hashtags,
        include_emoji=include_emoji,
        language=language
    )
    return result


@router.post("/hashtags-test")
def generate_hashtags_test(
    request,
    content: str = Form(...),
    count: int = Form(5)
):
    """
    TEST endpoint - Generate hashtags without authentication
    WARNING: Remove this endpoint in production!
    """
    result = AIContentService.generate_hashtags(
        content=content,
        count=count
    )
    return result


@router.post("/schedule-test")
def generate_schedule_test(
    request,
    business_type: str = Form(...),
    goals: str = Form(...),
    start_date: str = Form(...),
    duration: str = Form("1_week"),
    posts_per_day: int = Form(2),
    language: str = Form("vi")
):
    """
    TEST endpoint - Generate schedule without authentication
    WARNING: Remove this endpoint in production!
    """
    result = AIContentService.generate_posting_schedule(
        business_type=business_type,
        goals=goals,
        start_date=start_date,
        duration=duration,
        posts_per_day=posts_per_day,
        language=language
    )
    return result


# Step names for schedule generation (Vietnamese)
SCHEDULE_STEP_NAMES = {
    'validating': 'Kiểm tra thông tin',
    'preparing': 'Chuẩn bị prompt',
    'generating': 'Đang tạo lịch đăng',
    'parsing': 'Phân tích kết quả',
    'validating_result': 'Xác nhận lịch trình',
    'done': 'Hoàn thành'
}


def schedule_stream_generator(business_type: str, goals: str, start_date: str,
                              duration: str, posts_per_day: int, language: str):
    """Generator for streaming schedule generation progress"""
    import time

    def send_event(event_type: str, step: str = None, message: str = None, data: dict = None):
        event = {'type': event_type}
        if step:
            event['step'] = step
            event['step_name'] = SCHEDULE_STEP_NAMES.get(step, step)
        if message:
            event['message'] = message
        if data:
            event['data'] = data
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    try:
        # Step 1: Validating input
        yield send_event('progress', 'validating', 'Đang kiểm tra thông tin đầu vào...')

        if not business_type.strip() or not goals.strip() or not start_date:
            yield send_event('error', message='Vui lòng điền đầy đủ thông tin')
            return

        time.sleep(0.3)  # Small delay for UX

        # Step 2: Preparing prompt
        yield send_event('progress', 'preparing', 'Đang chuẩn bị prompt cho AI...')
        time.sleep(0.3)

        # Step 3: Generating schedule (main AI call)
        yield send_event('progress', 'generating', f'Đang tạo lịch đăng bài ({duration})...')

        result = AIContentService.generate_posting_schedule(
            business_type=business_type,
            goals=goals,
            start_date=start_date,
            duration=duration,
            posts_per_day=posts_per_day,
            language=language
        )

        # Step 4: Parsing result
        yield send_event('progress', 'parsing', 'Đang phân tích kết quả...')
        time.sleep(0.2)

        # Step 5: Validating result
        yield send_event('progress', 'validating_result',
                        f'Đã tạo {len(result.get("posts", []))} bài đăng, đang xác nhận...')
        time.sleep(0.2)

        # Step 6: Done
        yield send_event('done', 'done',
                        f'Hoàn thành! Đã tạo {len(result.get("posts", []))} bài đăng.',
                        data=result)

    except Exception as e:
        yield send_event('error', message=str(e))


@router.post("/schedule/stream")
def generate_schedule_stream(
    request,
    business_type: str = Form(...),
    goals: str = Form(...),
    start_date: str = Form(...),
    duration: str = Form("1_week"),
    posts_per_day: int = Form(2),
    language: str = Form("vi")
):
    """
    Generate posting schedule with streaming progress updates (SSE)

    Returns Server-Sent Events with progress updates:
    - progress: {type, step, step_name, message}
    - done: {type, step, step_name, message, data}
    - error: {type, message}
    """
    response = StreamingHttpResponse(
        schedule_stream_generator(
            business_type=business_type,
            goals=goals,
            start_date=start_date,
            duration=duration,
            posts_per_day=posts_per_day,
            language=language
        ),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ============ AI Image Generation Endpoints ============

@router.post("/generate-image", auth=AuthBearer(), response=AIImageGenerateSchema)
def generate_ai_image(
    request,
    prompt: str = Form(...),
    size: str = Form(...),
    creativity: str = Form(...),
    reference_images: List[UploadedFile] = File(None),
):
    """
    Generate image using AI (Google Gemini)

    Args:
        prompt: Text prompt describing the image to generate
        size: Image size (required) - '1080x1080', '1200x628', '1080x1920', '1920x1080'
        creativity: Creativity level (required) - 'low', 'medium', 'high'
        reference_images: Optional reference images for style/content guidance

    Returns:
        AIImageGenerateSchema: Generated image information
    """
    from apps.media.models import Media, MediaFolder

    # Get or create "AI Generated" folder for this user
    ai_folder, _ = MediaFolder.objects.get_or_create(
        user=request.auth,
        name='AI Generated',
        defaults={'parent': None}
    )

    # Save reference images temporarily if provided
    ref_paths = []
    if reference_images:
        for ref_file in reference_images:
            if ref_file and ref_file.size > 0:
                path = AIImageService.save_reference_image(ref_file, request.auth)
                ref_paths.append(path)

    try:
        # Generate image (count=1 for Media Library - faster generation)
        gen_result = AIImageService.generate_image(
            prompt=prompt,
            user=request.auth,
            size=size,
            creativity=creativity,
            reference_images=ref_paths if ref_paths else None,
            count=1
        )

        # Get first image from results (new format with 'images' key)
        results = gen_result.get('images', [])
        file_info = results[0]

        # Create database record with AI Generated folder
        media = Media.objects.create(
            user=request.auth,
            file_url=file_info['file_url'],
            file_path=file_info['file_path'],
            file_type='image',
            file_size=file_info['file_size'],
            width=file_info['width'],
            height=file_info['height'],
            folder=ai_folder,  # Auto-assign to AI Generated folder
        )

        return {
            "id": media.id,
            "file_url": media.file_url,
            "file_type": media.file_type,
            "file_size": media.file_size,
            "width": media.width,
            "height": media.height,
            "created_at": media.created_at.isoformat(),
            "message": "AI image generated successfully"
        }

    finally:
        # Clean up reference images
        if ref_paths:
            AIImageService.cleanup_reference_images(ref_paths)


@router.post("/generate-image-test")
def generate_ai_image_test(
    request,
    prompt: str = Form(...),
    size: str = Form(...),
    creativity: str = Form(...),
    reference_images: List[UploadedFile] = File(None),
):
    """
    TEST endpoint - Generate image using AI without authentication
    WARNING: Remove this endpoint in production!
    """
    from apps.auth.models import User
    from apps.media.models import Media, MediaFolder

    # Get or create a test user
    test_user, _ = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com'}
    )

    # Get or create "AI Generated" folder for this user
    ai_folder, _ = MediaFolder.objects.get_or_create(
        user=test_user,
        name='AI Generated',
        defaults={'parent': None}
    )

    # Save reference images temporarily if provided
    ref_paths = []
    if reference_images:
        for ref_file in reference_images:
            if ref_file and ref_file.size > 0:
                path = AIImageService.save_reference_image(ref_file, test_user)
                ref_paths.append(path)

    try:
        # Generate image (count=1 for Media Library - faster generation)
        gen_result = AIImageService.generate_image(
            prompt=prompt,
            user=test_user,
            size=size,
            creativity=creativity,
            reference_images=ref_paths if ref_paths else None,
            count=1
        )

        # Get first image from results (new format with 'images' key)
        results = gen_result.get('images', [])
        file_info = results[0]

        # Create database record with AI Generated folder
        media = Media.objects.create(
            user=test_user,
            file_url=file_info['file_url'],
            file_path=file_info['file_path'],
            file_type='image',
            file_size=file_info['file_size'],
            width=file_info['width'],
            height=file_info['height'],
            folder=ai_folder,  # Auto-assign to AI Generated folder
        )

        return {
            "id": media.id,
            "file_url": file_info['file_url'],
            "file_type": "image",
            "file_size": file_info['file_size'],
            "width": file_info['width'],
            "height": file_info['height'],
            "folder": "AI Generated",
            "message": "AI image generated successfully (TEST MODE)"
        }

    finally:
        # Clean up reference images
        if ref_paths:
            AIImageService.cleanup_reference_images(ref_paths)


# ============ Async Task Management Endpoints ============

@router.post("/tasks/content/submit", auth=AuthBearer(), response=TaskSubmitResponse)
def submit_content_task(
    request,
    prompt: str = Form(...),
    tone: str = Form("professional"),
    include_hashtags: bool = Form(True),
    include_emoji: bool = Form(True),
    language: str = Form("vi")
):
    """
    Submit content generation task for async processing

    Returns immediately with task_id for status polling

    Args:
        prompt: Content prompt
        tone: Content tone
        include_hashtags: Include hashtags flag
        include_emoji: Include emoji flag
        language: Language code

    Returns:
        TaskSubmitResponse with task_id
    """
    task_id = AsyncAIService.submit_content_task(
        user=request.auth,
        prompt=prompt,
        tone=tone,
        include_hashtags=include_hashtags,
        include_emoji=include_emoji,
        language=language
    )

    return {
        'task_id': task_id,
        'status': 'pending',
        'message': 'Content generation task submitted successfully. Use task_id to poll for status.'
    }


@router.post("/tasks/image/submit", auth=AuthBearer(), response=TaskSubmitResponse)
def submit_image_task(
    request,
    prompt: str = Form(...),
    size: str = Form(...),
    creativity: str = Form(...),
    reference_images: List[UploadedFile] = File(None),
):
    """
    Submit image generation task for async processing

    Returns immediately with task_id for status polling

    Args:
        prompt: Image prompt
        size: Image size
        creativity: Creativity level
        reference_images: Optional reference images

    Returns:
        TaskSubmitResponse with task_id
    """
    # Save reference images temporarily if provided
    ref_paths = []
    if reference_images:
        for ref_file in reference_images:
            if ref_file and ref_file.size > 0:
                path = AIImageService.save_reference_image(ref_file, request.auth)
                ref_paths.append(path)

    task_id = AsyncAIService.submit_image_task(
        user=request.auth,
        prompt=prompt,
        size=size,
        creativity=creativity,
        reference_image_paths=ref_paths if ref_paths else None
    )

    return {
        'task_id': task_id,
        'status': 'pending',
        'message': 'Image generation task submitted successfully. Use task_id to poll for status.'
    }


@router.post("/tasks/schedule/submit", auth=AuthBearer(), response=TaskSubmitResponse)
def submit_schedule_task(
    request,
    business_type: str = Form(...),
    goals: str = Form(...),
    start_date: str = Form(...),
    duration: str = Form("1_week"),
    posts_per_day: int = Form(2),
    language: str = Form("vi")
):
    """
    Submit schedule generation task for async processing

    Returns immediately with task_id for status polling

    Args:
        business_type: Business type
        goals: Marketing goals
        start_date: Start date
        duration: Schedule duration
        posts_per_day: Posts per day
        language: Language code

    Returns:
        TaskSubmitResponse with task_id
    """
    task_id = AsyncAIService.submit_schedule_task(
        user=request.auth,
        business_type=business_type,
        goals=goals,
        start_date=start_date,
        duration=duration,
        posts_per_day=posts_per_day,
        language=language
    )

    return {
        'task_id': task_id,
        'status': 'pending',
        'message': 'Schedule generation task submitted successfully. Use task_id to poll for status.'
    }


@router.get("/tasks/{task_id}/status", auth=AuthBearer(), response=TaskStatusResponse)
def get_task_status(request, task_id: str):
    """
    Get task status and result

    Poll this endpoint to check task progress and get results

    Args:
        task_id: Task identifier

    Returns:
        TaskStatusResponse with status, progress, and result
    """
    # First check Redis cache for fast access
    task_data = TaskManager.get_task(task_id)

    if not task_data:
        # If not in Redis, check database
        try:
            db_task = AsyncAITask.objects.get(task_id=task_id, user=request.auth)
            return {
                'task_id': db_task.task_id,
                'task_type': db_task.task_type,
                'status': db_task.status,
                'progress': db_task.progress,
                'result': db_task.result,
                'error_message': db_task.error_message,
                'created_at': db_task.created_at.isoformat(),
                'started_at': db_task.started_at.isoformat() if db_task.started_at else None,
                'completed_at': db_task.completed_at.isoformat() if db_task.completed_at else None,
                'duration_seconds': db_task.duration_seconds
            }
        except AsyncAITask.DoesNotExist:
            return {'error': 'Task not found'}, 404

    # Return data from Redis
    return {
        'task_id': task_data['task_id'],
        'task_type': task_data['task_type'],
        'status': task_data['status'],
        'progress': task_data['progress'],
        'result': task_data.get('result'),
        'error_message': task_data.get('error_message'),
        'created_at': task_data['created_at'],
        'started_at': task_data.get('started_at'),
        'completed_at': task_data.get('completed_at'),
        'duration_seconds': None  # Not stored in Redis, only in DB
    }


@router.get("/tasks/stats", auth=AuthBearer(), response=TaskStatsResponse)
def get_task_statistics(request):
    """
    Get AI generation statistics for the user

    Returns statistics including:
    - Total tasks count
    - Completed/failed tasks count
    - Average generation time per task type
    - Recent task history

    Returns:
        TaskStatsResponse with statistics
    """
    user = request.auth

    # Get all tasks for user
    all_tasks = AsyncAITask.objects.filter(user=user)

    # Basic counts
    total_tasks = all_tasks.count()
    completed_tasks = all_tasks.filter(status='completed').count()
    failed_tasks = all_tasks.filter(status='failed').count()

    # Average duration by task type (only completed tasks)
    completed_content_tasks = all_tasks.filter(
        task_type='content',
        status='completed',
        duration_seconds__isnull=False
    )
    avg_duration_content = completed_content_tasks.aggregate(
        avg=Avg('duration_seconds')
    )['avg']

    completed_image_tasks = all_tasks.filter(
        task_type='image',
        status='completed',
        duration_seconds__isnull=False
    )
    avg_duration_image = completed_image_tasks.aggregate(
        avg=Avg('duration_seconds')
    )['avg']

    completed_schedule_tasks = all_tasks.filter(
        task_type='schedule',
        status='completed',
        duration_seconds__isnull=False
    )
    avg_duration_schedule = completed_schedule_tasks.aggregate(
        avg=Avg('duration_seconds')
    )['avg']

    # Recent tasks (last 10)
    recent_tasks = all_tasks.order_by('-created_at')[:10]
    recent_tasks_data = []
    for task in recent_tasks:
        recent_tasks_data.append({
            'task_id': task.task_id,
            'task_type': task.task_type,
            'status': task.status,
            'duration_seconds': task.duration_seconds,
            'created_at': task.created_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        })

    return {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'failed_tasks': failed_tasks,
        'avg_duration_content': round(avg_duration_content, 2) if avg_duration_content else None,
        'avg_duration_image': round(avg_duration_image, 2) if avg_duration_image else None,
        'avg_duration_schedule': round(avg_duration_schedule, 2) if avg_duration_schedule else None,
        'recent_tasks': recent_tasks_data
    }


@router.delete("/tasks/{task_id}", auth=AuthBearer())
def cancel_task(request, task_id: str):
    """
    Cancel/delete a task

    Note: This only marks the task as deleted. If the task is already
    processing, it may still complete.

    Args:
        task_id: Task identifier

    Returns:
        Success message
    """
    # Delete from Redis
    TaskManager.delete_task(task_id)

    # Delete from database if exists
    try:
        task = AsyncAITask.objects.get(task_id=task_id, user=request.auth)
        task.delete()
    except AsyncAITask.DoesNotExist:
        pass

    return {
        'success': True,
        'message': 'Task cancelled/deleted successfully'
    }
