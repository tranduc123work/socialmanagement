"""
Agent Services - Business logic và tool execution
"""
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db.models import Count, Q
from apps.auth.models import User
from apps.ai.models import ScheduledContent, PostingSchedule
from apps.ai.services import AIContentService, AIImageService
from apps.media.models import Media
from apps.platforms.models import SocialAccount
from .models import AgentPost, AgentConversation, AgentTask, AgentPostImage
from .agent_factory import get_agent
import re


def clean_markdown_from_content(content: str) -> str:
    """
    Loại bỏ markdown formatting khỏi content để đăng Facebook
    Facebook không hỗ trợ markdown, cần plain text

    Args:
        content: Nội dung có thể chứa markdown

    Returns:
        Content đã được làm sạch markdown
    """
    if not content:
        return content

    # Remove bold: **text** hoặc __text__
    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
    content = re.sub(r'__(.+?)__', r'\1', content)

    # Remove italic: *text* hoặc _text_ (cẩn thận không remove single *)
    content = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', content)
    content = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', content)

    # Remove strikethrough: ~~text~~
    content = re.sub(r'~~(.+?)~~', r'\1', content)

    # Remove inline code: `text`
    content = re.sub(r'`(.+?)`', r'\1', content)

    # Remove markdown headers: # ## ### etc
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

    # Remove markdown links: [text](url) -> text
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)

    # Remove markdown images: ![alt](url)
    content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', content)

    # Clean up extra whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()


def extract_hashtags_from_content(content: str) -> tuple:
    """
    Trích xuất hashtags từ cuối content

    Args:
        content: Nội dung có chứa hashtags ở cuối

    Returns:
        tuple: (content_without_hashtags, list_of_hashtags)
    """
    if not content:
        return content, []

    # Tìm tất cả hashtags trong content
    hashtag_pattern = r'#[a-zA-Z0-9_àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]+'
    all_hashtags = re.findall(hashtag_pattern, content, re.IGNORECASE)

    # Tìm block hashtags ở cuối content (thường là dòng cuối cùng)
    lines = content.strip().split('\n')

    # Check từ dưới lên để tìm dòng hashtags
    hashtag_lines = []
    content_lines = []
    found_content = False

    for line in reversed(lines):
        line_stripped = line.strip()

        # Nếu dòng chủ yếu là hashtags
        hashtags_in_line = re.findall(hashtag_pattern, line_stripped, re.IGNORECASE)
        non_hashtag_text = re.sub(hashtag_pattern, '', line_stripped).strip()

        # Nếu dòng gần như toàn hashtags (>50% là hashtags)
        if hashtags_in_line and len(non_hashtag_text) < len(line_stripped) * 0.3 and not found_content:
            hashtag_lines.insert(0, line)
        else:
            content_lines.insert(0, line)
            if line_stripped:  # Dòng có nội dung thực sự
                found_content = True

    # Nếu tìm thấy hashtag lines riêng biệt ở cuối
    if hashtag_lines:
        clean_content = '\n'.join(content_lines).strip()
        hashtags_text = ' '.join(hashtag_lines)
        final_hashtags = re.findall(hashtag_pattern, hashtags_text, re.IGNORECASE)
        return clean_content, final_hashtags

    # Nếu không tìm thấy block riêng, trả về tất cả hashtags tìm được
    return content, all_hashtags


