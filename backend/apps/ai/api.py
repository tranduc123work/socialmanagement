"""
AI Content Generation API Endpoints
"""
from typing import List, Optional
from ninja import Router, Form, Schema, File, UploadedFile
from api.main import AuthBearer
from .services import AIContentService, AIImageService
from .models import PostingSchedule, ScheduledContent
from datetime import datetime

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
        # Generate image
        file_info = AIImageService.generate_image(
            prompt=prompt,
            user=request.auth,
            size=size,
            creativity=creativity,
            reference_images=ref_paths if ref_paths else None
        )

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
        # Generate image
        file_info = AIImageService.generate_image(
            prompt=prompt,
            user=test_user,
            size=size,
            creativity=creativity,
            reference_images=ref_paths if ref_paths else None
        )

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
