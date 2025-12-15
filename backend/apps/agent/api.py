"""
Agent API Endpoints
"""
import json
import base64
from typing import List, Optional
from ninja import Router, Schema, File, Form
from ninja.files import UploadedFile
from django.http import StreamingHttpResponse
from api.dependencies import AuthBearer
from .services import AgentConversationService, AgentPostService


router = Router()


# ============ Schemas ============

class ChatMessageRequest(Schema):
    message: str


class TokenUsageSchema(Schema):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class ChatMessageResponse(Schema):
    agent_response: str
    conversation_id: int
    function_calls: List[dict] = []
    token_usage: Optional[TokenUsageSchema] = None


class ConversationHistoryResponse(Schema):
    id: int
    role: str
    message: str
    function_calls: List[dict] = []
    created_at: str


class AgentPostImageResponse(Schema):
    id: int
    url: str
    order: int


class TargetAccountResponse(Schema):
    id: int
    name: str
    platform: str
    profile_picture_url: str = ''


class AgentPostResponse(Schema):
    id: int
    content: str
    full_content: str
    hashtags: List[str]
    image_url: Optional[str] = None  # Backward compatible - first image
    images: List[AgentPostImageResponse] = []  # All images
    status: str
    target_account: Optional[TargetAccountResponse] = None  # Page được gắn
    created_at: str
    completed_at: Optional[str] = None


# ============ Chat Endpoints ============

@router.post("/chat", auth=AuthBearer(), response=ChatMessageResponse)
def chat_with_agent(request, payload: ChatMessageRequest):
    """
    Chat với AI Agent

    Agent có thể:
    - Trả lời câu hỏi
    - Check hệ thống
    - Tạo bài đăng
    - Phân tích lịch đăng
    """
    user = request.auth

    result = AgentConversationService.send_message(
        user=user,
        message=payload.message
    )

    return {
        'agent_response': result['agent_response'],
        'conversation_id': result['conversation_id'],
        'function_calls': result.get('function_calls', []),
        'token_usage': result.get('token_usage', {})
    }


