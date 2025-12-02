"""
Agent API Endpoints
"""
from typing import List, Optional
from ninja import Router, Schema
from api.dependencies import AuthBearer
from .services import AgentConversationService, AgentPostService


router = Router()


# ============ Schemas ============

class ChatMessageRequest(Schema):
    message: str


class ChatMessageResponse(Schema):
    agent_response: str
    conversation_id: int
    function_calls: List[dict] = []


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


class AgentPostResponse(Schema):
    id: int
    content: str
    full_content: str
    hashtags: List[str]
    image_url: Optional[str] = None  # Backward compatible - first image
    images: List[AgentPostImageResponse] = []  # All images
    status: str
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
        'function_calls': result.get('function_calls', [])
    }


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
        post = AgentPost.objects.prefetch_related('images__media').get(id=post_id, user=user)

        # Get all images
        images = [
            {
                'id': img.id,
                'url': img.media.file_url,
                'order': img.order
            }
            for img in post.images.all()
        ]

        return {
            'id': post.id,
            'content': post.content,
            'full_content': post.full_content,
            'hashtags': post.hashtags,
            'image_url': post.generated_image.file_url if post.generated_image else None,
            'image_id': post.generated_image.id if post.generated_image else None,
            'images': images,  # All images
            'status': post.status,
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