class AgentToolExecutor:
    """
    Thực thi các tools mà LLM Agent yêu cầu
    """

    @staticmethod
    def execute_tool(function_name: str, arguments: Dict, user: User) -> Dict[str, Any]:
        """
        Execute một tool function

        Args:
            function_name: Tên function
            arguments: Arguments cho function
            user: User đang thực hiện

        Returns:
            Kết quả từ function
        """
        tool_map = {
            'get_current_datetime': AgentToolExecutor.get_current_datetime,
            'get_scheduled_posts': AgentToolExecutor.get_scheduled_posts,
            'get_agent_posts': AgentToolExecutor.get_agent_posts,
            'get_agent_post_details': AgentToolExecutor.get_agent_post_details,
            'get_system_stats': AgentToolExecutor.get_system_stats,
            'get_agent_settings': AgentToolExecutor.get_agent_settings,  # Fugu Settings
            'generate_post_content': AgentToolExecutor.generate_post_content,
            'generate_post_image': AgentToolExecutor.generate_post_image,
            'save_agent_post': AgentToolExecutor.save_agent_post,
            'edit_agent_post': AgentToolExecutor.edit_agent_post,
            'batch_edit_agent_posts': AgentToolExecutor.batch_edit_agent_posts,
            'analyze_schedule': AgentToolExecutor.analyze_schedule,
            'get_connected_accounts': AgentToolExecutor.get_connected_accounts,
            'update_page_info': AgentToolExecutor.update_page_info,
            'update_page_photo': AgentToolExecutor.update_page_photo,
            'batch_update_pages_info': AgentToolExecutor.batch_update_pages_info,
            'edit_image': AgentToolExecutor.edit_image,
            'batch_create_posts': AgentToolExecutor.batch_create_posts,
            'batch_add_text_to_images': AgentToolExecutor.batch_add_text_to_images,
        }

        if function_name not in tool_map:
            return {'error': f'Unknown function: {function_name}'}

        try:
            # Add user to arguments
            result = tool_map[function_name](user=user, **arguments)
            return result
        except Exception as e:
            return {'error': str(e)}

    # ==================== HELPER FUNCTIONS ====================
    # These are shared between single post and batch post creation

    @staticmethod
    def _get_agent_settings(user: User):
        """Get AgentSettings for user"""
        from .models import AgentSettings
        return AgentSettings.objects.filter(user=user).first()

    @staticmethod
    def get_agent_settings(user: User) -> Dict[str, Any]:
        """
        Tool: Lấy thông tin Fugu Settings của user
        Trả về logo_id, logo_url, và các brand settings khác
        """
        from .models import AgentSettings
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[AGENT TOOL] get_agent_settings called for user {user.id}")

        settings = AgentSettings.objects.filter(user=user).first()

        if not settings:
            return {
                'success': False,
                'message': 'Chưa có cài đặt Fugu Settings. Vui lòng cấu hình trong phần Settings.',
                'logo_id': None,
                'logo_url': None
            }

        result = {
            'success': True,
            'logo_id': settings.logo.id if settings.logo else None,
            'logo_url': settings.logo.file_url if settings.logo else None,
            'logo_position': settings.logo_position,
            'logo_size': settings.logo_size,
            'auto_add_logo': settings.auto_add_logo,
            'hotline': settings.hotline or '',
            'website': settings.website or '',
            'auto_add_hotline': settings.auto_add_hotline,
            'slogan': settings.slogan or '',
            'brand_colors': settings.brand_colors or [],
            'default_tone': settings.default_tone,
            'default_word_count': settings.default_word_count,
        }

        logger.info(f"[AGENT TOOL] Fugu Settings: logo_id={result['logo_id']}, logo_url={result['logo_url']}")
        return result

    @staticmethod
    def _apply_hotline_to_content(content: str, agent_settings) -> str:
        """Add hotline/website to content if enabled"""
        if not agent_settings or not agent_settings.auto_add_hotline or not agent_settings.hotline:
            return content

        # Find hashtags position to insert hotline before them
        lines = content.strip().split('\n')
        hashtag_start_idx = len(lines)

        # Find where hashtags start (look from the end)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith('#'):
                hashtag_start_idx = i
            else:
                break

        # Build hotline text
        hotline_text = f"\n📞 Hotline: {agent_settings.hotline}"
        if agent_settings.website:
            hotline_text += f"\n🌐 Website: {agent_settings.website}"

        # Insert hotline before hashtags
        if hashtag_start_idx < len(lines):
            content_lines = lines[:hashtag_start_idx]
            hashtag_lines = lines[hashtag_start_idx:]
            return '\n'.join(content_lines) + hotline_text + '\n\n' + '\n'.join(hashtag_lines)
        else:
            return content + hotline_text

    @staticmethod
    def _build_logo_instruction(agent_settings) -> tuple:
        """Build logo instruction and get logo path for image generation
        Returns: (logo_instruction: str, logo_path: str or None)
        """
        import os
        from django.conf import settings

        if not agent_settings or not agent_settings.auto_add_logo or not agent_settings.logo:
            return "", None

        logo_path = agent_settings.logo.file_path
        if not os.path.isabs(logo_path):
            logo_path = os.path.join(settings.MEDIA_ROOT, logo_path.lstrip('/media/'))

        if not os.path.exists(logo_path):
            return "", None

        position_map = {
            'top_left': 'góc trên bên trái',
            'top_right': 'góc trên bên phải',
            'bottom_left': 'góc dưới bên trái',
            'bottom_right': 'góc dưới bên phải',
            'center': 'chính giữa'
        }
        pos_text = position_map.get(agent_settings.logo_position, 'góc dưới bên phải')
        logo_size = agent_settings.logo_size or 15

        logo_instruction = f"""
🏷️ LOGO THƯƠNG HIỆU:
- Ảnh tham chiếu là LOGO của thương hiệu
- Đặt logo tinh tế ở {pos_text}, kích thước khoảng {logo_size}% ảnh
- Logo như watermark chuyên nghiệp, blend nhẹ với background
"""
        return logo_instruction, logo_path

    @staticmethod
    def _build_brand_instruction(agent_settings) -> str:
        """Build brand colors and slogan instructions"""
        instruction = ""

        if agent_settings and agent_settings.brand_colors:
            colors_str = ', '.join(agent_settings.brand_colors)
            instruction += f"\n🎨 MÀU THƯƠNG HIỆU: Sử dụng các màu {colors_str} trong thiết kế."

        if agent_settings and agent_settings.slogan:
            instruction += f"\n✨ SLOGAN: Có thể thêm \"{agent_settings.slogan}\" vào ảnh nếu phù hợp."

        return instruction

    # ==================== TOOL FUNCTIONS ====================

    @staticmethod
    def get_current_datetime(user: User) -> Dict:
        """Tool: Lấy thông tin thời gian hiện tại"""
        from datetime import datetime, timedelta

        now = timezone.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        # Vietnamese day names
        day_names = {
            0: 'Thứ Hai',
            1: 'Thứ Ba',
            2: 'Thứ Tư',
            3: 'Thứ Năm',
            4: 'Thứ Sáu',
            5: 'Thứ Bảy',
            6: 'Chủ Nhật'
        }

        return {
            'current_datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
            'current_date': today.strftime('%Y-%m-%d'),
            'current_time': now.strftime('%H:%M:%S'),
            'day_of_week': day_names.get(today.weekday(), 'Unknown'),
            'today': today.strftime('%Y-%m-%d'),
            'tomorrow': tomorrow.strftime('%Y-%m-%d'),
            'yesterday': yesterday.strftime('%Y-%m-%d'),
            'year': today.year,
            'month': today.month,
            'day': today.day,
            'hour': now.hour,
            'minute': now.minute,
            'timezone': str(timezone.get_current_timezone()),
            'message': f'Hôm nay là {day_names.get(today.weekday())}, ngày {today.strftime("%d/%m/%Y")}, giờ {now.strftime("%H:%M")}'
        }

    @staticmethod
    def get_agent_posts(user: User, limit: int = 20, status: str = 'all') -> Dict:
        """Tool: Lấy danh sách bài đăng do Agent tạo"""
        queryset = AgentPost.objects.filter(user=user)

        # Filter by status if specified
        if status != 'all':
            queryset = queryset.filter(status=status)

        # Order by most recent first
        queryset = queryset.order_by('-created_at')[:limit]

        posts = []
        for post in queryset:
            posts.append({
                'id': post.id,
                'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
                'full_content': post.full_content[:200] + '...' if post.full_content and len(post.full_content) > 200 else post.full_content,
                'hashtags': post.hashtags,
                'has_image': bool(post.generated_image),
                'image_url': post.generated_image.file_url if post.generated_image else None,
                'status': post.status,
                'created_at': post.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'completed_at': post.completed_at.strftime('%Y-%m-%d %H:%M:%S') if post.completed_at else None
            })

        return {
            'total': queryset.count(),
            'posts': posts,
            'message': f'Tìm thấy {len(posts)} bài đăng do Agent tạo'
        }

    @staticmethod
    def get_scheduled_posts(
        user: User,
        status: str = 'all',
        limit: int = 10,
        start_date: str = None,
        end_date: str = None,
        days_ahead: int = None,
        relative_day: str = None,
        specific_date: str = None
    ) -> Dict:
        """Tool: Lấy danh sách scheduled posts với date filtering, bao gồm business_type và marketing_goals"""
        from datetime import datetime, timedelta

        # Use select_related to optimize query and get PostingSchedule data
        queryset = ScheduledContent.objects.filter(user=user).select_related('schedule')

        # Filter by status
        if status != 'all':
            queryset = queryset.filter(status=status)

        today = timezone.now().date()
        actual_start = None
        actual_end = None

        # Filter by specific_date (highest priority - most explicit)
        if specific_date:
            try:
                target_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
                queryset = queryset.filter(schedule_date=target_date)
                actual_start = target_date
                actual_end = target_date
            except ValueError:
                pass  # Invalid date format, skip this filter

        # Filter by relative_day
        elif relative_day:
            if relative_day == 'today':
                queryset = queryset.filter(schedule_date=today)
                actual_start = today
                actual_end = today
            elif relative_day == 'tomorrow':
                tomorrow = today + timedelta(days=1)
                queryset = queryset.filter(schedule_date=tomorrow)
                actual_start = tomorrow
                actual_end = tomorrow
            elif relative_day == 'this_week':
                start_of_week = today - timedelta(days=today.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                queryset = queryset.filter(
                    schedule_date__gte=start_of_week,
                    schedule_date__lte=end_of_week
                )
                actual_start = start_of_week
                actual_end = end_of_week
        # Filter by days_ahead (range from today)
        elif days_ahead is not None:
            end = today + timedelta(days=days_ahead)
            queryset = queryset.filter(
                schedule_date__gte=today,
                schedule_date__lte=end
            )
            actual_start = today
            actual_end = end
        elif start_date and end_date:
            # Use provided date range
            queryset = queryset.filter(
                schedule_date__gte=start_date,
                schedule_date__lte=end_date
            )
            actual_start = start_date
            actual_end = end_date
        elif start_date:
            queryset = queryset.filter(schedule_date__gte=start_date)
            actual_start = start_date
            actual_end = None
        elif end_date:
            queryset = queryset.filter(schedule_date__lte=end_date)
            actual_start = None
            actual_end = end_date
        else:
            actual_start = None
            actual_end = None

        # Order and limit
        queryset = queryset.order_by('schedule_date', 'schedule_time')[:limit]

        posts = []
        for post in queryset:
            # Build full content - natural flowing text without labels
            full_content_parts = []
            if post.hook:
                full_content_parts.append(post.hook)
            if post.body:
                full_content_parts.append(post.body)
            if post.engagement:
                full_content_parts.append(post.engagement)
            if post.cta:
                full_content_parts.append(post.cta)
            if post.hashtags:
                full_content_parts.append(' '.join(post.hashtags))

            full_content = '\n\n'.join(full_content_parts)

            # Get marketing_goals from parent PostingSchedule
            marketing_goals = ''
            schedule_id = None
            if post.schedule:
                marketing_goals = post.schedule.goals or ''
                schedule_id = post.schedule.id

            posts.append({
                'id': post.id,
                'schedule_id': schedule_id,
                'business_type': post.business_type,
                'marketing_goals': marketing_goals,  # Mục tiêu marketing tổng thể từ PostingSchedule
                'title': post.title,
                'content_type': post.content_type,
                'goal': post.goal,  # Goal của từng bài (awareness/engagement/conversion/retention)
                'schedule_date': str(post.schedule_date),
                'schedule_time': str(post.schedule_time),
                'day_of_week': post.day_of_week or '',
                'status': post.status,
                'preview': post.hook[:100] if post.hook else '',
                'full_content': full_content,
                'hook': post.hook or '',
                'body': post.body or '',
                'engagement': post.engagement or '',
                'cta': post.cta or '',
                'hashtags': post.hashtags or [],
                'media_type': post.media_type or 'text'
            })

        return {
            'total': len(posts),
            'posts': posts,
            'status_filter': status,
            'date_range': {
                'start_date': str(actual_start) if actual_start else None,
                'end_date': str(actual_end) if actual_end else None,
                'days_ahead': days_ahead
            }
        }

    @staticmethod
    def get_system_stats(user: User) -> Dict:
        """Tool: Lấy thống kê bài đăng trên hệ thống"""
        from apps.platforms.models import SocialPost

        # === BÀI ĐĂNG TRÊN PLATFORMS (SocialPost) ===
        social_posts = SocialPost.objects.filter(created_by=user)
        total_social_posts = social_posts.count()
        published_posts = social_posts.filter(status='published').count()
        scheduled_posts = social_posts.filter(status='scheduled').count()
        draft_posts = social_posts.filter(status='draft').count()
        failed_posts = social_posts.filter(status='failed').count()

        # === BÀI ĐĂNG DO AGENT TẠO ===
        agent_posts_qs = AgentPost.objects.filter(user=user)
        total_agent_posts = agent_posts_qs.count()
        completed_agent_posts = agent_posts_qs.filter(status='completed').count()
        pending_agent_posts = agent_posts_qs.filter(status='pending').count()

        # === TÀI KHOẢN KẾT NỐI ===
        connected_accounts = SocialAccount.objects.filter(user=user, is_active=True).count()

        # === LỊCH ĐĂNG (ScheduledContent) ===
        total_scheduled_content = ScheduledContent.objects.filter(user=user).count()

        return {
            'social_posts': {
                'total': total_social_posts,
                'published': published_posts,
                'scheduled': scheduled_posts,
                'draft': draft_posts,
                'failed': failed_posts
            },
            'agent_posts': {
                'total': total_agent_posts,
                'completed': completed_agent_posts,
                'pending': pending_agent_posts
            },
            'connected_accounts': connected_accounts,
            'scheduled_content': total_scheduled_content,
            'summary': f"Đã đăng {published_posts} bài lên các platform, {scheduled_posts} bài đang chờ đăng, {total_agent_posts} bài do Agent tạo. Có {connected_accounts} tài khoản đang kết nối."
        }

    @staticmethod
    def generate_post_content(
        user: User,
        draft_content: str = None,
        page_context: str = None,
        topic: str = None,
        goal: str = 'engagement',
        tone: str = None,  # None = use default from AgentSettings
        word_count: int = None,  # None = use default from AgentSettings
        business_type: str = None,  # Loại ngành nghề/sản phẩm
        marketing_goals: str = None  # Mục tiêu marketing tổng thể
    ) -> Dict:
        """Tool: Generate/polish nội dung bài đăng

        Có 2 mode:
        1. Polish mode: Nếu có draft_content -> chau chuốt nội dung nháp
        2. Create mode: Nếu có topic -> tạo content mới từ đầu
        """
        import logging
        logger = logging.getLogger(__name__)

        # Get AgentSettings for default values and auto-add features
        from .models import AgentSettings
        agent_settings = AgentSettings.objects.filter(user=user).first()

        # Use default values from settings if not specified
        if tone is None:
            tone = agent_settings.default_tone if agent_settings else 'casual'
        if word_count is None:
            word_count = agent_settings.default_word_count if agent_settings else 150

        logger.info(f"[AGENT TOOL] generate_post_content called with:")
        logger.info(f"  - draft_content: {draft_content[:100] if draft_content else None}...")
        logger.info(f"  - page_context: {page_context}")
        logger.info(f"  - topic: {topic}")
        logger.info(f"  - goal: {goal}")
        logger.info(f"  - tone: {tone} (from settings: {agent_settings is not None})")
        logger.info(f"  - word_count: {word_count}")
        logger.info(f"  - business_type: {business_type}")
        logger.info(f"  - marketing_goals: {marketing_goals}")

        # Build page context section
        page_section = ""
        if page_context:
            page_section = f"""
BÀI VIẾT CHO PAGE: {page_context}
(Viết nội dung phù hợp với đặc thù của page này, có thể nhắc đến tên page nếu phù hợp với ngữ cảnh)
"""

        # Build business context section
        business_section = ""
        if business_type or marketing_goals:
            business_section = "\n📊 THÔNG TIN KINH DOANH:\n"
            if business_type:
                business_section += f"- NGÀNH NGHỀ/SẢN PHẨM: {business_type}\n"
            if marketing_goals:
                business_section += f"- MỤC TIÊU MARKETING: {marketing_goals}\n"
            business_section += """
⚠️ LƯU Ý QUAN TRỌNG:
- Nội dung PHẢI phù hợp với ngành nghề và sản phẩm nêu trên
- Hướng đến mục tiêu marketing đã đề ra
- Nhấn mạnh điểm mạnh, giá trị của sản phẩm/dịch vụ
"""

        # Determine mode and build prompt
        if draft_content:
            # POLISH MODE: Chau chuốt nội dung nháp
            prompt = f"""
NHIỆM VỤ: Chau chuốt nội dung nháp thành bài đăng hoàn chỉnh, TỐI ƯU CHO REACH VÀ ENGAGEMENT.
{page_section}{business_section}
NỘI DUNG NHÁP:
{draft_content}

MỤC TIÊU: {goal}
GIỌNG ĐIỆU: {tone}

YÊU CẦU CHẤT LƯỢNG:
- GIỮ NGUYÊN ý chính, thông điệp của nội dung nháp
- Viết lại cho CHẢY TỰ NHIÊN như người thật đang chia sẻ
- Bắt đầu bằng câu hook gây chú ý mạnh (1-2 câu)
- Nội dung chính súc tích, đi thẳng vào điểm chính
- Thêm 1 câu hỏi tương tác ngắn gọn
- Kết thúc bằng CTA ngắn (1 câu)
- KHÔNG dùng markdown (*, **, #, -)

🚀 TỐI ƯU REACH & ENGAGEMENT (CHUẨN SEO FACEBOOK):
- Dùng TỪ KHÓA CHÍNH liên quan đến sản phẩm/dịch vụ 2-3 lần một cách tự nhiên
- Câu hook phải GÂY TÒ MÒ, khiến người đọc muốn xem tiếp (dùng con số, câu hỏi mở, sự kiện gây chú ý)
- Câu hỏi tương tác nên DỄ TRẢ LỜI để tăng comment (VD: "Bạn thích màu nào?", "Ai đồng ý?")
- CTA phải RÕ RÀNG và CỤ THỂ (VD: "Inbox ngay", "Gọi hotline", "Click link")
- Sử dụng EMOJI phù hợp 🎯 để tăng điểm dừng mắt (2-4 emoji, KHÔNG spam)
- Cuối bài thêm 5-7 HASHTAGS PHỔ BIẾN + HASHTAGS NGÁCH (mix trending + specific)

⚠️ GIỚI HẠN ĐỘ DÀI: KHÔNG ĐƯỢC vượt quá {word_count} từ (không tính hashtags). Viết SÚC TÍCH, tránh dài dòng.

QUAN TRỌNG: Chỉ viết nội dung thuần text, KHÔNG ghi label như "Hook:", "Body:", "CTA:"
"""
        elif topic:
            # CREATE MODE: Tạo content mới
            prompt = f"""
NHIỆM VỤ: Tạo bài đăng Facebook hoàn chỉnh, TỐI ƯU CHO REACH VÀ ENGAGEMENT.
{page_section}{business_section}
CHỦ ĐỀ: {topic}
MỤC TIÊU: {goal}
GIỌNG ĐIỆU: {tone}

YÊU CẦU CHẤT LƯỢNG:
- Viết nội dung CHẢY TỰ NHIÊN như người thật đang chia sẻ
- Bắt đầu bằng câu hook gây chú ý mạnh (1-2 câu)
- Nội dung chính súc tích, đi thẳng vào điểm chính
- Đặt 1 câu hỏi tương tác ngắn gọn
- Kết thúc bằng CTA ngắn (1 câu)
- KHÔNG dùng markdown (*, **, #, -)

🚀 TỐI ƯU REACH & ENGAGEMENT (CHUẨN SEO FACEBOOK):
- Dùng TỪ KHÓA CHÍNH liên quan đến sản phẩm/dịch vụ 2-3 lần một cách tự nhiên
- Câu hook phải GÂY TÒ MÒ, khiến người đọc muốn xem tiếp (dùng con số, câu hỏi mở, sự kiện gây chú ý)
- Câu hỏi tương tác nên DỄ TRẢ LỜI để tăng comment (VD: "Bạn thích màu nào?", "Ai đồng ý?")
- CTA phải RÕ RÀNG và CỤ THỂ (VD: "Inbox ngay", "Gọi hotline", "Click link")
- Sử dụng EMOJI phù hợp 🎯 để tăng điểm dừng mắt (2-4 emoji, KHÔNG spam)
- Cuối bài thêm 5-7 HASHTAGS PHỔ BIẾN + HASHTAGS NGÁCH (mix trending + specific)

⚠️ GIỚI HẠN ĐỘ DÀI: KHÔNG ĐƯỢC vượt quá {word_count} từ (không tính hashtags). Viết SÚC TÍCH, tránh dài dòng.

QUAN TRỌNG: Chỉ viết nội dung thuần text, KHÔNG ghi label như "Hook:", "Body:", "CTA:"
"""
        else:
            return {
                'error': 'Cần draft_content hoặc topic để tạo nội dung',
                'success': False
            }

        logger.info(f"[AGENT TOOL] Mode: {'POLISH' if draft_content else 'CREATE'}")

        result = AIContentService.generate_content(
            prompt=prompt,
            tone=tone,
            include_hashtags=True,
            language='vi'
        )

        full_ai_content = result.get('content', '')

        logger.info(f"[AGENT TOOL] AI returned content length: {len(full_ai_content)} chars")
        logger.info(f"[AGENT TOOL] Content preview:\n{full_ai_content[:500]}...")

        # Clean markdown từ content (Facebook không hỗ trợ markdown)
        full_ai_content = clean_markdown_from_content(full_ai_content)
        logger.info(f"[AGENT TOOL] Cleaned markdown from content")

        # Auto-add hotline using helper function
        full_ai_content = AgentToolExecutor._apply_hotline_to_content(full_ai_content, agent_settings)
        if agent_settings and agent_settings.auto_add_hotline:
            logger.info(f"[AGENT TOOL] Auto-added hotline: {agent_settings.hotline}")

        return {
            'content': full_ai_content,
            'mode': 'polish' if draft_content else 'create',
            'page_context': page_context,
            'success': True,
            'message': 'Đã tạo nội dung bài đăng hoàn chỉnh'
        }

    # Facebook image layout configurations - optimized for Facebook display 2024
    # Based on Facebook guidelines & best practices:
    # - 1080x1080 (1:1 square): Most consistent, no unexpected cropping
    # - 1080x1350 (4:5 portrait): Best for mobile, takes most screen space
    # - 1920x1080 (16:9 landscape): Standard video/landscape ratio
    # - 1200x628 (1.91:1): Link preview standard
    # IMPORTANT: First image determines layout orientation on Facebook
    FB_IMAGE_LAYOUTS = {
        1: [
            {
                'layout': 'single_portrait',
                'sizes': ['1080x1350'],  # 4:5 - Best for mobile feed
                'description': '1 ảnh dọc 4:5 (1080x1350) - tối ưu mobile'
            },
            {
                'layout': 'single_landscape',
                'sizes': ['1200x628'],  # 1.91:1 - Link preview standard
                'description': '1 ảnh ngang link preview (1200x628)'
            },
            {
                'layout': 'single_square',
                'sizes': ['1080x1080'],  # 1:1 - Most consistent
                'description': '1 ảnh vuông (1080x1080)'
            }
        ],
        2: [
            {
                # Portrait first → 2 images side-by-side
                'layout': 'two_portrait',
                'sizes': ['1080x1350', '1080x1350'],  # 4:5 portrait - more screen space
                'description': '2 ảnh dọc 4:5 ngang hàng (1080x1350)'
            },
            {
                # Square → 2 images stacked vertically
                'layout': 'two_square',
                'sizes': ['1080x1080', '1080x1080'],  # FB stacks vertically
                'description': '2 ảnh vuông xếp dọc (1080x1080)'
            }
        ],
        3: [
            {
                # Portrait first → Portrait LEFT (hero) + 2 squares stacked RIGHT
                'layout': 'one_vertical_two_square',
                'sizes': ['1080x1350', '1080x1080', '1080x1080'],  # 4:5 hero + squares
                'description': '1 ảnh dọc 4:5 (TRÁI, hero) + 2 vuông (PHẢI)'
            },
            {
                # Landscape first → Landscape TOP (hero) + 2 squares BELOW
                'layout': 'one_horizontal_two_square',
                'sizes': ['1920x1080', '1080x1080', '1080x1080'],  # 16:9 hero + squares
                'description': '1 ảnh ngang 16:9 (TRÊN, hero) + 2 vuông (DƯỚI)'
            }
        ],
        4: [
            {
                # All squares - most balanced layout (2x2 grid)
                'layout': 'four_square',
                'sizes': ['1080x1080', '1080x1080', '1080x1080', '1080x1080'],
                'description': '4 ảnh vuông đều nhau (2x2 grid)'
            },
            {
                # Portrait hero LEFT + 3 squares stacked RIGHT
                'layout': 'one_vertical_three_square',
                'sizes': ['1080x1350', '1080x1080', '1080x1080', '1080x1080'],
                'description': '1 ảnh dọc 4:5 (TRÁI, hero) + 3 vuông (PHẢI)'
            },
            {
                # Landscape hero TOP + 3 squares BELOW
                'layout': 'one_horizontal_three_square',
                'sizes': ['1920x1080', '1080x1080', '1080x1080', '1080x1080'],
                'description': '1 ảnh ngang 16:9 (TRÊN, hero) + 3 vuông (DƯỚI)'
            }
        ],
        5: [
            {
                # All squares - consistent for 5 images (2 top + 3 bottom)
                'layout': 'five_square',
                'sizes': ['1080x1080', '1080x1080', '1080x1080', '1080x1080', '1080x1080'],
                'description': '5 ảnh vuông (2 lớn trên + 3 nhỏ dưới)'
            },
            {
                # 1 portrait hero + 4 squares for visual variety
                'layout': 'one_portrait_four_square',
                'sizes': ['1080x1350', '1080x1080', '1080x1080', '1080x1080', '1080x1080'],
                'description': '1 ảnh dọc 4:5 (hero) + 4 vuông'
            },
            {
                # 2 portrait heroes + 3 squares for more impact
                'layout': 'two_portrait_three_square',
                'sizes': ['1080x1350', '1080x1350', '1080x1080', '1080x1080', '1080x1080'],
                'description': '2 ảnh dọc 4:5 (hero) + 3 vuông - visual variety'
            }
        ]
    }

    @staticmethod
    def generate_post_image(
        user: User,
        post_content: str,
        page_context: str = None,
        style: str = 'professional',
        size: str = None,  # Now auto-determined by count
        count: int = 3,
        reference_image_data: str = None,
        reference_media_id: int = None,
        text_overlay: str = None,
        business_type: str = None,  # Loại ngành nghề/sản phẩm
        marketing_goals: str = None  # Mục tiêu marketing tổng thể
    ) -> Dict:
        """Tool: Generate hình ảnh phù hợp với content bài đăng

        Args:
            post_content: Nội dung bài đăng đã generate (từ generate_post_content)
            page_context: Tên page + ngành nghề để customize
            style: Phong cách ảnh
            size: Kích thước (nếu không set, sẽ tự động theo count)
            count: Số lượng ảnh cần tạo (1-5)
            reference_image_data: Base64 ảnh tham chiếu từ user
            reference_media_id: ID ảnh tham chiếu từ thư viện
            text_overlay: Text cụ thể để thêm vào ảnh (nếu có)
        """
        import logging
        import random
        import base64
        import tempfile
        import os
        from django.conf import settings
        logger = logging.getLogger(__name__)

        # Convert count to int (LLM may return float like 3.0)
        try:
            count = int(count) if count else 3
        except (ValueError, TypeError):
            count = 3

        # Ensure count is within valid range
        count = max(1, min(5, count))

        # Get layout options for this count and randomly select one
        layout_options = AgentToolExecutor.FB_IMAGE_LAYOUTS.get(count, AgentToolExecutor.FB_IMAGE_LAYOUTS[3])
        layout_config = random.choice(layout_options)
        layout_type = layout_config['layout']
        image_sizes = layout_config['sizes']

        logger.info(f"[AGENT TOOL] generate_post_image called with:")
        logger.info(f"  - post_content length: {len(post_content)} chars")
        logger.info(f"  - page_context: {page_context}")
        logger.info(f"  - style: {style}")
        logger.info(f"  - count: {count}")
        logger.info(f"  - layout: {layout_type}")
        logger.info(f"  - sizes: {image_sizes}")
        logger.info(f"  - reference_image_data: {'yes' if reference_image_data else 'no'}")
        logger.info(f"  - reference_media_id: {reference_media_id}")
        logger.info(f"  - text_overlay: {text_overlay}")
        logger.info(f"  - business_type: {business_type}")
        logger.info(f"  - marketing_goals: {marketing_goals}")

        try:
            # Collect reference images
            reference_images = []

            if reference_image_data:
                try:
                    if ',' in reference_image_data:
                        reference_image_data = reference_image_data.split(',')[1]
                    img_bytes = base64.b64decode(reference_image_data)
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    temp_file.write(img_bytes)
                    temp_file.close()
                    reference_images.append(temp_file.name)
                    logger.info(f"[AGENT TOOL] Saved reference image to {temp_file.name}")
                except Exception as e:
                    logger.error(f"[AGENT TOOL] Error decoding reference_image_data: {e}")

            elif reference_media_id:
                try:
                    ref_media = Media.objects.get(id=reference_media_id)
                    file_path = ref_media.file_path
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(settings.MEDIA_ROOT, file_path.lstrip('/media/'))
                    if os.path.exists(file_path):
                        reference_images.append(file_path)
                        logger.info(f"[AGENT TOOL] Using reference media {reference_media_id}: {file_path}")
                except Media.DoesNotExist:
                    logger.warning(f"[AGENT TOOL] Reference media {reference_media_id} not found")

            # Check if user has auto_add_logo enabled
            logo_instruction = ""
            from .models import AgentSettings
            agent_settings = AgentSettings.objects.filter(user=user).first()
            if agent_settings and agent_settings.auto_add_logo and agent_settings.logo:
                # Add logo to reference images
                logo_path = agent_settings.logo.file_path
                if not os.path.isabs(logo_path):
                    logo_path = os.path.join(settings.MEDIA_ROOT, logo_path.lstrip('/media/'))
                if os.path.exists(logo_path):
                    reference_images.append(logo_path)
                    logger.info(f"[AGENT TOOL] Adding logo to reference images: {logo_path}")

                    # Build logo instruction based on position and size
                    position_map = {
                        'top_left': 'góc trên bên trái',
                        'top_right': 'góc trên bên phải',
                        'bottom_left': 'góc dưới bên trái',
                        'bottom_right': 'góc dưới bên phải',
                        'center': 'chính giữa'
                    }
                    pos_text = position_map.get(agent_settings.logo_position, 'góc dưới bên phải')
                    logo_size = agent_settings.logo_size

                    logo_instruction = f"""
🏷️ LOGO THƯƠNG HIỆU (TÍCH HỢP TỰ NHIÊN):
- Ảnh tham chiếu thứ 2 là LOGO của thương hiệu
- CÁCH TÍCH HỢP LOGO (chọn 1 trong các cách sau, ưu tiên theo thứ tự):

  1. WATERMARK TINH TẾ (ưu tiên nhất):
     • Đặt logo tinh tế ở {pos_text}
     • Kích thước nhỏ gọn (khoảng {logo_size}% ảnh)
     • Blend nhẹ với background, có thể thêm subtle shadow
     • Có thể giảm opacity nhẹ để logo hòa hợp hơn
     • KHÔNG đặt logo trong khung vuông/chữ nhật có màu nền
     • Logo "nằm" trực tiếp trên ảnh như watermark chuyên nghiệp

  2. TÍCH HỢP VÀO KHUNG CẢNH (nếu phù hợp):
     • Logo xuất hiện trên biển hiệu, bảng quảng cáo trong ảnh
     • Logo in trên sản phẩm, bao bì, hộp đựng
     • Logo trên đồng phục nhân viên, áo thun
     • Logo trên banner, standee, backdrop trong scene

- ⛔ TRÁNH: Khung nền xung quanh logo, logo quá to che nội dung, màu chói không hợp ảnh
- ✅ MỤC TIÊU: Logo tinh tế, chuyên nghiệp, không làm phân tâm nội dung chính
"""

            # Add brand_colors instruction if available
            brand_colors_instruction = ""
            if agent_settings and agent_settings.brand_colors:
                colors_str = ', '.join(agent_settings.brand_colors)
                brand_colors_instruction = f"""
🎨 MÀU THƯƠNG HIỆU:
- Sử dụng các màu sau trong thiết kế: {colors_str}
- Màu này nên xuất hiện trong các chi tiết trang trí, text, hoặc tông màu chủ đạo
- Giữ sự hài hòa màu sắc, không cần dùng tất cả màu cùng lúc
"""
                logger.info(f"[AGENT TOOL] Using brand colors: {colors_str}")

            # Add slogan instruction if available
            slogan_instruction = ""
            if agent_settings and agent_settings.slogan:
                slogan_instruction = f"""
✨ SLOGAN/TAGLINE:
- Có thể thêm slogan của thương hiệu vào ảnh nếu phù hợp: "{agent_settings.slogan}"
- Nếu thêm slogan, đặt ở vị trí dễ nhìn, font đẹp, màu tương phản
"""
                logger.info(f"[AGENT TOOL] Slogan available: {agent_settings.slogan}")

            # Build business context for image
            business_context = ""
            if business_type or marketing_goals:
                business_context = "\n📊 NGỮ CẢNH KINH DOANH:\n"
                if business_type:
                    business_context += f"- NGÀNH NGHỀ/SẢN PHẨM: {business_type}\n"
                if marketing_goals:
                    business_context += f"- MỤC TIÊU: {marketing_goals}\n"
                business_context += "- Hình ảnh phải thể hiện đúng đặc thù ngành nghề và hỗ trợ mục tiêu marketing\n"

            # Build image prompt từ content
            content_summary = post_content[:500] if len(post_content) > 500 else post_content

            # Text instruction - if user provides text_overlay, add it; otherwise suggest AI can add text
            if text_overlay:
                text_instruction = f"""
TEXT TRÊN ẢNH:
- Thêm text sau vào ảnh một cách nổi bật, dễ đọc: "{text_overlay}"
- Text phải có font đẹp, màu tương phản với nền
- Có thể thêm effect như shadow hoặc outline để dễ đọc
"""
            else:
                text_instruction = """
TEXT TRÊN ẢNH (TÙY CHỌN):
- Có thể thêm text/slogan ngắn gọn nếu phù hợp với nội dung
- Hoặc để ảnh không có text nếu ảnh đã đủ ý nghĩa
- Nếu thêm text: font đẹp, màu tương phản, không che nội dung chính
"""

            # Build prompt with or without reference
            photorealistic_requirement = """
⚠️ BẮT BUỘC - PHOTOREALISTIC 100%:
- Ảnh phải trông như CHỤP THẬT từ máy ảnh chuyên nghiệp (DSLR/mirrorless)
- KHÔNG được trông như ảnh AI tạo ra
- Ánh sáng TỰ NHIÊN: natural light, golden hour, hoặc studio soft lighting
- Màu sắc CHÂN THỰC, không quá saturate, không neon
- Chi tiết THỰC TẾ: texture bề mặt (da, vải, kim loại, gỗ...) phải như thật
- Bối cảnh THỰC TẾ như location thật ở Việt Nam (showroom, cửa hàng, văn phòng, công trường...)
- Depth of field và bokeh như ảnh chụp thật
- TRÁNH: texture lặp lại, blur kỳ lạ, bàn tay bất thường, background giả tạo, floating objects
"""
            if reference_images:
                image_prompt = f"""
Tạo hình ảnh PHOTOREALISTIC cho bài đăng Facebook, LẤY CẢM HỨNG từ ảnh tham chiếu.

{photorealistic_requirement}

NỘI DUNG BÀI ĐĂNG:
{content_summary}

{"NGÀNH NGHỀ: " + page_context if page_context else ""}
{business_context}
YÊU CẦU HÌNH ẢNH:
- Phong cách: {style} - nhưng PHẢI THỰC TẾ như ảnh chụp
- Tham khảo phong cách, màu sắc, bố cục từ ảnh tham chiếu
- Tạo ảnh MỚI trông như CHỤP THẬT, phù hợp với nội dung bài đăng
- Sản phẩm/đối tượng trong khung cảnh TỰ NHIÊN, không giả tạo
{text_instruction}
{logo_instruction}
{brand_colors_instruction}
{slogan_instruction}
"""
            else:
                image_prompt = f"""
Tạo hình ảnh PHOTOREALISTIC cho bài đăng Facebook.

{photorealistic_requirement}

NỘI DUNG BÀI ĐĂNG:
{content_summary}

{"NGÀNH NGHỀ: " + page_context if page_context else ""}
{business_context}
YÊU CẦU HÌNH ẢNH:
- Phong cách: {style} - nhưng PHẢI THỰC TẾ như ảnh chụp
- Hình ảnh phải liên quan đến nội dung bài đăng
- Trông như ảnh chụp từ máy ảnh chuyên nghiệp
- Sản phẩm/đối tượng trong khung cảnh TỰ NHIÊN, thực tế
{text_instruction}
{logo_instruction}
{brand_colors_instruction}
{slogan_instruction}
"""

            logger.info(f"[AGENT TOOL] Image prompt:\n{image_prompt[:500]}...")

            # Generate images with appropriate sizes
            media_list = []

            # Token tracking for image generation
            total_image_tokens = 0
            total_image_prompt_tokens = 0
            total_image_output_tokens = 0

            # Find the HERO image index (largest size = most prominent position)
            size_areas = []
            for s in image_sizes:
                try:
                    w, h = map(int, s.split('x'))
                    size_areas.append(w * h)
                except:
                    size_areas.append(0)
            hero_idx = size_areas.index(max(size_areas)) if size_areas else 0
            logger.info(f"[AGENT TOOL] Hero image will be at index {hero_idx} (size: {image_sizes[hero_idx] if hero_idx < len(image_sizes) else 'default'})")

            for idx in range(count):
                # Get size for this image position
                img_size = image_sizes[idx] if idx < len(image_sizes) else '1080x1080'

                # Use provided size if specified, otherwise use layout-based size
                final_size = size if size else img_size

                # Determine image role based on position
                is_hero = (idx == hero_idx)

                # Build role-specific instruction
                if is_hero:
                    role_instruction = """
🌟 VAI TRÒ: ẢNH CHÍNH (HERO) - Vị trí nổi bật nhất trong bố cục
- Đây là ảnh LỚN NHẤT, được nhìn thấy ĐẦU TIÊN
- Bố cục tập trung, điểm nhấn mạnh, màu sắc thu hút
- TEXT LÀ TÙY CHỌN - AI tự quyết định:
  • Nếu nội dung CẦN truyền tải thông điệp → thêm text TO, RÕ RÀNG, font đẹp
  • Nếu hình ảnh đã đủ sức truyền tải → KHÔNG CẦN text, để ảnh nói lên tất cả
- NẾU CÓ TEXT: đây là nơi text nổi bật NHẤT (so với ảnh phụ)
- Logo (nếu có): đặt tinh tế, chuyên nghiệp
"""
                else:
                    role_instruction = f"""
📷 VAI TRÒ: ẢNH PHỤ #{idx + 1} - Hỗ trợ ảnh chính
- Ảnh này hiển thị NHỎ HƠN, đi kèm ảnh chính
- TEXT LÀ TÙY CHỌN - AI tự quyết định:
  • Có thể KHÔNG CÓ text - tập trung vào hình ảnh đẹp
  • Hoặc có text TINH TẾ, NHỎ hơn ảnh chính
- Nội dung: góc nhìn khác, chi tiết sản phẩm, lifestyle, không gian
- KHÔNG lặp lại y hệt ảnh chính
- Logo: KHÔNG BẮT BUỘC ở ảnh phụ
"""

                # Combine prompts
                final_prompt = f"{image_prompt}\n{role_instruction}"

                logger.info(f"[AGENT TOOL] Generating image {idx + 1}/{count} ({'HERO' if is_hero else 'SUPPORTING'}) with size {final_size}")

                gen_result = AIImageService.generate_image(
                    prompt=final_prompt,
                    user=user,
                    size=final_size,
                    creativity='low',  # Use 'low' for most photorealistic results
                    reference_images=reference_images if reference_images else None,
                    count=1  # Generate one at a time for different sizes
                )

                # Track token usage from image generation
                if gen_result.get('token_usage'):
                    token_usage = gen_result['token_usage']
                    total_image_tokens += token_usage.get('total_tokens', 0)
                    total_image_prompt_tokens += token_usage.get('prompt_tokens', 0)
                    total_image_output_tokens += token_usage.get('output_tokens', 0)

                results = gen_result.get('images', [])
                if results:
                    result = results[0]
                    media = Media.objects.create(
                        user=user,
                        file_url=result['file_url'],
                        file_path=result['file_path'],
                        file_type='image',
                        file_size=result['file_size'],
                        width=result['width'],
                        height=result['height']
                    )
                    media_list.append({
                        'media_id': media.id,
                        'image_url': media.file_url,
                        'width': media.width,
                        'height': media.height,
                        'order': idx,
                        'position': f'image_{idx + 1}',
                        'intended_size': final_size
                    })

            # Cleanup temp files
            for ref_path in reference_images:
                if ref_path.startswith(tempfile.gettempdir()):
                    try:
                        os.unlink(ref_path)
                    except:
                        pass

            media_ids = [m['media_id'] for m in media_list]
            logger.info(f"[AGENT TOOL] Generated {len(media_list)} images, total tokens: {total_image_tokens}")
            logger.info(f"[AGENT TOOL] Returning media_ids: {media_ids}")

            return {
                'media_ids': media_ids,
                'images': media_list,
                'count': len(media_list),
                'layout': layout_type,
                'layout_description': layout_config['description'],
                'success': True,
                'message': f'Đã tạo {len(media_list)} hình ảnh với bố cục {layout_config["description"]}',
                'image_generation_tokens': {
                    'prompt_tokens': total_image_prompt_tokens,
                    'output_tokens': total_image_output_tokens,
                    'total_tokens': total_image_tokens
                }
            }
        except Exception as e:
            logger.error(f"[AGENT TOOL] Error generating images: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }

    @staticmethod
    def save_agent_post(
        user: User,
        content: str,
        image_id: int = None,
        image_ids: list = None,
        target_account_id: int = None,
        page_context: str = None,
        layout: str = None
    ) -> Dict:
        """Tool: Lưu bài đăng hoàn chỉnh vào database

        CHỈ LƯU, không generate. Content và image phải được tạo trước bằng:
        - generate_post_content -> content
        - generate_post_image -> image_ids (từ media_ids)

        Args:
            content: Nội dung đã generate từ generate_post_content
            image_id: ID của 1 image (backward compatible)
            image_ids: List các image IDs từ generate_post_image
            target_account_id: ID của page sẽ đăng bài này (từ get_connected_accounts)
            page_context: Tên page để reference
            layout: Layout type (single, two_square, one_large_two_small, etc.)
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[AGENT TOOL] save_agent_post called with:")
        logger.info(f"  - content length: {len(content)} chars")
        logger.info(f"  - content preview: {content[:200]}...")
        logger.info(f"  - image_id: {image_id}")
        logger.info(f"  - image_ids: {image_ids}")
        logger.info(f"  - target_account_id: {target_account_id}")
        logger.info(f"  - page_context: {page_context}")
        logger.info(f"  - layout: {layout}")

        try:
            full_content = content

            # Add page context if provided
            if page_context:
                logger.info(f"[AGENT TOOL] Adding page_context: {page_context}")
                full_content += f"\n\n📍 {page_context}"

            # Collect all image IDs (support both single and multiple)
            all_image_ids = []
            if image_ids:
                # Handle case where LLM returns string representation of list
                if isinstance(image_ids, str):
                    try:
                        import json
                        image_ids = json.loads(image_ids)
                    except json.JSONDecodeError:
                        # Try eval as fallback (for cases like "[208.0, 209.0]")
                        try:
                            image_ids = eval(image_ids)
                        except:
                            image_ids = []

                # Convert each to int in case LLM returns floats
                if isinstance(image_ids, (list, tuple)):
                    all_image_ids = [int(float(i)) for i in image_ids if i]
                else:
                    logger.warning(f"[AGENT TOOL] image_ids is not a list: {type(image_ids)} - {image_ids}")

            if not all_image_ids and image_id:
                # Fallback to single image_id
                try:
                    all_image_ids = [int(float(image_id))]
                except (ValueError, TypeError):
                    logger.warning(f"[AGENT TOOL] Cannot parse image_id: {image_id}")

            # Determine layout based on image count if not provided
            image_count = len(all_image_ids)
            if not layout and image_count > 0:
                layout_map = {1: 'single', 2: 'two_square', 3: 'one_large_two_small', 4: 'four_square', 5: 'two_large_three_small'}
                layout = layout_map.get(image_count, 'grid')

            # Get main image (first one)
            main_image = None
            if all_image_ids:
                try:
                    main_image = Media.objects.get(id=all_image_ids[0])
                    logger.info(f"[AGENT TOOL] Found main image: {main_image.file_url}")
                except Media.DoesNotExist:
                    logger.warning(f"[AGENT TOOL] Main image {all_image_ids[0]} not found")

            # Build strategy with layout info
            strategy = {
                'layout': layout,
                'image_count': image_count
            }
            if page_context:
                strategy['page_context'] = page_context

            # Get target account if provided
            target_account = None
            target_account_name = None
            if target_account_id:
                try:
                    target_account = SocialAccount.objects.get(id=target_account_id, user=user)
                    target_account_name = target_account.name
                    logger.info(f"[AGENT TOOL] Target account: {target_account_name}")
                except SocialAccount.DoesNotExist:
                    logger.warning(f"[AGENT TOOL] Target account {target_account_id} not found")

            # Clean markdown và extract hashtags
            clean_content = clean_markdown_from_content(full_content)
            content_without_tags, extracted_hashtags = extract_hashtags_from_content(clean_content)
            logger.info(f"[AGENT TOOL] Extracted {len(extracted_hashtags)} hashtags: {extracted_hashtags[:5]}...")

            # Create AgentPost
            agent_post = AgentPost.objects.create(
                user=user,
                content=content_without_tags,
                hashtags=extracted_hashtags,
                full_content=clean_content,
                generated_image=main_image,
                target_account=target_account,
                generation_strategy=strategy,
                status='completed',
                completed_at=timezone.now()
            )

            # Save ALL images to AgentPostImage
            saved_images = []
            for idx, img_id in enumerate(all_image_ids):
                try:
                    media = Media.objects.get(id=img_id)
                    post_image = AgentPostImage.objects.create(
                        agent_post=agent_post,
                        media=media,
                        order=idx,
                        variation=idx + 1
                    )
                    saved_images.append({
                        'id': post_image.id,
                        'media_id': media.id,
                        'url': media.file_url,
                        'order': idx
                    })
                    logger.info(f"[AGENT TOOL] Saved image {idx + 1}: {media.file_url}")
                except Media.DoesNotExist:
                    logger.warning(f"[AGENT TOOL] Image {img_id} not found, skipping")

            logger.info(f"[AGENT TOOL] Saved post {agent_post.id}")

            # Build success message
            target_info = f" cho page '{target_account_name}'" if target_account_name else ""
            page_info = f" (context: {page_context})" if page_context and not target_account_name else ""
            image_info = " với hình ảnh" if main_image else ""

            return {
                'post_id': agent_post.id,
                'content': agent_post.content[:200] + '...' if len(agent_post.content) > 200 else agent_post.content,
                'image_url': main_image.file_url if main_image else None,
                'images': saved_images,
                'target_account_id': target_account.id if target_account else None,
                'target_account_name': target_account_name,
                'page_context': page_context,
                'success': True,
                'message': f'Bài đăng #{agent_post.id} đã được lưu thành công{target_info}{page_info}{image_info}!'
            }

        except Exception as e:
            logger.error(f"[AGENT TOOL] Error saving post: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }

    @staticmethod
    def get_agent_post_details(user: User, post_id: int) -> Dict:
        """Tool: Lấy chi tiết bài đăng Agent đã tạo"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] get_agent_post_details called: post_id={post_id}")

        try:
            post = AgentPost.objects.prefetch_related('images__media').get(id=post_id, user=user)

            # Get images info
            images = []
            for img in post.images.all().order_by('order'):
                if img.media:
                    images.append({
                        'id': img.media.id,
                        'url': img.media.file_url,
                        'order': img.order
                    })

            return {
                'success': True,
                'post_id': post.id,
                'content': post.content,
                'full_content': post.full_content,
                'hashtags': post.hashtags or [],
                'status': post.status,
                'created_at': post.created_at.isoformat() if post.created_at else None,
                'image_count': len(images),
                'images': images,
                'agent_reasoning': post.agent_reasoning,
                'generation_strategy': post.generation_strategy
            }

        except AgentPost.DoesNotExist:
            return {
                'success': False,
                'error': f'Không tìm thấy bài đăng #{post_id}'
            }
        except Exception as e:
            logger.error(f"[AGENT TOOL] Error getting post details: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def edit_agent_post(
        user: User,
        post_id: int,
        new_content: str = None,
        new_hashtags: List[str] = None,
        regenerate_images: bool = False,
        image_count: int = 3
    ) -> Dict:
        """Tool: Chỉnh sửa bài đăng Agent đã tạo"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] edit_agent_post called: post_id={post_id}")

        try:
            post = AgentPost.objects.prefetch_related('images__media').get(id=post_id, user=user)

            # Update content if provided
            if new_content:
                post.content = new_content
                post.full_content = new_content
                logger.info(f"[AGENT TOOL] Updated content for post {post_id}")

            # Update hashtags if provided
            if new_hashtags is not None:
                post.hashtags = new_hashtags
                logger.info(f"[AGENT TOOL] Updated hashtags for post {post_id}")

            post.save()

            result = {
                'post_id': post.id,
                'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
                'hashtags': post.hashtags,
                'success': True,
                'message': f'Đã cập nhật bài đăng #{post.id}'
            }

            # If regenerate_images is requested, generate new images
            if regenerate_images and new_content:
                logger.info(f"[AGENT TOOL] Regenerating images for post {post_id}")
                image_result = AgentToolExecutor.generate_post_image(
                    user=user,
                    post_content=new_content,
                    count=image_count
                )

                if image_result.get('success'):
                    # Delete old images
                    post.images.all().delete()

                    # Link new images to post
                    new_image_ids = image_result.get('media_ids', [])
                    for idx, img_id in enumerate(new_image_ids):
                        try:
                            media = Media.objects.get(id=img_id)
                            AgentPostImage.objects.create(
                                agent_post=post,
                                media=media,
                                order=idx,
                                variation=idx + 1
                            )
                        except Media.DoesNotExist:
                            pass

                    # Update main image reference
                    if new_image_ids:
                        post.generated_image_id = new_image_ids[0]
                        post.save()

                    result['new_images'] = image_result.get('images', [])
                    result['message'] += ' và tạo ảnh mới'

            return result

        except AgentPost.DoesNotExist:
            return {
                'success': False,
                'error': f'Không tìm thấy bài đăng #{post_id}'
            }
        except Exception as e:
            logger.error(f"[AGENT TOOL] Error editing post: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def batch_edit_agent_posts(
        user: User,
        post_ids: List[int],
        new_content: str = None,
        new_hashtags: List[str] = None,
        edit_instruction: str = None,
        regenerate_images: bool = False,
        image_count: int = 3
    ) -> Dict:
        """Tool: Chỉnh sửa nhiều bài đăng Agent cùng lúc

        Args:
            post_ids: Danh sách ID các bài đăng cần sửa
            new_content: Nội dung mới (áp dụng cho tất cả - ít dùng)
            new_hashtags: Hashtags mới (áp dụng cho tất cả)
            edit_instruction: Hướng dẫn sửa đổi (AI sẽ áp dụng cho từng bài)
            regenerate_images: Có tạo lại ảnh mới không
            image_count: Số ảnh nếu tạo lại
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] batch_edit_agent_posts called: post_ids={post_ids}")

        # Handle case where post_ids might be passed as string
        if isinstance(post_ids, str):
            try:
                import json
                post_ids = json.loads(post_ids)
            except json.JSONDecodeError:
                try:
                    post_ids = eval(post_ids)
                except:
                    return {
                        'success': False,
                        'error': 'Invalid post_ids format'
                    }

        # Convert to list of integers
        try:
            post_ids = [int(float(pid)) for pid in post_ids if pid]
        except (ValueError, TypeError):
            return {
                'success': False,
                'error': 'Invalid post_ids format'
            }

        if not post_ids:
            return {
                'success': False,
                'error': 'Không có bài đăng nào được chọn'
            }

        results = []
        success_count = 0
        fail_count = 0

        for post_id in post_ids:
            try:
                post = AgentPost.objects.prefetch_related('images__media').get(id=post_id, user=user)

                # If we have edit_instruction, use AI to modify content
                if edit_instruction and not new_content:
                    # Generate new content based on instruction
                    prompt = f"""
Bài đăng hiện tại:
{post.content}

Hashtags hiện tại: {', '.join(post.hashtags or [])}

Yêu cầu chỉnh sửa: {edit_instruction}

Hãy chỉnh sửa bài đăng theo yêu cầu trên. Giữ nguyên ý chính, chỉ thay đổi theo yêu cầu.
Viết lại nội dung bài đăng hoàn chỉnh (không ghi label).
"""
                    from apps.ai.services import AIContentService
                    ai_result = AIContentService.generate_content(
                        prompt=prompt,
                        tone='casual',
                        include_hashtags=True,
                        language='vi'
                    )
                    edited_content = ai_result.get('content', post.content)
                    post.content = edited_content
                    post.full_content = edited_content
                    logger.info(f"[AGENT TOOL] AI edited content for post {post_id}")
                elif new_content:
                    post.content = new_content
                    post.full_content = new_content

                # Update hashtags if provided
                if new_hashtags is not None:
                    post.hashtags = new_hashtags

                post.save()

                result_item = {
                    'post_id': post.id,
                    'success': True,
                    'content_preview': post.content[:100] + '...' if len(post.content) > 100 else post.content
                }

                # Regenerate images if requested
                if regenerate_images:
                    logger.info(f"[AGENT TOOL] Regenerating images for post {post_id}")
                    image_result = AgentToolExecutor.generate_post_image(
                        user=user,
                        post_content=post.content,
                        count=image_count
                    )

                    if image_result.get('success'):
                        # Delete old images
                        post.images.all().delete()

                        # Link new images to post
                        new_image_ids = image_result.get('media_ids', [])
                        for idx, img_id in enumerate(new_image_ids):
                            try:
                                media = Media.objects.get(id=img_id)
                                AgentPostImage.objects.create(
                                    agent_post=post,
                                    media=media,
                                    order=idx,
                                    variation=idx + 1
                                )
                            except Media.DoesNotExist:
                                pass

                        # Update main image reference
                        if new_image_ids:
                            post.generated_image_id = new_image_ids[0]
                            post.save()

                        result_item['new_images'] = len(new_image_ids)

                results.append(result_item)
                success_count += 1

            except AgentPost.DoesNotExist:
                results.append({
                    'post_id': post_id,
                    'success': False,
                    'error': f'Không tìm thấy bài đăng #{post_id}'
                })
                fail_count += 1
            except Exception as e:
                logger.error(f"[AGENT TOOL] Error editing post {post_id}: {str(e)}")
                results.append({
                    'post_id': post_id,
                    'success': False,
                    'error': str(e)
                })
                fail_count += 1

        return {
            'success': success_count > 0,
            'total': len(post_ids),
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results,
            'message': f'Đã cập nhật {success_count}/{len(post_ids)} bài đăng' + (f' ({fail_count} thất bại)' if fail_count > 0 else '')
        }

    @staticmethod
    def analyze_schedule(user: User, schedule_id: int = None) -> Dict:
        """Tool: Phân tích lịch đăng"""
        if schedule_id:
            # Analyze specific schedule
            try:
                schedule = PostingSchedule.objects.get(id=schedule_id, user=user)
                posts_count = schedule.posts.count()

                return {
                    'schedule_id': schedule.id,
                    'business_type': schedule.business_type,
                    'total_posts': posts_count,
                    'duration': schedule.duration,
                    'posts_per_day': schedule.posts_per_day,
                    'insights': f"Lịch này có {posts_count} bài đăng trong {schedule.duration}"
                }
            except PostingSchedule.DoesNotExist:
                return {'error': 'Schedule not found'}
        else:
            # Analyze all schedules
            schedules = PostingSchedule.objects.filter(user=user)
            total = schedules.count()

            return {
                'total_schedules': total,
                'insights': f"Bạn có {total} lịch đăng bài được tạo"
            }

    @staticmethod
    def get_connected_accounts(
        user: User,
        platform: str = None,
        active_only: bool = True
    ) -> Dict:
        """Tool: Lấy danh sách tài khoản/pages đang kết nối"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] ========== get_connected_accounts called! ==========")
        logger.info(f"[AGENT TOOL] platform={platform}, active_only={active_only}")

        # Lấy tất cả pages trong hệ thống (tạm thời không phân quyền)
        queryset = SocialAccount.objects.all()
        logger.info(f"[AGENT TOOL] Total pages in DB: {queryset.count()}")

        # Log all page names for debugging
        all_names = list(queryset.values_list('name', flat=True))
        logger.info(f"[AGENT TOOL] All page names in DB: {all_names}")

        # Filter by platform if specified
        if platform:
            queryset = queryset.filter(platform=platform.lower())

        # Filter by active status
        if active_only:
            queryset = queryset.filter(is_active=True)

        accounts = []
        for account in queryset:
            # Check token status
            token_status = 'valid'
            if account.is_token_expired():
                token_status = 'expired'
            elif account.token_expires_at:
                # Check if expiring soon (within 7 days)
                days_until_expiry = (account.token_expires_at - timezone.now()).days
                if days_until_expiry <= 7:
                    token_status = f'expiring_soon ({days_until_expiry} days)'

            accounts.append({
                'id': account.id,
                'platform': account.platform,
                'platform_account_id': account.platform_account_id,
                'name': account.name,
                'username': account.username or '',
                'category': account.category or '',  # Loại hình kinh doanh của page
                'profile_picture_url': account.profile_picture_url or '',
                'is_active': account.is_active,
                'is_verified': account.is_verified,
                'token_status': token_status,
                'connected_at': account.created_at.strftime('%Y-%m-%d %H:%M'),
                'last_synced': account.last_synced_at.strftime('%Y-%m-%d %H:%M') if account.last_synced_at else None
            })

        # Summary by platform
        platform_summary = {}
        for acc in accounts:
            p = acc['platform']
            if p not in platform_summary:
                platform_summary[p] = 0
            platform_summary[p] += 1

        # Create a clear list of page names for easy reference
        page_names_list = [acc['name'] for acc in accounts]

        return {
            'total': len(accounts),
            'page_names': page_names_list,  # List of exact names to use
            'accounts': accounts,
            'platform_summary': platform_summary,
            'message': f'Đang có {len(accounts)} tài khoản/pages được kết nối',
            'IMPORTANT': f'CHỈ SỬ DỤNG các tên pages sau: {", ".join(page_names_list)}',
            'tip': 'Sử dụng category của page làm business_type khi tạo bài đăng để nội dung phù hợp hơn'
        }

    @staticmethod
    def update_page_info(
        user: User,
        account_id: int,
        about: str = None,
        description: str = None,
        phone: str = None,
        website: str = None,
        emails: List[str] = None
    ) -> Dict:
        """Tool: Cập nhật thông tin Facebook page"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] update_page_info called: account_id={account_id}")

        try:
            from apps.platforms.services.facebook import FacebookService

            # Lấy account từ DB
            account = SocialAccount.objects.get(id=account_id)

            if account.platform != 'facebook':
                return {
                    'success': False,
                    'error': f'Page này không phải Facebook page (platform: {account.platform})'
                }

            # Gọi FacebookService
            fb_service = FacebookService()
            result = fb_service.update_page_info(
                access_token=account.access_token,
                page_id=account.platform_account_id,
                about=about,
                description=description,
                phone=phone,
                website=website,
                emails=emails
            )

            if result.get('success'):
                # Cập nhật thông tin vào database nếu cần
                updated_fields = []
                if about is not None:
                    updated_fields.append('about')
                if description is not None:
                    updated_fields.append('description')
                if phone is not None:
                    updated_fields.append('phone')
                if website is not None:
                    updated_fields.append('website')
                if emails is not None:
                    updated_fields.append('emails')

                result['page_name'] = account.name
                result['updated_fields'] = updated_fields
                result['message'] = f"Đã cập nhật {', '.join(updated_fields)} cho page {account.name}"

            return result

        except SocialAccount.DoesNotExist:
            return {
                'success': False,
                'error': f'Không tìm thấy page với ID {account_id}'
            }
        except Exception as e:
            logger.error(f"[AGENT TOOL] Error updating page info: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def update_page_photo(
        user: User,
        account_id: int,
        photo_type: str,  # 'picture' or 'cover'
        media_id: int = None,
        image_url: str = None
    ) -> Dict:
        """Tool: Cập nhật ảnh đại diện hoặc ảnh bìa page"""
        import logging
        from apps.media.models import Media
        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] update_page_photo called: account_id={account_id}, photo_type={photo_type}")

        try:
            from apps.platforms.services.facebook import FacebookService

            # Lấy account từ DB
            account = SocialAccount.objects.get(id=account_id)

            if account.platform != 'facebook':
                return {
                    'success': False,
                    'error': f'Page này không phải Facebook page (platform: {account.platform})'
                }

            # Validate photo_type
            if photo_type not in ['picture', 'cover']:
                return {
                    'success': False,
                    'error': f"photo_type phải là 'picture' hoặc 'cover', nhận được: {photo_type}"
                }

            # Lấy local file path nếu có media_id
            local_path = None
            if media_id:
                try:
                    media = Media.objects.get(id=media_id)
                    local_path = media.file_path
                    if not image_url:
                        image_url = media.file_url
                    logger.info(f"[AGENT TOOL] Using media {media_id}: {local_path}")
                except Media.DoesNotExist:
                    return {
                        'success': False,
                        'error': f'Không tìm thấy media với ID {media_id}'
                    }

            if not local_path and not image_url:
                return {
                    'success': False,
                    'error': 'Cần cung cấp media_id hoặc image_url'
                }

            fb_service = FacebookService()

            if photo_type == 'cover':
                result = fb_service.update_page_cover(
                    access_token=account.access_token,
                    page_id=account.platform_account_id,
                    image_url=image_url,
                    image_file_path=local_path
                )
                photo_type_display = 'ảnh bìa'
            else:
                result = fb_service.update_page_picture(
                    access_token=account.access_token,
                    page_id=account.platform_account_id,
                    image_url=image_url,
                    image_file_path=local_path
                )
                photo_type_display = 'ảnh đại diện'

            if result.get('success'):
                result['page_name'] = account.name
                result['message'] = f"Đã cập nhật {photo_type_display} cho page {account.name}"

            return result

        except SocialAccount.DoesNotExist:
            return {
                'success': False,
                'error': f'Không tìm thấy page với ID {account_id}'
            }
        except Exception as e:
            logger.error(f"[AGENT TOOL] Error updating page photo: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def batch_update_pages_info(
        user: User,
        account_ids: List[int],
        about: str = None,
        description: str = None,
        phone: str = None,
        website: str = None,
        emails: List[str] = None
    ) -> Dict:
        """Tool: Cập nhật thông tin cho nhiều pages cùng lúc"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] batch_update_pages_info called: account_ids={account_ids}")

        # Handle case where account_ids might be passed as string
        if isinstance(account_ids, str):
            try:
                import json
                account_ids = json.loads(account_ids)
            except json.JSONDecodeError:
                try:
                    account_ids = eval(account_ids)
                except:
                    return {
                        'success': False,
                        'error': 'Invalid account_ids format'
                    }

        # Convert to list of integers
        try:
            account_ids = [int(float(aid)) for aid in account_ids if aid]
        except (ValueError, TypeError):
            return {
                'success': False,
                'error': 'Invalid account_ids format'
            }

        if not account_ids:
            return {
                'success': False,
                'error': 'Không có page nào được chọn'
            }

        results = []
        success_count = 0
        fail_count = 0

        for account_id in account_ids:
            result = AgentToolExecutor.update_page_info(
                user=user,
                account_id=account_id,
                about=about,
                description=description,
                phone=phone,
                website=website,
                emails=emails
            )

            if result.get('success'):
                success_count += 1
                results.append({
                    'account_id': account_id,
                    'page_name': result.get('page_name', ''),
                    'success': True
                })
            else:
                fail_count += 1
                results.append({
                    'account_id': account_id,
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                })

        # Build updated fields list for message
        updated_fields = []
        if about is not None:
            updated_fields.append('about')
        if description is not None:
            updated_fields.append('description')
        if phone is not None:
            updated_fields.append('phone')
        if website is not None:
            updated_fields.append('website')
        if emails is not None:
            updated_fields.append('emails')

        return {
            'success': success_count > 0,
            'total': len(account_ids),
            'success_count': success_count,
            'fail_count': fail_count,
            'updated_fields': updated_fields,
            'results': results,
            'message': f'Đã cập nhật {", ".join(updated_fields)} cho {success_count}/{len(account_ids)} pages' + (f' ({fail_count} thất bại)' if fail_count > 0 else '')
        }

    @staticmethod
    def edit_image(
        user: User,
        edit_instruction: str,
        source_image_data: str = None,
        source_media_id: int = None,
        agent_post_id: int = None,
        agent_post_image_index: int = 0,
        overlay_image_data: str = None,
        overlay_media_id: int = None,
        text_to_add: str = None,
        update_post: bool = True,
        use_brand_settings: bool = False,  # Use logo/settings from AgentSettings
        target_size: str = None  # Target size (WIDTHxHEIGHT), None = keep original size
    ) -> Dict:
        """Tool: Chỉnh sửa hình ảnh bằng AI"""
        import logging
        import base64
        import os
        import tempfile
        from django.conf import settings
        from .models import AgentSettings

        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] edit_image called with instruction: {edit_instruction}, use_brand_settings={use_brand_settings}")

        try:
            # ===== 1. COLLECT REFERENCE IMAGES =====
            reference_images = []
            agent_post = None

            # Get source image
            if source_image_data:
                # Save base64 to temp file
                try:
                    if ',' in source_image_data:
                        source_image_data = source_image_data.split(',')[1]
                    img_bytes = base64.b64decode(source_image_data)
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    temp_file.write(img_bytes)
                    temp_file.close()
                    reference_images.append(temp_file.name)
                    logger.info(f"[AGENT TOOL] Saved source image to {temp_file.name}")
                except Exception as e:
                    logger.error(f"[AGENT TOOL] Error decoding source_image_data: {e}")

            elif source_media_id:
                try:
                    source_media = Media.objects.get(id=source_media_id)
                    file_path = source_media.file_path
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(settings.MEDIA_ROOT, file_path.lstrip('/media/'))
                    if os.path.exists(file_path):
                        reference_images.append(file_path)
                        logger.info(f"[AGENT TOOL] Using source media {source_media_id}: {file_path}")
                except Media.DoesNotExist:
                    return {'success': False, 'error': f'Không tìm thấy ảnh với ID {source_media_id}'}

            elif agent_post_id:
                try:
                    agent_post = AgentPost.objects.prefetch_related('images__media').get(id=agent_post_id, user=user)
                    images = list(agent_post.images.all().order_by('order'))
                    if not images:
                        return {'success': False, 'error': f'Bài đăng #{agent_post_id} không có ảnh'}

                    if agent_post_image_index >= len(images):
                        agent_post_image_index = 0
                    target_image = images[agent_post_image_index]
                    source_media = target_image.media

                    file_path = source_media.file_path
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(settings.MEDIA_ROOT, file_path.lstrip('/media/'))
                    if os.path.exists(file_path):
                        reference_images.append(file_path)
                        logger.info(f"[AGENT TOOL] Using image from post {agent_post_id}: {file_path}")
                except AgentPost.DoesNotExist:
                    return {'success': False, 'error': f'Không tìm thấy bài đăng #{agent_post_id}'}

            # Get overlay image (logo, sticker...)
            if overlay_image_data:
                try:
                    if ',' in overlay_image_data:
                        overlay_image_data = overlay_image_data.split(',')[1]
                    img_bytes = base64.b64decode(overlay_image_data)
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    temp_file.write(img_bytes)
                    temp_file.close()
                    reference_images.append(temp_file.name)
                    logger.info(f"[AGENT TOOL] Saved overlay image to {temp_file.name}")
                except Exception as e:
                    logger.error(f"[AGENT TOOL] Error decoding overlay_image_data: {e}")

            elif overlay_media_id:
                try:
                    overlay_media = Media.objects.get(id=overlay_media_id)
                    file_path = overlay_media.file_path
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(settings.MEDIA_ROOT, file_path.lstrip('/media/'))
                    if os.path.exists(file_path):
                        reference_images.append(file_path)
                        logger.info(f"[AGENT TOOL] Using overlay media {overlay_media_id}: {file_path}")
                except Media.DoesNotExist:
                    logger.warning(f"[AGENT TOOL] Overlay media {overlay_media_id} not found")

            # NEW: Use logo from AgentSettings if requested
            brand_settings_info = None
            if use_brand_settings:
                agent_settings = AgentSettings.objects.filter(user=user).first()
                if agent_settings and agent_settings.logo:
                    logo_path = agent_settings.logo.file_path
                    if not os.path.isabs(logo_path):
                        logo_path = os.path.join(settings.MEDIA_ROOT, logo_path.lstrip('/media/'))
                    if os.path.exists(logo_path):
                        reference_images.append(logo_path)
                        # Store settings for prompt
                        position_map = {
                            'top_left': 'góc trên bên trái',
                            'top_right': 'góc trên bên phải',
                            'bottom_left': 'góc dưới bên trái',
                            'bottom_right': 'góc dưới bên phải',
                            'center': 'giữa ảnh'
                        }
                        brand_settings_info = {
                            'logo_position': position_map.get(agent_settings.logo_position, 'góc dưới bên phải'),
                            'logo_size': agent_settings.logo_size or 15,
                            'hotline': agent_settings.hotline if agent_settings.auto_add_hotline else None,
                            'slogan': agent_settings.slogan
                        }
                        logger.info(f"[AGENT TOOL] Using brand logo from settings: {logo_path}, position={brand_settings_info['logo_position']}, size={brand_settings_info['logo_size']}%")
                else:
                    logger.warning("[AGENT TOOL] use_brand_settings=True but no logo found in AgentSettings")

            if not reference_images:
                return {'success': False, 'error': 'Cần cung cấp ảnh gốc (source_image_data, source_media_id hoặc agent_post_id)'}

            # ===== 1.5. DETERMINE TARGET SIZE =====
            # Priority: target_size param > original image size > default 1080x1080
            from PIL import Image as PILImage
            final_size = target_size

            if not final_size and reference_images:
                # Get original image size
                try:
                    with PILImage.open(reference_images[0]) as img:
                        orig_width, orig_height = img.size
                        final_size = f"{orig_width}x{orig_height}"
                        logger.info(f"[AGENT TOOL] Detected original image size: {final_size}")
                except Exception as e:
                    logger.warning(f"[AGENT TOOL] Could not detect original size: {e}, using default 1080x1080")
                    final_size = '1080x1080'

            if not final_size:
                final_size = '1080x1080'

            logger.info(f"[AGENT TOOL] Final target size for edit: {final_size}")

            # ===== 2. BUILD EDIT PROMPT =====
            # Detect if this is "add element" (keep original) or "modify" (can change)
            add_keywords = ['thêm', 'add', 'chèn', 'đặt', 'insert', 'overlay', 'watermark', 'logo', 'viền', 'border', 'text']
            is_add_element = any(kw in edit_instruction.lower() for kw in add_keywords)

            # Build brand settings prompt section
            brand_prompt = ""
            if brand_settings_info:
                brand_prompt = f"""