@router.post("/chat/stream", auth=AuthBearer())
def chat_with_agent_stream(request):
    """
    Chat với AI Agent với streaming progress updates (SSE)
    Hỗ trợ cả JSON body và multipart/form-data (với file đính kèm)

    Returns Server-Sent Events với các event types:
    - progress: Tiến trình đang thực hiện
    - function_call: Agent đang gọi function
    - done: Hoàn thành với kết quả cuối cùng
    - error: Lỗi xảy ra
    """
    user = request.auth

    # Parse request based on content type
    content_type = request.content_type or ''
    files_data = []

    if 'multipart/form-data' in content_type:
        # Handle file upload
        message = request.POST.get('message', '')

        # Collect all files (file_0, file_1, etc.)
        for key in request.FILES:
            uploaded_file = request.FILES[key]
            file_content = uploaded_file.read()
            file_mime = uploaded_file.content_type

            # Convert to base64 for Gemini
            file_base64 = base64.b64encode(file_content).decode('utf-8')

            files_data.append({
                'name': uploaded_file.name,
                'mime_type': file_mime,
                'data': file_base64
            })
    else:
        # Handle JSON body
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
        except json.JSONDecodeError:
            message = ''

    def event_stream():
        try:
            # Stream progress từ service
            for event in AgentConversationService.send_message_stream(
                user=user,
                message=message,
                files=files_data if files_data else None
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@router.get("/chat/history", auth=AuthBearer(), response=List[ConversationHistoryResponse])
def get_conversation_history(request, limit: int = 50):
    """
    Lấy lịch sử conversation với Agent
    """
    user = request.auth

    history = AgentConversationService.get_conversation_history(
        user=user,
        limit=limit
    )

    return history


@router.delete("/chat/history", auth=AuthBearer())
def clear_conversation_history(request):
    """
    Xóa toàn bộ lịch sử conversation
    """
    from .models import AgentConversation
    user = request.auth

    deleted_count = AgentConversation.objects.filter(user=user).delete()[0]

    return {
        'success': True,
        'message': f'Đã xóa {deleted_count} tin nhắn'
    }


# ============ Agent Posts Endpoints ============

@router.get("/posts", auth=AuthBearer(), response=List[AgentPostResponse])
def get_agent_posts(request, limit: int = 20):
    """
    Lấy danh sách bài đăng do Agent tạo
    """
    user = request.auth

    posts = AgentPostService.get_user_posts(
        user=user,
        limit=limit
    )

    return posts


@router.get("/posts/{post_id}", auth=AuthBearer())
def get_agent_post_detail(request, post_id: int):
    """
    Lấy chi tiết một bài đăng
    """
    from .models import AgentPost
    user = request.auth

    try:
        post = AgentPost.objects.select_related('target_account').prefetch_related('images__media').get(id=post_id, user=user)

        # Get all images - explicitly order by 'order' field to ensure hero image is first
        images = [
            {
                'id': img.id,
                'url': img.media.file_url,
                'order': img.order
            }
            for img in post.images.all().order_by('order')
        ]

        # Get target account info
        target_account_info = None
        if post.target_account:
            target_account_info = {
                'id': post.target_account.id,
                'name': post.target_account.name,
                'platform': post.target_account.platform,
                'profile_picture_url': post.target_account.profile_picture_url or ''
            }

        return {
            'id': post.id,
            'content': post.content,
            'full_content': post.full_content,
            'hashtags': post.hashtags,
            'image_url': post.generated_image.file_url if post.generated_image else None,
            'image_id': post.generated_image.id if post.generated_image else None,
            'images': images,  # All images
            'status': post.status,
            'target_account': target_account_info,  # Page được gắn
            'agent_reasoning': post.agent_reasoning,
            'generation_strategy': post.generation_strategy,
            'created_at': post.created_at.isoformat(),
            'completed_at': post.completed_at.isoformat() if post.completed_at else None
        }
    except AgentPost.DoesNotExist:
        return {'error': 'Post not found'}, 404


@router.delete("/posts/{post_id}", auth=AuthBearer())
def delete_agent_post(request, post_id: int):
    """
    Xóa bài đăng do Agent tạo
    """
    user = request.auth

    success = AgentPostService.delete_post(
        user=user,
        post_id=post_id
    )

    if success:
        return {
            'success': True,
            'message': 'Đã xóa bài đăng'
        }
    else:
        return {
            'success': False,
            'message': 'Không tìm thấy bài đăng'
        }, 404


@router.patch("/posts/{post_id}", auth=AuthBearer())
def update_agent_post(request, post_id: int):
    """
    Cập nhật bài đăng do Agent tạo (sửa nhanh content/hashtags)
    """
    import json
    user = request.auth

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return {'success': False, 'message': 'Invalid JSON'}, 400

    result = AgentPostService.update_post(
        user=user,
        post_id=post_id,
        content=data.get('content'),
        full_content=data.get('full_content'),
        hashtags=data.get('hashtags')
    )

    if result:
        return {
            'success': True,
            'message': 'Đã cập nhật bài đăng',
            'post': result
        }
    else:
        return {
            'success': False,
            'message': 'Không tìm thấy bài đăng'
        }, 404


# ============ Quick Actions ============

@router.post("/quick/generate-post", auth=AuthBearer())
def quick_generate_post(
    request,
    business_type: str,
    topic: str,
    goal: str = 'engagement'
):
    """
    Nhanh chóng tạo một bài đăng
    Agent sẽ tự động tạo content + image
    """
    user = request.auth

    # Create a prompt for agent
    prompt = f"Hãy tạo một bài đăng Facebook hoàn chỉnh về {topic} cho business {business_type} với mục tiêu {goal}. Include cả hình ảnh nhé!"

    result = AgentConversationService.send_message(
        user=user,
        message=prompt
    )

    return {
        'success': True,
        'message': 'Agent đang tạo bài đăng...',
        'agent_response': result['agent_response']
    }


@router.get("/stats", auth=AuthBearer())
def get_agent_stats(request):
    """
    Lấy thống kê về Agent
    """
    from .models import AgentPost, AgentConversation
    user = request.auth

    total_posts = AgentPost.objects.filter(user=user).count()
    completed_posts = AgentPost.objects.filter(user=user, status='completed').count()
    total_conversations = AgentConversation.objects.filter(user=user).count()

    return {
        'total_posts': total_posts,
        'completed_posts': completed_posts,
        'total_conversations': total_conversations,
        'summary': f'Agent đã tạo {completed_posts} bài đăng và có {total_conversations} cuộc hội thoại'
    }


# ============ Agent Settings Endpoints ============

class AgentSettingsSchema(Schema):
    logo_id: Optional[int] = None
    logo_url: Optional[str] = None
    logo_position: str = 'bottom_right'
    logo_size: int = 15
    auto_add_logo: bool = False
    hotline: str = ''
    website: str = ''
    auto_add_hotline: bool = False
    slogan: str = ''
    brand_colors: List[str] = []
    default_tone: str = 'casual'
    default_word_count: int = 100


class AgentSettingsUpdateSchema(Schema):
    logo_id: Optional[int] = None
    logo_position: Optional[str] = None
    logo_size: Optional[int] = None
    auto_add_logo: Optional[bool] = None
    hotline: Optional[str] = None
    website: Optional[str] = None
    auto_add_hotline: Optional[bool] = None
    slogan: Optional[str] = None
    brand_colors: Optional[List[str]] = None
    default_tone: Optional[str] = None
    default_word_count: Optional[int] = None


@router.get("/settings", auth=AuthBearer(), response=AgentSettingsSchema)
def get_agent_settings(request):
    """
    Lấy cài đặt Agent của user
    Tạo mới nếu chưa có
    """
    from .models import AgentSettings
    user = request.auth

    settings, created = AgentSettings.objects.get_or_create(user=user)

    return {
        'logo_id': settings.logo_id,
        'logo_url': settings.logo.file_url if settings.logo else None,
        'logo_position': settings.logo_position,
        'logo_size': settings.logo_size,
        'auto_add_logo': settings.auto_add_logo,
        'hotline': settings.hotline,
        'website': settings.website,
        'auto_add_hotline': settings.auto_add_hotline,
        'slogan': settings.slogan,
        'brand_colors': settings.brand_colors,
        'default_tone': settings.default_tone,
        'default_word_count': settings.default_word_count,
    }


@router.put("/settings", auth=AuthBearer())
def update_agent_settings(request, payload: AgentSettingsUpdateSchema):
    """
    Cập nhật cài đặt Agent
    """
    from .models import AgentSettings
    from apps.media.models import Media
    user = request.auth

    settings, created = AgentSettings.objects.get_or_create(user=user)

    # Update fields if provided
    if payload.logo_id is not None:
        if payload.logo_id == 0:
            settings.logo = None
        else:
            try:
                settings.logo = Media.objects.get(id=payload.logo_id, user=user)
            except Media.DoesNotExist:
                return {'success': False, 'message': 'Logo không tồn tại'}, 400

    if payload.logo_position is not None:
        settings.logo_position = payload.logo_position

    if payload.logo_size is not None:
        settings.logo_size = payload.logo_size

    if payload.auto_add_logo is not None:
        settings.auto_add_logo = payload.auto_add_logo

    if payload.hotline is not None:
        settings.hotline = payload.hotline

    if payload.website is not None:
        settings.website = payload.website

    if payload.auto_add_hotline is not None:
        settings.auto_add_hotline = payload.auto_add_hotline

    if payload.slogan is not None:
        settings.slogan = payload.slogan

    if payload.brand_colors is not None:
        settings.brand_colors = payload.brand_colors

    if payload.default_tone is not None:
        settings.default_tone = payload.default_tone

    if payload.default_word_count is not None:
        settings.default_word_count = payload.default_word_count

    settings.save()

    return {
        'success': True,
        'message': 'Đã cập nhật cài đặt',
        'settings': {
            'logo_id': settings.logo_id,
            'logo_url': settings.logo.file_url if settings.logo else None,
            'logo_position': settings.logo_position,
            'logo_size': settings.logo_size,
            'auto_add_logo': settings.auto_add_logo,
            'hotline': settings.hotline,
            'website': settings.website,
            'auto_add_hotline': settings.auto_add_hotline,
            'slogan': settings.slogan,
            'brand_colors': settings.brand_colors,
            'default_tone': settings.default_tone,
            'default_word_count': settings.default_word_count,
        }
    }


@router.post("/settings/logo", auth=AuthBearer())
def upload_agent_logo(request, file: UploadedFile = File(...)):
    """
    Upload logo cho Agent Settings
    Tự động lưu vào Media và cập nhật settings
    """
    from .models import AgentSettings
    from apps.media.services import MediaService
    user = request.auth

    # Save file to disk
    file_info = MediaService.save_file(file, user, file_type='image')

    # Create media record in database
    media = MediaService.create_media_record(user, file_info, file_type='image')

    # Update settings
    settings, created = AgentSettings.objects.get_or_create(user=user)
    settings.logo = media
    settings.save()

    return {
        'success': True,
        'message': 'Đã upload logo',
        'logo': {
            'id': media.id,
            'url': media.file_url
        }
    }
