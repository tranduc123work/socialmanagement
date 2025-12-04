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
from .llm_agent import get_agent


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
        }

        if function_name not in tool_map:
            return {'error': f'Unknown function: {function_name}'}

        try:
            # Add user to arguments
            result = tool_map[function_name](user=user, **arguments)
            return result
        except Exception as e:
            return {'error': str(e)}

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
        relative_day: str = None
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

        # Filter by relative_day (highest priority - simplest for agent)
        if relative_day:
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
        tone: str = 'casual',
        word_count: int = 100
    ) -> Dict:
        """Tool: Generate/polish nội dung bài đăng

        Có 2 mode:
        1. Polish mode: Nếu có draft_content -> chau chuốt nội dung nháp
        2. Create mode: Nếu có topic -> tạo content mới từ đầu
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[AGENT TOOL] generate_post_content called with:")
        logger.info(f"  - draft_content: {draft_content[:100] if draft_content else None}...")
        logger.info(f"  - page_context: {page_context}")
        logger.info(f"  - topic: {topic}")
        logger.info(f"  - goal: {goal}")
        logger.info(f"  - tone: {tone}")

        # Build page context section
        page_section = ""
        if page_context:
            page_section = f"""
BÀI VIẾT CHO PAGE: {page_context}
(Viết nội dung phù hợp với đặc thù của page này, có thể nhắc đến tên page nếu phù hợp với ngữ cảnh)
"""

        # Determine mode and build prompt
        if draft_content:
            # POLISH MODE: Chau chuốt nội dung nháp
            prompt = f"""
NHIỆM VỤ: Chau chuốt nội dung nháp thành bài đăng hoàn chỉnh.
{page_section}
NỘI DUNG NHÁP:
{draft_content}

MỤC TIÊU: {goal}
GIỌNG ĐIỆU: {tone}