THÔNG TIN BRAND/LOGO:
- ẢNH THỨ 2 LÀ LOGO cần thêm vào ảnh gốc
- Vị trí đặt logo: {brand_settings_info['logo_position']}
- Kích thước logo: khoảng {brand_settings_info['logo_size']}% so với ảnh
"""
                if brand_settings_info.get('hotline'):
                    brand_prompt += f"- Hotline cần hiển thị: {brand_settings_info['hotline']}\n"
                if brand_settings_info.get('slogan'):
                    brand_prompt += f"- Slogan: {brand_settings_info['slogan']}\n"

            if is_add_element:
                # For adding elements - emphasize keeping original image intact
                # Check if adding text
                is_adding_text = text_to_add or any(kw in edit_instruction.lower() for kw in ['text', 'chữ', 'viết', 'ghi'])

                text_design_guide = ""
                if is_adding_text:
                    text_design_guide = """
HƯỚNG DẪN THIẾT KẾ TEXT ĐẸP:
- Font chữ: Sử dụng font hiện đại, dễ đọc (không dùng font cứng nhắc)
- Style: Thêm hiệu ứng để text nổi bật nhưng hài hòa với ảnh (shadow, gradient, outline mềm)
- Màu sắc: Chọn màu phù hợp với tone màu của ảnh gốc, đảm bảo contrast tốt
- Kích thước: Vừa phải, không quá to che mất ảnh, không quá nhỏ khó đọc
- Bố cục: Đặt text ở vị trí hài hòa, có padding/margin phù hợp
- Nền text (nếu cần): Có thể thêm background mờ/gradient nhẹ để text dễ đọc hơn
- QUAN TRỌNG: Text phải trông CHUYÊN NGHIỆP như thiết kế quảng cáo/marketing
"""

                prompt = f"""CHỈNH SỬA ẢNH - GIỮ NGUYÊN NỘI DUNG GỐC

YÊU CẦU QUAN TRỌNG:
- GIỮ NGUYÊN 100% nội dung, chi tiết, màu sắc của ảnh gốc (ảnh đầu tiên)
- CHỈ THÊM các element theo yêu cầu bên dưới
- KHÔNG thay đổi bất kỳ chi tiết nào của ảnh gốc
- Element được thêm phải có THIẾT KẾ ĐẸP, CHUYÊN NGHIỆP như poster quảng cáo

YÊU CẦU CHỈNH SỬA:
{edit_instruction}

{"TEXT CẦN THÊM: " + text_to_add if text_to_add else ""}
{text_design_guide}
{brand_prompt if brand_settings_info else ("ẢNH THỨ 2 LÀ LOGO/ELEMENT CẦN THÊM VÀO ẢNH GỐC." if len(reference_images) > 1 else "")}
"""
            else:
                # For modifications - AI can change the image
                prompt = f"""CHỈNH SỬA ẢNH THEO YÊU CẦU

Dựa trên ảnh gốc được cung cấp, thực hiện các thay đổi sau:

{edit_instruction}

{"TEXT CẦN THÊM: " + text_to_add if text_to_add else ""}

Hãy tạo ra phiên bản ảnh mới với các thay đổi theo yêu cầu.
"""

            logger.info(f"[AGENT TOOL] Edit prompt (is_add_element={is_add_element}):\n{prompt[:500]}...")

            # ===== 3. CALL AI IMAGE SERVICE =====
            gen_result = AIImageService.generate_image(
                prompt=prompt,
                user=user,
                size=final_size,  # Use target size or original image size
                creativity='low',  # Always use 'low' for most photorealistic results
                reference_images=reference_images,
                count=1
            )

            results = gen_result.get('images', [])
            image_tokens = gen_result.get('token_usage', {})

            if not results or len(results) == 0:
                return {'success': False, 'error': 'AI không thể tạo ảnh đã chỉnh sửa'}

            # ===== 4. SAVE EDITED IMAGE =====
            result = results[0]
            new_media = Media.objects.create(
                user=user,
                file_url=result['file_url'],
                file_path=result['file_path'],
                file_type='image',
                file_size=result['file_size'],
                width=result['width'],
                height=result['height']
            )

            logger.info(f"[AGENT TOOL] Created new media {new_media.id}: {new_media.file_url}")

            response = {
                'success': True,
                'media_id': new_media.id,
                'file_url': new_media.file_url,
                'width': new_media.width,
                'height': new_media.height,
                'edit_type': 'add_element' if is_add_element else 'modify',
                'message': f'Đã chỉnh sửa ảnh thành công!',
                'image_generation_tokens': {
                    'prompt_tokens': image_tokens.get('prompt_tokens', 0),
                    'output_tokens': image_tokens.get('output_tokens', 0),
                    'total_tokens': image_tokens.get('total_tokens', 0)
                }
            }

            # ===== 5. UPDATE AGENT POST IF REQUESTED =====
            if agent_post and update_post:
                old_image = agent_post.images.filter(order=agent_post_image_index).first()
                if old_image:
                    old_image.media = new_media
                    old_image.save()
                    logger.info(f"[AGENT TOOL] Updated post {agent_post_id} image at index {agent_post_image_index}")

                if agent_post_image_index == 0:
                    agent_post.generated_image = new_media
                    agent_post.save()

                response['agent_post_id'] = agent_post_id
                response['message'] = f'Đã chỉnh sửa ảnh bài đăng #{agent_post_id}!'

            # Cleanup temp files
            for ref_path in reference_images:
                if ref_path.startswith(tempfile.gettempdir()):
                    try:
                        os.unlink(ref_path)
                    except:
                        pass

            return response

        except Exception as e:
            logger.error(f"[AGENT TOOL] Error editing image: {str(e)}")
            import traceback
            logger.error(f"[AGENT TOOL] Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def batch_add_text_to_images(
        user: User,
        image_text_pairs: list,  # [{media_id: int, text: str}, ...]
        text_position: str = "bottom_left",  # top_left, top_right, bottom_left, bottom_right, center
        text_style: str = "modern",  # modern, elegant, bold, minimal, neon
        text_color: str = None,  # hex color or None for auto
        font_size: str = "medium",  # small, medium, large
        use_brand_settings: bool = False
    ) -> Dict:
        """Tool: Thêm text vào NHIỀU ảnh với style THỐNG NHẤT"""
        import logging
        import os
        from django.conf import settings
        from .models import AgentSettings

        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] batch_add_text_to_images called with {len(image_text_pairs)} images, style={text_style}, position={text_position}")

        try:
            results = []
            total_tokens = {'prompt_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}

            # Get brand settings if requested
            brand_info = ""
            if use_brand_settings:
                agent_settings = AgentSettings.objects.filter(user=user).first()
                if agent_settings:
                    if agent_settings.slogan:
                        brand_info += f"\nSlogan thương hiệu: {agent_settings.slogan}"
                    if agent_settings.hotline and agent_settings.auto_add_hotline:
                        brand_info += f"\nHotline: {agent_settings.hotline}"

            # Position mapping
            position_map = {
                'top_left': 'góc trên bên trái',
                'top_right': 'góc trên bên phải',
                'bottom_left': 'góc dưới bên trái',
                'bottom_right': 'góc dưới bên phải',
                'center': 'giữa ảnh'
            }
            position_text = position_map.get(text_position, 'góc dưới bên trái')

            # Style descriptions
            style_descriptions = {
                'modern': 'font hiện đại sans-serif, clean, với shadow nhẹ',
                'elegant': 'font thanh lịch serif, có gradient subtle, tinh tế',
                'bold': 'font đậm impact, viền trắng/đen, nổi bật mạnh',
                'minimal': 'font đơn giản, không hiệu ứng, tối giản',
                'neon': 'hiệu ứng neon glow sáng, style cyber/gaming'
            }
            style_desc = style_descriptions.get(text_style, style_descriptions['modern'])

            # Font size descriptions
            size_desc = {'small': 'nhỏ vừa phải', 'medium': 'trung bình', 'large': 'to nổi bật'}

            for pair in image_text_pairs:
                media_id = pair.get('media_id')
                text = pair.get('text', '')

                if not media_id or not text:
                    results.append({
                        'media_id': media_id,
                        'success': False,
                        'error': 'Missing media_id or text'
                    })
                    continue

                try:
                    # Get source image
                    source_media = Media.objects.get(id=media_id, user=user)
                    file_path = source_media.file_path
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(settings.MEDIA_ROOT, file_path.lstrip('/media/'))

                    if not os.path.exists(file_path):
                        results.append({
                            'media_id': media_id,
                            'success': False,
                            'error': f'File not found: {file_path}'
                        })
                        continue

                    # Build consistent prompt for all images
                    color_instruction = f"màu {text_color}" if text_color else "màu tự động phù hợp với ảnh (đảm bảo contrast tốt)"

                    prompt = f"""CHỈNH SỬA ẢNH - THÊM TEXT CHUYÊN NGHIỆP