YÊU CẦU:
- GIỮ NGUYÊN ý chính, thông điệp của nội dung nháp
- Viết lại cho CHẢY TỰ NHIÊN như người thật đang chia sẻ
- Bắt đầu bằng câu hook gây chú ý mạnh
- Mở rộng nội dung chính có chiều sâu, chi tiết hơn (khoảng {word_count} từ)
- Thêm câu hỏi tương tác với người đọc
- Kết thúc bằng CTA (lời kêu gọi hành động)
- Cuối bài thêm 5-7 hashtags phù hợp
- KHÔNG dùng markdown (*, **, #, -)

QUAN TRỌNG: Chỉ viết nội dung thuần text, KHÔNG ghi label như "Hook:", "Body:", "CTA:"
"""
        elif topic:
            # CREATE MODE: Tạo content mới
            prompt = f"""
NHIỆM VỤ: Tạo bài đăng Facebook hoàn chỉnh.
{page_section}
CHỦ ĐỀ: {topic}
MỤC TIÊU: {goal}
GIỌNG ĐIỆU: {tone}

YÊU CẦU:
- Viết nội dung CHẢY TỰ NHIÊN như người thật đang chia sẻ
- Bắt đầu bằng câu hook gây chú ý mạnh
- Nội dung chính có giá trị, chi tiết (khoảng {word_count} từ)
- Đặt câu hỏi tương tác với người đọc
- Kết thúc bằng CTA (lời kêu gọi hành động)
- Cuối bài thêm 5-7 hashtags phù hợp
- KHÔNG dùng markdown (*, **, #, -)

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

        return {
            'content': full_ai_content,
            'mode': 'polish' if draft_content else 'create',
            'page_context': page_context,
            'success': True,
            'message': 'Đã tạo nội dung bài đăng hoàn chỉnh'
        }

    # Facebook image layout configurations - multiple options per count
    # Based on official Facebook post image size guidelines
    FB_IMAGE_LAYOUTS = {
        1: [
            {
                'layout': 'single_landscape',
                'sizes': ['1200x630'],
                'description': '1 ảnh ngang (1200x630)'
            }
        ],
        2: [
            {
                'layout': 'two_horizontal',
                'sizes': ['2000x1000', '2000x1000'],
                'description': '2 ảnh ngang (2000x1000)'
            },
            {
                'layout': 'two_vertical',
                'sizes': ['1000x2000', '1000x2000'],
                'description': '2 ảnh dọc (1000x2000)'
            }
        ],
        3: [
            {
                'layout': 'one_horizontal_two_square',
                'sizes': ['2000x1000', '1000x1000', '1000x1000'],
                'description': '1 ảnh ngang lớn + 2 ảnh vuông'
            },
            {
                'layout': 'one_vertical_two_square',
                'sizes': ['1000x2000', '1000x1000', '1000x1000'],
                'description': '1 ảnh dọc lớn + 2 ảnh vuông'
            }
        ],
        4: [
            {
                'layout': 'one_horizontal_three_square',
                'sizes': ['1920x960', '1920x1920', '1920x1920', '1920x1920'],
                'description': '1 ảnh ngang + 3 ảnh vuông'
            },
            {
                'layout': 'one_vertical_three_square',
                'sizes': ['960x1920', '1920x1920', '1920x1920', '1920x1920'],
                'description': '1 ảnh dọc + 3 ảnh vuông'
            },
            {
                'layout': 'four_square',
                'sizes': ['1920x1920', '1920x1920', '1920x1920', '1920x1920'],
                'description': '4 ảnh vuông đồng đều'
            }
        ],
        5: [
            {
                'layout': 'two_square_three_rect',
                'sizes': ['1920x1920', '1920x1920', '1920x1280', '1920x1280', '1920x1280'],
                'description': '2 ảnh vuông + 3 ảnh chữ nhật'
            },
            {
                'layout': 'five_square',
                'sizes': ['1920x1920', '1920x1920', '1920x1920', '1920x1920', '1920x1920'],
                'description': '5 ảnh vuông đồng đều'
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
        count: int = 3
    ) -> Dict:
        """Tool: Generate hình ảnh phù hợp với content bài đăng

        Args:
            post_content: Nội dung bài đăng đã generate (từ generate_post_content)
            page_context: Tên page + ngành nghề để customize
            style: Phong cách ảnh
            size: Kích thước (nếu không set, sẽ tự động theo count)
            count: Số lượng ảnh cần tạo (1-5)
        """
        import logging
        import random
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

        try:
            # Build image prompt từ content
            content_summary = post_content[:500] if len(post_content) > 500 else post_content

            image_prompt = f"""
Tạo hình ảnh quảng cáo chuyên nghiệp cho bài đăng Facebook.

NỘI DUNG BÀI ĐĂNG:
{content_summary}

{"NGÀNH NGHỀ: " + page_context if page_context else ""}

YÊU CẦU HÌNH ẢNH:
- Phong cách: {style}
- Hình ảnh phải liên quan đến nội dung bài đăng
- Chất lượng cao, chuyên nghiệp
- Phù hợp với social media marketing
- Không có text trên ảnh
"""

            logger.info(f"[AGENT TOOL] Image prompt:\n{image_prompt[:300]}...")

            # Generate images with appropriate sizes
            media_list = []
            for idx in range(count):
                # Get size for this image position
                img_size = image_sizes[idx] if idx < len(image_sizes) else '1080x1080'

                # Use provided size if specified, otherwise use layout-based size
                final_size = size if size else img_size

                logger.info(f"[AGENT TOOL] Generating image {idx + 1}/{count} with size {final_size}")

                results = AIImageService.generate_image(
                    prompt=image_prompt,
                    user=user,
                    size=final_size,
                    creativity='medium',
                    count=1  # Generate one at a time for different sizes
                )

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

            logger.info(f"[AGENT TOOL] Generated {len(media_list)} images")

            return {
                'media_ids': [m['media_id'] for m in media_list],
                'images': media_list,
                'count': len(media_list),
                'layout': layout_type,
                'layout_description': layout_config['description'],
                'success': True,
                'message': f'Đã tạo {len(media_list)} hình ảnh với bố cục {layout_config["description"]}'
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

            # Create AgentPost
            agent_post = AgentPost.objects.create(
                user=user,
                content=content,
                hashtags=[],  # Hashtags đã được embed trong content
                full_content=full_content,
                generated_image=main_image,
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
            page_info = f" cho page '{page_context}'" if page_context else ""
            image_info = " với hình ảnh" if main_image else ""

            return {
                'post_id': agent_post.id,
                'content': agent_post.content[:200] + '...' if len(agent_post.content) > 200 else agent_post.content,
                'image_url': main_image.file_url if main_image else None,
                'images': saved_images,
                'page_context': page_context,
                'success': True,
                'message': f'Bài đăng #{agent_post.id} đã được lưu thành công{page_info}{image_info}!'
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

        # Get conversation history (last 20 messages)
        history = AgentConversation.objects.filter(user=user).order_by('-created_at')[:20]
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
                function_results.append({
                    'function_name': fc['name'],
                    'result': result
                })

            # Continue conversation with tool results
            tool_result = agent.continue_with_tool_results(
                chat_session=response.get('chat_session'),
                function_results=function_results,
                user=user  # Pass user for executing additional tools
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
    def send_message_stream(user: User, message: str):
        """
        Gửi message đến Agent với streaming progress updates

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
            # Save user message
            user_conv = AgentConversation.objects.create(
                user=user,
                role='user',
                message=message
            )

            yield {'type': 'progress', 'step': 'analyzing', 'message': 'Đang phân tích yêu cầu...'}

            # Get conversation history (last 20 messages)
            history = AgentConversation.objects.filter(user=user).order_by('-created_at')[:20]
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
                conversation_history=history_list
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
                    function_results.append({
                        'function_name': fc['name'],
                        'result': result
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
                    initial_token_usage=response.get('token_usage', {})
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
            'batch_update_pages_info': 'Cập nhật nhiều pages'
        }
        return step_names.get(function_name, function_name)

    @staticmethod
    def _continue_with_tool_results_stream(agent, chat_session, function_results, user, initial_token_usage):
        """
        Streaming version of continue_with_tool_results
        Yields progress events for additional tool calls
        """
        import logging
        import google.generativeai as genai

        logger = logging.getLogger(__name__)

        try:
            input_tokens = 0
            output_tokens = 0

            # Create function response parts
            parts = []
            for result in function_results:
                result_str = str(result.get('result', ''))
                input_tokens += agent.count_tokens(result_str)

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

            # Recursive function to handle more tool calls
            def process_response(resp, accumulated_input_tokens):
                nonlocal output_tokens

                if not resp.candidates or not resp.candidates[0].content:
                    yield {
                        'type': 'done',
                        'response': 'Đã xử lý xong!',
                        'token_usage': {
                            'input_tokens': initial_token_usage.get('input_tokens', 0) + accumulated_input_tokens,
                            'output_tokens': initial_token_usage.get('output_tokens', 0) + output_tokens,
                            'total_tokens': initial_token_usage.get('input_tokens', 0) + accumulated_input_tokens + initial_token_usage.get('output_tokens', 0) + output_tokens
                        }
                    }
                    return

                # Check for MALFORMED_FUNCTION_CALL or other errors
                if resp.candidates[0].finish_reason:
                    finish_reason = str(resp.candidates[0].finish_reason)
                    if 'MALFORMED' in finish_reason or 'ERROR' in finish_reason:
                        yield {
                            'type': 'done',
                            'response': 'Đã hoàn thành xử lý các bước trước đó.',
                            'token_usage': {
                                'input_tokens': initial_token_usage.get('input_tokens', 0) + accumulated_input_tokens,
                                'output_tokens': initial_token_usage.get('output_tokens', 0) + output_tokens,
                                'total_tokens': initial_token_usage.get('input_tokens', 0) + accumulated_input_tokens + initial_token_usage.get('output_tokens', 0) + output_tokens
                            }
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
                    for result in additional_results:
                        result_str = str(result.get('result', ''))
                        add_input_tokens += agent.count_tokens(result_str)

                        add_parts.append(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=result['function_name'],
                                    response={'result': result['result']}
                                )
                            )
                        )

                    yield {'type': 'progress', 'step': 'continuing', 'message': 'Đang xử lý kết quả tiếp theo...'}

                    next_response = chat_session.send_message(
                        genai.protos.Content(parts=add_parts)
                    )

                    # Recursively process
                    for event in process_response(next_response, accumulated_input_tokens + add_input_tokens):
                        yield event
                else:
                    # No more function calls - extract text response
                    text_parts = []
                    for p in parts_list:
                        if hasattr(p, 'text') and p.text:
                            text_parts.append(p.text)
                            output_tokens += agent.count_tokens(p.text)

                    response_text = '\n'.join(text_parts) if text_parts else "Đã xử lý xong!"

                    yield {
                        'type': 'done',
                        'response': response_text,
                        'token_usage': {
                            'input_tokens': initial_token_usage.get('input_tokens', 0) + accumulated_input_tokens,
                            'output_tokens': initial_token_usage.get('output_tokens', 0) + output_tokens,
                            'total_tokens': initial_token_usage.get('input_tokens', 0) + accumulated_input_tokens + initial_token_usage.get('output_tokens', 0) + output_tokens
                        }
                    }

            # Start processing
            for event in process_response(response, input_tokens):
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
        posts = AgentPost.objects.filter(user=user).prefetch_related('images__media').order_by('-created_at')[:limit]

        result = []
        for post in posts:
            # Get all images from AgentPostImage
            images = [
                {
                    'id': img.id,
                    'url': img.media.file_url,
                    'order': img.order
                }
                for img in post.images.all()
            ]

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

            # Return updated post data
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
                'images': images,
                'status': post.status,
                'created_at': post.created_at.isoformat()
            }
        except AgentPost.DoesNotExist:
            return None