YÊU CẦU QUAN TRỌNG:
- GIỮ NGUYÊN 100% nội dung ảnh gốc
- CHỈ THÊM text vào ảnh

TEXT CẦN THÊM: "{text}"

THIẾT KẾ TEXT (PHẢI TUÂN THỦ CHÍNH XÁC):
- Vị trí: {position_text}
- Style: {style_desc}
- Màu chữ: {color_instruction}
- Kích thước: {size_desc.get(font_size, 'trung bình')}
- Text phải dễ đọc, có padding phù hợp với viền ảnh
- Thiết kế CHUYÊN NGHIỆP như poster marketing
{brand_info}

LƯU Ý: Đây là 1 trong chuỗi ảnh cần thêm text với CÙNG STYLE. Hãy đảm bảo style nhất quán.
"""

                    # Generate edited image
                    gen_result = AIImageService.generate_image(
                        prompt=prompt,
                        user=user,
                        size='1080x1080',
                        creativity='low',
                        reference_images=[file_path],
                        count=1
                    )

                    images = gen_result.get('images', [])
                    tokens = gen_result.get('token_usage', {})

                    total_tokens['prompt_tokens'] += tokens.get('prompt_tokens', 0)
                    total_tokens['output_tokens'] += tokens.get('output_tokens', 0)
                    total_tokens['total_tokens'] += tokens.get('total_tokens', 0)

                    if not images:
                        results.append({
                            'media_id': media_id,
                            'text': text,
                            'success': False,
                            'error': 'AI không thể tạo ảnh'
                        })
                        continue

                    # Save new image
                    img_result = images[0]
                    new_media = Media.objects.create(
                        user=user,
                        file_url=img_result['file_url'],
                        file_path=img_result['file_path'],
                        file_type='image',
                        file_size=img_result['file_size'],
                        width=img_result['width'],
                        height=img_result['height']
                    )

                    results.append({
                        'original_media_id': media_id,
                        'text': text,
                        'success': True,
                        'new_media_id': new_media.id,
                        'file_url': new_media.file_url
                    })

                    logger.info(f"[AGENT TOOL] Added text '{text}' to image {media_id} -> new image {new_media.id}")

                except Media.DoesNotExist:
                    results.append({
                        'media_id': media_id,
                        'success': False,
                        'error': f'Không tìm thấy ảnh ID {media_id}'
                    })
                except Exception as e:
                    results.append({
                        'media_id': media_id,
                        'success': False,
                        'error': str(e)
                    })

            success_count = sum(1 for r in results if r.get('success'))
            fail_count = len(results) - success_count

            return {
                'success': success_count > 0,
                'total': len(image_text_pairs),
                'success_count': success_count,
                'fail_count': fail_count,
                'results': results,
                'text_style': text_style,
                'text_position': text_position,
                'message': f'Đã thêm text vào {success_count}/{len(image_text_pairs)} ảnh với style "{text_style}"',
                'image_generation_tokens': total_tokens
            }

        except Exception as e:
            logger.error(f"[AGENT TOOL] Error in batch_add_text_to_images: {str(e)}")
            import traceback
            logger.error(f"[AGENT TOOL] Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def batch_create_posts(
        user: User,
        source_content: str,
        account_ids: list,
        generate_images: bool = True,
        image_count: int = 3,
        shared_image_ids: list = None,
        shared_image_layout: str = None,
        adaptation_style: str = 'natural',
        business_type: str = None,  # Loại ngành nghề/sản phẩm
        marketing_goals: str = None  # Mục tiêu marketing tổng thể
    ) -> Dict:
        """Tool: Tạo nhiều bài đăng HOÀN CHỈNH từ 1 nội dung gốc cho nhiều pages

        AI viết lại nội dung cho từng page một cách tự nhiên.
        TẠO ẢNH PHÙ HỢP với từng page (dựa trên page_name và adapted_content).

        Args:
            source_content: Nội dung gốc cần adapt
            account_ids: Danh sách account_ids từ get_connected_accounts
            generate_images: Có tạo ảnh mới cho mỗi bài không (default True)
            image_count: Số ảnh tạo cho mỗi bài (default 3)
            shared_image_ids: Nếu có, dùng chung ảnh này cho tất cả bài
            shared_image_layout: Bố cục cho shared images ('single', 'two_square', 'one_large_two_small', 'four_square', 'grid')
            adaptation_style: 'subtle', 'natural', 'localized'
            business_type: Ngành nghề/loại sản phẩm (từ lịch đăng)
            marketing_goals: Mục tiêu marketing tổng thể (từ lịch đăng)
        """
        import logging
        from apps.ai.services import AIContentService

        logger = logging.getLogger(__name__)
        logger.info(f"[AGENT TOOL] batch_create_posts called with:")
        logger.info(f"  - source_content: {source_content[:100]}...")
        logger.info(f"  - account_ids: {account_ids}")
        logger.info(f"  - generate_images: {generate_images}")
        logger.info(f"  - image_count: {image_count}")
        logger.info(f"  - shared_image_ids: {shared_image_ids}")
        logger.info(f"  - shared_image_layout: {shared_image_layout}")
        logger.info(f"  - adaptation_style: {adaptation_style}")
        logger.info(f"  - business_type: {business_type}")
        logger.info(f"  - marketing_goals: {marketing_goals}")

        # Convert image_count to int (LLM may return float like 3.0)
        try:
            image_count = int(image_count) if image_count else 3
        except (ValueError, TypeError):
            image_count = 3

        # Handle account_ids parsing
        if isinstance(account_ids, str):
            try:
                import json
                account_ids = json.loads(account_ids)
            except:
                account_ids = []

        # Convert account_ids to integers (LLM may return floats like [21.0, 18.0])
        try:
            account_ids = [int(float(aid)) for aid in account_ids if aid]
        except (ValueError, TypeError):
            account_ids = []

        if not account_ids:
            return {'success': False, 'error': 'Cần danh sách account_ids'}

        # Parse shared_image_ids
        use_shared_images = False
        all_shared_image_ids = []
        if shared_image_ids:
            use_shared_images = True
            if isinstance(shared_image_ids, str):
                try:
                    import json
                    shared_image_ids = json.loads(shared_image_ids)
                except:
                    shared_image_ids = []
            all_shared_image_ids = [int(i) for i in shared_image_ids if i]

        created_posts = []
        failed = []

        # Track image generation tokens
        total_img_prompt_tokens = 0
        total_img_output_tokens = 0
        total_img_tokens = 0

        # Get AgentSettings for user (logo, hotline, brand colors, etc.)
        from .models import AgentSettings
        agent_settings = AgentSettings.objects.filter(user=user).first()

        # Get all accounts first
        accounts = SocialAccount.objects.filter(id__in=account_ids, user=user)
        account_map = {acc.id: acc for acc in accounts}

        for acc_id in account_ids:
            try:
                if acc_id not in account_map:
                    failed.append({'account_id': acc_id, 'error': 'Account not found'})
                    continue

                account = account_map[acc_id]
                page_name = account.name

                # Adapt content for this page using AI
                adapt_prompt = f"""NHIỆM VỤ: Điều chỉnh nội dung bài đăng cho page "{page_name}"

NỘI DUNG GỐC:
{source_content}

YÊU CẦU:
- Giữ nguyên ý chính, thông điệp của nội dung gốc
- Tích hợp tên page "{page_name}" vào nội dung MỘT CÁCH TỰ NHIÊN
- Không chỉ đơn giản thêm tên vào đầu/cuối, mà điều chỉnh câu từ cho phù hợp
- Nếu page có địa danh (VD: "Bắc Ninh", "Đà Nẵng"), có thể thêm chi tiết địa phương nếu hợp lý
- Giữ giọng văn và tone của bài gốc
- Giữ hashtags nếu có

KIỂU ADAPT: {adaptation_style}
- subtle: Chỉ thêm tên page nhẹ nhàng vào 1-2 chỗ
- natural: Viết lại tự nhiên, tên page xuất hiện hợp lý trong ngữ cảnh
- localized: Customize theo đặc thù địa phương (nếu có)

CHỈ TRẢ VỀ NỘI DUNG ĐÃ ĐIỀU CHỈNH, KHÔNG CẦN GIẢI THÍCH.
"""

                adapted_result = AIContentService.generate_content(
                    prompt=adapt_prompt,
                    tone='casual',
                    include_hashtags=False,
                    language='vi'
                )

                adapted_content = adapted_result.get('content', source_content)

                # Auto-add hotline/website using helper function
                adapted_content = AgentToolExecutor._apply_hotline_to_content(adapted_content, agent_settings)
                if agent_settings and agent_settings.auto_add_hotline:
                    logger.info(f"[AGENT TOOL] batch_create: Auto-added hotline to {page_name}")

                # Handle images
                main_image = None
                all_image_ids = []
                image_urls = []
                image_layout = None
                image_sizes = []

                if use_shared_images and all_shared_image_ids:
                    # Use shared images for all posts
                    all_image_ids = all_shared_image_ids
                    # Use provided layout or auto-detect based on image count
                    if shared_image_layout:
                        image_layout = shared_image_layout
                    else:
                        # Auto-detect layout based on number of images (using FB layout names)
                        # Default to portrait-first layouts for better mobile engagement
                        layout_map = {
                            1: 'single_portrait',
                            2: 'two_portrait',
                            3: 'one_vertical_two_square',  # Portrait LEFT + 2 squares RIGHT
                            4: 'four_square',
                            5: 'five_square'
                        }
                        image_layout = layout_map.get(len(all_image_ids), 'one_vertical_two_square')

                    if all_image_ids:
                        try:
                            main_image = Media.objects.get(id=all_image_ids[0])
                            # Get all image URLs
                            image_urls = []
                            for img_id in all_image_ids:
                                try:
                                    media = Media.objects.get(id=img_id)
                                    image_urls.append(media.file_url)
                                except Media.DoesNotExist:
                                    pass
                        except Media.DoesNotExist:
                            pass

                elif generate_images:
                    # Generate images using the SAME workflow as single post
                    # This ensures FB layout, hero image, logo, brand colors all work identically
                    try:
                        # Build page context từ account name và category
                        page_context = f"{page_name} - {account.category}" if account.category else page_name

                        image_result = AgentToolExecutor.generate_post_image(
                            user=user,
                            post_content=adapted_content,
                            page_context=page_context,
                            count=image_count,
                            business_type=business_type,
                            marketing_goals=marketing_goals
                        )

                        if image_result.get('success'):
                            all_image_ids = image_result.get('media_ids', [])
                            if all_image_ids:
                                main_image = Media.objects.get(id=all_image_ids[0])
                                image_urls = [img['url'] for img in image_result.get('images', [])]
                            # Save layout info for FB display
                            image_layout = image_result.get('layout')
                            image_sizes = image_result.get('sizes', [])
                            # Capture image generation tokens
                            img_tokens = image_result.get('image_generation_tokens', {})
                            total_img_prompt_tokens += img_tokens.get('prompt_tokens', 0)
                            total_img_output_tokens += img_tokens.get('output_tokens', 0)
                            total_img_tokens += img_tokens.get('total_tokens', 0)
                            logger.info(f"[AGENT TOOL] batch_create: Generated {len(all_image_ids)} images for {page_name} (layout: {image_layout}, tokens: {img_tokens.get('total_tokens', 0)})")
                        else:
                            logger.warning(f"[AGENT TOOL] batch_create: generate_post_image failed for {page_name}: {image_result.get('error')}")

                    except Exception as img_err:
                        logger.warning(f"[AGENT TOOL] Could not generate images for {page_name}: {img_err}")

                # Clean markdown và extract hashtags
                clean_adapted = clean_markdown_from_content(adapted_content)
                content_no_tags, hashtags_extracted = extract_hashtags_from_content(clean_adapted)

                # Create AgentPost with target_account
                agent_post = AgentPost.objects.create(
                    user=user,
                    content=content_no_tags,
                    hashtags=hashtags_extracted,
                    full_content=clean_adapted,
                    generated_image=main_image,
                    target_account=account,
                    generation_strategy={
                        'batch_created': True,
                        'adaptation_style': adaptation_style,
                        'source_content_preview': source_content[:100],
                        'images_generated': len(all_image_ids),
                        'layout': image_layout,
                        'sizes': image_sizes
                    },
                    status='completed',
                    completed_at=timezone.now()
                )

                # Save images to AgentPostImage
                for idx, img_id in enumerate(all_image_ids):
                    try:
                        media = Media.objects.get(id=img_id)
                        AgentPostImage.objects.create(
                            agent_post=agent_post,
                            media=media,
                            order=idx,
                            variation=idx + 1
                        )
                    except Media.DoesNotExist:
                        pass

                created_posts.append({
                    'post_id': agent_post.id,
                    'account_id': acc_id,
                    'page_name': page_name,
                    'content_preview': adapted_content[:100] + '...',
                    'image_count': len(all_image_ids),
                    'image_urls': image_urls[:2]  # First 2 for preview
                })

                logger.info(f"[AGENT TOOL] Created post {agent_post.id} for page {page_name} with {len(all_image_ids)} images")

            except Exception as e:
                logger.error(f"[AGENT TOOL] Error creating post for account {acc_id}: {e}")
                import traceback
                logger.error(f"[AGENT TOOL] Traceback: {traceback.format_exc()}")
                failed.append({'account_id': acc_id, 'error': str(e)})

        total_images = sum(p['image_count'] for p in created_posts)
        return {
            'success': True,
            'success_count': len(created_posts),
            'fail_count': len(failed),
            'total_images_created': total_images,
            'created_posts': created_posts,
            'failed': failed,
            'message': f'Đã tạo {len(created_posts)}/{len(account_ids)} bài đăng với tổng {total_images} ảnh!',
            'image_generation_tokens': {
                'prompt_tokens': total_img_prompt_tokens,
                'output_tokens': total_img_output_tokens,
                'total_tokens': total_img_tokens
            }
        }


class AgentConversationService:
    """
    Service quản lý conversation với Agent
    """

    @staticmethod
    def send_message(user: User, message: str) -> Dict[str, Any]:
        """
        Gửi message đến Agent và nhận response

        Returns:
            {
                'agent_response': str,
                'conversation_id': int,
                'needs_tool_execution': bool,
                'function_calls': List[Dict]
            }
        """
        # Save user message
        user_conv = AgentConversation.objects.create(
            user=user,
            role='user',
            message=message
        )

        # Get conversation history (last 10 messages)
        history = AgentConversation.objects.filter(user=user).order_by('-created_at')[:10]
        history = list(reversed(history))  # Oldest first

        history_list = [
            {'role': msg.role, 'message': msg.message}
            for msg in history[:-1]  # Exclude current message
        ]

        # Get agent and chat
        agent = get_agent()
        response = agent.chat(
            user_message=message,
            user_id=user.id,
            conversation_history=history_list
        )

        # Check if needs tool execution
        if response['needs_tool_execution']:
            # Execute tools
            function_results = []
            for fc in response['function_calls']:
                result = AgentToolExecutor.execute_tool(
                    function_name=fc['name'],
                    arguments=fc['args'],
                    user=user
                )
                # Include tool_call_id for DeepSeek compatibility (Gemini ignores it)
                function_results.append({
                    'function_name': fc['name'],
                    'result': result,
                    'tool_call_id': fc.get('tool_call_id'),
                    'args': fc.get('args', {})
                })

            # Continue conversation with tool results
            tool_result = agent.continue_with_tool_results(
                chat_session=response.get('chat_session'),
                function_results=function_results,
                user=user,  # Pass user for executing additional tools
                reasoning_content=response.get('reasoning_content')  # For deepseek-reasoner
            )

            # Extract response and token_usage from result
            final_response = tool_result.get('response', '')
            token_usage = tool_result.get('token_usage', response.get('token_usage', {}))

            # Save agent response with function calls
            agent_conv = AgentConversation.objects.create(
                user=user,
                role='agent',
                message=final_response,
                function_calls=response['function_calls']
            )

            return {
                'agent_response': final_response,
                'conversation_id': agent_conv.id,
                'function_calls': response['function_calls'],
                'token_usage': token_usage
            }
        else:
            # No tools needed, just save response
            agent_conv = AgentConversation.objects.create(
                user=user,
                role='agent',
                message=response['agent_response']
            )

            return {
                'agent_response': response['agent_response'],
                'conversation_id': agent_conv.id,
                'function_calls': [],
                'token_usage': response.get('token_usage', {})
            }

    @staticmethod
    def send_message_stream(user: User, message: str, files: List[Dict] = None):
        """
        Gửi message đến Agent với streaming progress updates
        Hỗ trợ files đính kèm (images, documents) cho Gemini multimodal

        Args:
            user: User object
            message: Tin nhắn từ user
            files: List các file đính kèm với format:
                   [{'name': 'file.jpg', 'mime_type': 'image/jpeg', 'data': 'base64...'}]

        Yields events:
            {'type': 'progress', 'step': 'analyzing', 'message': '...'}
            {'type': 'function_call', 'name': '...', 'args': {...}}
            {'type': 'function_result', 'name': '...', 'success': True}
            {'type': 'done', 'response': '...', 'conversation_id': X, 'token_usage': {...}}
            {'type': 'error', 'message': '...'}
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Build message with file info for display
            display_message = message
            if files:
                file_names = [f['name'] for f in files]
                display_message += f"\n📎 {', '.join(file_names)}"

            # Save user message
            user_conv = AgentConversation.objects.create(
                user=user,
                role='user',
                message=display_message
            )

            progress_msg = 'Đang tải file lên...' if files else 'Đang phân tích yêu cầu...'
            yield {'type': 'progress', 'step': 'analyzing', 'message': progress_msg}

            # Get conversation history (last 5 messages)
            history = AgentConversation.objects.filter(user=user).order_by('-created_at')[:5]
            history = list(reversed(history))

            history_list = [
                {'role': msg.role, 'message': msg.message}
                for msg in history[:-1]
            ]

            # Get agent and chat
            agent = get_agent()
            response = agent.chat(
                user_message=message,
                user_id=user.id,
                conversation_history=history_list,
                files=files
            )

            # Check if needs tool execution
            if response['needs_tool_execution']:
                # Execute tools with progress updates
                function_results = []
                total_calls = len(response['function_calls'])

                for idx, fc in enumerate(response['function_calls'], 1):
                    # Yield function call event
                    step_name = AgentConversationService._get_step_name(fc['name'])
                    yield {
                        'type': 'function_call',
                        'name': fc['name'],
                        'display_name': step_name,
                        'args': fc.get('args', {}),
                        'current': idx,
                        'total': total_calls,
                        'message': f'{step_name} ({idx}/{total_calls})...'
                    }

                    # Execute the tool
                    result = AgentToolExecutor.execute_tool(
                        function_name=fc['name'],
                        arguments=fc['args'],
                        user=user
                    )
                    # Include tool_call_id for DeepSeek compatibility (Gemini ignores it)
                    function_results.append({
                        'function_name': fc['name'],
                        'result': result,
                        'tool_call_id': fc.get('tool_call_id'),
                        'args': fc.get('args', {})
                    })

                    # Yield result event
                    success = not result.get('error')
                    yield {
                        'type': 'function_result',
                        'name': fc['name'],
                        'success': success,
                        'message': result.get('message', 'Hoàn thành') if success else result.get('error', 'Lỗi')
                    }

                # Continue conversation with tool results (may have more tools)
                yield {'type': 'progress', 'step': 'continuing', 'message': 'Đang xử lý kết quả...'}

                # Use streaming version of continue_with_tool_results
                for event in AgentConversationService._continue_with_tool_results_stream(
                    agent=agent,
                    chat_session=response.get('chat_session'),
                    function_results=function_results,
                    user=user,
                    initial_token_usage=response.get('token_usage', {}),
                    reasoning_content=response.get('reasoning_content')  # For deepseek-reasoner
                ):
                    if event['type'] == 'done':
                        # Save agent response
                        final_response = event.get('response', '')
                        token_usage = event.get('token_usage', {})

                        agent_conv = AgentConversation.objects.create(
                            user=user,
                            role='agent',
                            message=final_response,
                            function_calls=response['function_calls']
                        )

                        yield {
                            'type': 'done',
                            'response': final_response,
                            'conversation_id': agent_conv.id,
                            'function_calls': response['function_calls'],
                            'token_usage': token_usage
                        }
                    else:
                        yield event
            else:
                # No tools needed
                agent_conv = AgentConversation.objects.create(
                    user=user,
                    role='agent',
                    message=response['agent_response']
                )

                yield {
                    'type': 'done',
                    'response': response['agent_response'],
                    'conversation_id': agent_conv.id,
                    'function_calls': [],
                    'token_usage': response.get('token_usage', {})
                }

        except Exception as e:
            logger.error(f"[AGENT STREAM] Error: {str(e)}")
            yield {'type': 'error', 'message': str(e)}

    @staticmethod
    def _get_step_name(function_name: str) -> str:
        """Convert function name to user-friendly display name"""
        step_names = {
            'get_current_datetime': 'Lấy thời gian',
            'get_scheduled_posts': 'Lấy lịch đăng',
            'get_agent_posts': 'Lấy bài đã tạo',
            'get_agent_post_details': 'Lấy chi tiết bài đăng',
            'get_system_stats': 'Lấy thống kê',
            'generate_post_content': 'Tạo nội dung',
            'generate_post_image': 'Tạo hình ảnh',
            'save_agent_post': 'Lưu bài đăng',
            'edit_agent_post': 'Sửa bài đăng',
            'batch_edit_agent_posts': 'Sửa nhiều bài đăng',
            'analyze_schedule': 'Phân tích lịch',
            'get_connected_accounts': 'Lấy danh sách pages',
            'update_page_info': 'Cập nhật thông tin page',
            'update_page_photo': 'Cập nhật ảnh page',
            'batch_update_pages_info': 'Cập nhật nhiều pages',
            'edit_image': 'Chỉnh sửa hình ảnh',
            'batch_create_posts': 'Tạo bài cho nhiều pages',
            'batch_add_text_to_images': 'Thêm text vào nhiều ảnh'
        }
        return step_names.get(function_name, function_name)

    @staticmethod
    def _continue_with_tool_results_stream(agent, chat_session, function_results, user, initial_token_usage, reasoning_content=None):
        """
        Streaming version of continue_with_tool_results
        Yields progress events for additional tool calls
        Supports both Gemini and DeepSeek agents
        """
        import logging

        logger = logging.getLogger(__name__)

        # Check if using DeepSeek (chat_session is a list of messages)
        if isinstance(chat_session, list):
            # DeepSeek agent - handle with streaming support for recursive tool calls
            logger.info("[AGENT STREAM] Using DeepSeek continue_with_tool_results with streaming")
            try:
                import json

                messages = chat_session.copy()
                current_function_results = function_results
                current_reasoning = reasoning_content
                accumulated_input_tokens = initial_token_usage.get('input_tokens', 0)
                accumulated_output_tokens = initial_token_usage.get('output_tokens', 0)
                initial_breakdown = initial_token_usage.get('breakdown', {})

                # Track image generation tokens
                total_img_prompt_tokens = 0
                total_img_output_tokens = 0
                total_img_tokens = 0
                tool_result_tokens_total = 0

                while True:
                    # Build assistant message with tool_calls
                    assistant_message = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": []
                    }
                    if current_reasoning:
                        assistant_message["reasoning_content"] = current_reasoning

                    for result in current_function_results:
                        tool_call_id = result.get('tool_call_id', f"call_{result['function_name']}")
                        assistant_message["tool_calls"].append({
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": result['function_name'],
                                "arguments": json.dumps(result.get('args', {}))
                            }
                        })

                    if assistant_message["tool_calls"]:
                        messages.append(assistant_message)

                    # Add tool results as tool messages
                    for result in current_function_results:
                        result_str = json.dumps(result.get('result', ''), ensure_ascii=False)
                        result_tokens = agent.count_tokens(result_str)
                        tool_result_tokens_total += result_tokens

                        # Extract image generation tokens
                        tool_result = result.get('result', {})
                        if isinstance(tool_result, dict):
                            img_tokens = tool_result.get('image_generation_tokens', {})
                            if img_tokens:
                                total_img_prompt_tokens += img_tokens.get('prompt_tokens', 0)
                                total_img_output_tokens += img_tokens.get('output_tokens', 0)
                                total_img_tokens += img_tokens.get('total_tokens', 0)

                        tool_call_id = result.get('tool_call_id', f"call_{result['function_name']}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result_str
                        })

                    # Call DeepSeek API
                    response = agent.client.chat.completions.create(
                        model=agent.model_name,
                        messages=messages,
                        tools=agent.tools,
                        tool_choice="auto"
                    )

                    choice = response.choices[0]
                    message = choice.message

                    # Get token usage
                    if response.usage:
                        accumulated_input_tokens += response.usage.prompt_tokens
                        accumulated_output_tokens += response.usage.completion_tokens

                    # Check for more tool calls
                    if message.tool_calls:
                        # Yield progress events for each tool call
                        total_calls = len(message.tool_calls)
                        new_function_results = []

                        for idx, tool_call in enumerate(message.tool_calls, 1):
                            fc_name = tool_call.function.name
                            try:
                                fc_args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                fc_args = {}

                            # Yield function_call event
                            step_name = AgentConversationService._get_step_name(fc_name)
                            yield {
                                'type': 'function_call',
                                'name': fc_name,
                                'display_name': step_name,
                                'args': fc_args,
                                'current': idx,
                                'total': total_calls,
                                'message': f'{step_name} ({idx}/{total_calls})...'
                            }

                            # Execute the tool
                            result = AgentToolExecutor.execute_tool(
                                function_name=fc_name,
                                arguments=fc_args,
                                user=user
                            )

                            new_function_results.append({
                                'function_name': fc_name,
                                'args': fc_args,
                                'result': result,
                                'tool_call_id': tool_call.id
                            })

                            # Yield function_result event
                            success = not result.get('error')
                            yield {
                                'type': 'function_result',
                                'name': fc_name,
                                'success': success,
                                'message': result.get('message', 'Hoàn thành') if success else result.get('error', 'Lỗi')
                            }

                        # Prepare for next iteration
                        current_function_results = new_function_results
                        current_reasoning = getattr(message, 'reasoning_content', None)
                        yield {'type': 'progress', 'step': 'continuing', 'message': 'Đang xử lý kết quả...'}
                    else:
                        # No more tool calls - we're done
                        response_text = message.content or "Fugu đã xử lý xong!"

                        # Build final token usage with breakdown
                        breakdown = {
                            'input_breakdown': {
                                **initial_breakdown.get('input_breakdown', {}),
                                'tool_results_tokens': tool_result_tokens_total
                            },
                            'text_tokens': initial_breakdown.get('text_tokens', 0) + agent.count_tokens(response_text),
                            'function_call_tokens': initial_breakdown.get('function_call_tokens', 0),
                            'function_calls_detail': initial_breakdown.get('function_calls_detail', [])
                        }

                        if total_img_tokens > 0:
                            breakdown['image_generation'] = {
                                'prompt_tokens': total_img_prompt_tokens,
                                'output_tokens': total_img_output_tokens,
                                'total_tokens': total_img_tokens
                            }

                        final_token_usage = {
                            'input_tokens': accumulated_input_tokens,
                            'output_tokens': accumulated_output_tokens,
                            'total_tokens': accumulated_input_tokens + accumulated_output_tokens,
                            'breakdown': breakdown
                        }

                        yield {
                            'type': 'done',
                            'response': response_text,
                            'token_usage': final_token_usage
                        }
                        return

            except Exception as e:
                logger.error(f"[AGENT STREAM] DeepSeek continue error: {e}")
                import traceback
                logger.error(f"[AGENT STREAM] Traceback: {traceback.format_exc()}")
                yield {
                    'type': 'error',
                    'message': str(e),
                    'token_usage': initial_token_usage
                }
                return

        # Gemini agent - use Gemini-specific code
        import google.generativeai as genai

        try:
            input_tokens = 0
            output_tokens = 0
            tool_result_tokens = 0  # Track tokens from tool results

            # Track image generation tokens
            image_gen_prompt_tokens = 0
            image_gen_output_tokens = 0
            image_gen_total_tokens = 0

            # Get initial breakdown
            initial_breakdown = initial_token_usage.get('breakdown', {})

            # Create function response parts
            parts = []
            for result in function_results:
                result_str = str(result.get('result', ''))
                result_token_count = agent.count_tokens(result_str)
                input_tokens += result_token_count
                tool_result_tokens += result_token_count

                # Extract image generation tokens if present
                tool_result = result.get('result', {})
                if isinstance(tool_result, dict):
                    img_tokens = tool_result.get('image_generation_tokens', {})
                    if img_tokens:
                        image_gen_prompt_tokens += img_tokens.get('prompt_tokens', 0)
                        image_gen_output_tokens += img_tokens.get('output_tokens', 0)
                        image_gen_total_tokens += img_tokens.get('total_tokens', 0)

                parts.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=result['function_name'],
                            response={'result': result['result']}
                        )
                    )
                )

            # Send function results back to model
            response = chat_session.send_message(
                genai.protos.Content(parts=parts)
            )

            # Helper to build final token_usage with breakdown
            def build_token_usage(accumulated_input_tokens, accumulated_tool_result_tokens, final_output_tokens, img_tokens=None):
                total_input = initial_token_usage.get('input_tokens', 0) + accumulated_input_tokens
                total_output = initial_token_usage.get('output_tokens', 0) + final_output_tokens

                # Lấy input_breakdown từ initial (đã được tính từ chat() method)
                input_breakdown = initial_breakdown.get('input_breakdown', {})
                # Cập nhật tool_result_tokens vào input breakdown nếu có
                if accumulated_tool_result_tokens > 0:
                    input_breakdown = {
                        **input_breakdown,
                        'tool_results_tokens': accumulated_tool_result_tokens
                    }

                breakdown = {
                    'input_breakdown': input_breakdown,
                    'text_tokens': initial_breakdown.get('text_tokens', 0) + final_output_tokens,
                    'function_call_tokens': initial_breakdown.get('function_call_tokens', 0),
                    'function_calls_detail': initial_breakdown.get('function_calls_detail', [])
                }

                # Add image generation tokens if present
                if img_tokens and img_tokens.get('total_tokens', 0) > 0:
                    breakdown['image_generation'] = img_tokens

                return {
                    'input_tokens': total_input,
                    'output_tokens': total_output,
                    'total_tokens': total_input + total_output,
                    'breakdown': breakdown
                }

            # Recursive function to handle more tool calls
            def process_response(resp, accumulated_input_tokens, accumulated_tool_result_tokens, accumulated_img_tokens=None):
                nonlocal output_tokens, image_gen_prompt_tokens, image_gen_output_tokens, image_gen_total_tokens

                # Build current image tokens
                current_img_tokens = accumulated_img_tokens or {
                    'prompt_tokens': image_gen_prompt_tokens,
                    'output_tokens': image_gen_output_tokens,
                    'total_tokens': image_gen_total_tokens
                }

                if not resp.candidates or not resp.candidates[0].content:
                    yield {
                        'type': 'done',
                        'response': 'Fugu đã xử lý xong!',
                        'token_usage': build_token_usage(accumulated_input_tokens, accumulated_tool_result_tokens, output_tokens, current_img_tokens)
                    }
                    return

                # Check for MALFORMED_FUNCTION_CALL or other errors
                if resp.candidates[0].finish_reason:
                    finish_reason = str(resp.candidates[0].finish_reason)
                    if 'MALFORMED' in finish_reason or 'ERROR' in finish_reason:
                        yield {
                            'type': 'done',
                            'response': 'Fugu đã hoàn thành xử lý các bước trước đó.',
                            'token_usage': build_token_usage(accumulated_input_tokens, accumulated_tool_result_tokens, output_tokens, current_img_tokens)
                        }
                        return

                parts_list = resp.candidates[0].content.parts

                # Check for more function calls
                more_function_calls = []
                for part in parts_list:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        args_dict = {}
                        if fc.args:
                            for key in fc.args:
                                value = fc.args[key]
                                if isinstance(value, (str, int, float, bool, type(None))):
                                    args_dict[key] = value
                                elif isinstance(value, (list, tuple)):
                                    args_dict[key] = list(value)
                                elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                                    try:
                                        args_dict[key] = [v for v in value]
                                    except:
                                        args_dict[key] = list(value)
                                else:
                                    try:
                                        args_dict[key] = str(value)
                                    except:
                                        args_dict[key] = None

                        more_function_calls.append({
                            'name': fc.name,
                            'args': args_dict
                        })

                if more_function_calls:
                    # Execute additional tools with progress
                    additional_results = []
                    total_calls = len(more_function_calls)

                    for idx, fc in enumerate(more_function_calls, 1):
                        step_name = AgentConversationService._get_step_name(fc['name'])
                        yield {
                            'type': 'function_call',
                            'name': fc['name'],
                            'display_name': step_name,
                            'args': fc.get('args', {}),
                            'current': idx,
                            'total': total_calls,
                            'message': f'{step_name} ({idx}/{total_calls})...'
                        }

                        result = AgentToolExecutor.execute_tool(
                            function_name=fc['name'],
                            arguments=fc['args'],
                            user=user
                        )
                        additional_results.append({
                            'function_name': fc['name'],
                            'result': result
                        })

                        success = not result.get('error')
                        yield {
                            'type': 'function_result',
                            'name': fc['name'],
                            'success': success,
                            'message': result.get('message', 'Hoàn thành') if success else result.get('error', 'Lỗi')
                        }

                    # Send additional results back to model
                    add_parts = []
                    add_input_tokens = 0
                    add_tool_result_tokens = 0
                    add_img_prompt_tokens = 0
                    add_img_output_tokens = 0
                    add_img_total_tokens = 0

                    for result in additional_results:
                        result_str = str(result.get('result', ''))
                        result_token_count = agent.count_tokens(result_str)
                        add_input_tokens += result_token_count
                        add_tool_result_tokens += result_token_count

                        # Extract image generation tokens from additional results
                        tool_result = result.get('result', {})
                        if isinstance(tool_result, dict):
                            img_tokens = tool_result.get('image_generation_tokens', {})
                            if img_tokens:
                                add_img_prompt_tokens += img_tokens.get('prompt_tokens', 0)
                                add_img_output_tokens += img_tokens.get('output_tokens', 0)
                                add_img_total_tokens += img_tokens.get('total_tokens', 0)

                        add_parts.append(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=result['function_name'],
                                    response={'result': result['result']}
                                )
                            )
                        )

                    # Merge image tokens
                    merged_img_tokens = {
                        'prompt_tokens': current_img_tokens.get('prompt_tokens', 0) + add_img_prompt_tokens,
                        'output_tokens': current_img_tokens.get('output_tokens', 0) + add_img_output_tokens,
                        'total_tokens': current_img_tokens.get('total_tokens', 0) + add_img_total_tokens
                    }

                    yield {'type': 'progress', 'step': 'continuing', 'message': 'Đang xử lý kết quả tiếp theo...'}

                    next_response = chat_session.send_message(
                        genai.protos.Content(parts=add_parts)
                    )

                    # Recursively process with accumulated tokens
                    for event in process_response(
                        next_response,
                        accumulated_input_tokens + add_input_tokens,
                        accumulated_tool_result_tokens + add_tool_result_tokens,
                        merged_img_tokens
                    ):
                        yield event
                else:
                    # No more function calls - extract text response
                    text_parts = []
                    for p in parts_list:
                        if hasattr(p, 'text') and p.text:
                            text_parts.append(p.text)
                            output_tokens += agent.count_tokens(p.text)

                    response_text = '\n'.join(text_parts) if text_parts else "Fugu đã xử lý xong!"

                    yield {
                        'type': 'done',
                        'response': response_text,
                        'token_usage': build_token_usage(accumulated_input_tokens, accumulated_tool_result_tokens, output_tokens, current_img_tokens)
                    }

            # Start processing with initial tokens
            for event in process_response(response, input_tokens, tool_result_tokens):
                yield event

        except Exception as e:
            logger.error(f"[AGENT STREAM] Error in continue: {str(e)}")
            yield {'type': 'error', 'message': str(e)}

    @staticmethod
    def get_conversation_history(user: User, limit: int = 50) -> List[Dict]:
        """Lấy lịch sử conversation"""
        conversations = AgentConversation.objects.filter(user=user).order_by('created_at')[:limit]

        return [
            {
                'id': conv.id,
                'role': conv.role,
                'message': conv.message,
                'function_calls': conv.function_calls,
                'created_at': conv.created_at.isoformat()
            }
            for conv in conversations
        ]


class AgentPostService:
    """
    Service quản lý Agent Posts
    """

    @staticmethod
    def get_user_posts(user: User, limit: int = 20) -> List[Dict]:
        """Lấy danh sách posts do Agent tạo"""
        posts = AgentPost.objects.filter(user=user).select_related('target_account').prefetch_related('images__media').order_by('-created_at')[:limit]

        result = []
        for post in posts:
            # Get all images from AgentPostImage - order by 'order' to ensure hero image is first
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

            result.append({
                'id': post.id,
                'content': post.content,
                'full_content': post.full_content,
                'hashtags': post.hashtags if isinstance(post.hashtags, list) else [],
                'image_url': post.generated_image.file_url if post.generated_image else None,
                'images': images,  # All images
                'status': post.status,
                'agent_reasoning': post.agent_reasoning or '',
                'generation_strategy': post.generation_strategy or {},
                'target_account': target_account_info,  # Page được gắn
                'created_at': post.created_at.isoformat(),
                'completed_at': post.completed_at.isoformat() if post.completed_at else None
            })

        return result

    @staticmethod
    def delete_post(user: User, post_id: int) -> bool:
        """Xóa agent post"""
        try:
            post = AgentPost.objects.get(id=post_id, user=user)
            post.delete()
            return True
        except AgentPost.DoesNotExist:
            return False

    @staticmethod
    def update_post(
        user: User,
        post_id: int,
        content: str = None,
        full_content: str = None,
        hashtags: List[str] = None
    ) -> Dict:
        """Cập nhật agent post (sửa nhanh)"""
        try:
            post = AgentPost.objects.prefetch_related('images__media').get(id=post_id, user=user)

            if content is not None:
                post.content = content
            if full_content is not None:
                post.full_content = full_content
            if hashtags is not None:
                post.hashtags = hashtags

            post.save()

            # Return updated post data - order by 'order' to ensure hero image is first
            images = [
                {
                    'id': img.id,
                    'url': img.media.file_url,
                    'order': img.order
                }
                for img in post.images.all().order_by('order')
            ]

            return {
                'id': post.id,
                'content': post.content,
                'full_content': post.full_content,
                'hashtags': post.hashtags,
                'image_url': post.generated_image.file_url if post.generated_image else None,
                'images': images,
                'status': post.status,
                'created_at': post.created_at.isoformat()
            }
        except AgentPost.DoesNotExist:
            return None
