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
            'get_system_stats': AgentToolExecutor.get_system_stats,
            'generate_post_content': AgentToolExecutor.generate_post_content,
            'generate_post_image': AgentToolExecutor.generate_post_image,
            'save_agent_post': AgentToolExecutor.save_agent_post,
            'analyze_schedule': AgentToolExecutor.analyze_schedule,
            'get_connected_accounts': AgentToolExecutor.get_connected_accounts,
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
        days_ahead: int = None
    ) -> Dict:
        """Tool: Lấy danh sách scheduled posts với date filtering, bao gồm business_type và marketing_goals"""
        from datetime import datetime, timedelta

        # Use select_related to optimize query and get PostingSchedule data
        queryset = ScheduledContent.objects.filter(user=user).select_related('schedule')

        # Filter by status
        if status != 'all':
            queryset = queryset.filter(status=status)

        # Filter by date range
        if days_ahead is not None:
            # Calculate date range from today
            today = timezone.now().date()
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
        tone: str = 'casual'
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

        # Determine mode and build prompt
        if draft_content:
            # POLISH MODE: Chau chuốt nội dung nháp
            prompt = f"""
NHIỆM VỤ: Chau chuốt nội dung nháp thành bài đăng hoàn chỉnh.

NỘI DUNG NHÁP:
{draft_content}

{f'PAGE: {page_context} (Hãy nhắc đến tên page này trong bài viết một cách tự nhiên)' if page_context else ''}
MỤC TIÊU: {goal}
GIỌNG ĐIỆU: {tone}

YÊU CẦU:
- GIỮ NGUYÊN ý chính, thông điệp của nội dung nháp
- Viết lại cho CHẢY TỰ NHIÊN như người thật đang chia sẻ
- Bắt đầu bằng câu hook gây chú ý mạnh
- Mở rộng nội dung chính có chiều sâu, chi tiết hơn (tối thiểu 150 từ)
- Thêm câu hỏi tương tác với người đọc
- Kết thúc bằng CTA (lời kêu gọi hành động)
- Cuối bài thêm 5-7 hashtags phù hợp

QUAN TRỌNG: Chỉ viết nội dung, KHÔNG ghi label như "Hook:", "Body:", "CTA:"
"""
        elif topic:
            # CREATE MODE: Tạo content mới
            prompt = f"""
NHIỆM VỤ: Tạo bài đăng Facebook hoàn chỉnh.

CHỦ ĐỀ: {topic}
{f'PAGE: {page_context} (Hãy nhắc đến tên page này trong bài viết một cách tự nhiên)' if page_context else ''}
MỤC TIÊU: {goal}
GIỌNG ĐIỆU: {tone}

YÊU CẦU:
- Viết nội dung CHẢY TỰ NHIÊN như người thật đang chia sẻ
- Bắt đầu bằng câu hook gây chú ý mạnh
- Nội dung chính có giá trị, chi tiết (tối thiểu 150 từ)
- Đặt câu hỏi tương tác với người đọc
- Kết thúc bằng CTA (lời kêu gọi hành động)
- Cuối bài thêm 5-7 hashtags phù hợp

QUAN TRỌNG: Chỉ viết nội dung, KHÔNG ghi label như "Hook:", "Body:", "CTA:"
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

    @staticmethod
    def generate_post_image(
        user: User,
        post_content: str,
        page_context: str = None,
        style: str = 'professional',
        size: str = '1080x1080',
        count: int = 3
    ) -> Dict:
        """Tool: Generate hình ảnh phù hợp với content bài đăng

        Args:
            post_content: Nội dung bài đăng đã generate (từ generate_post_content)
            page_context: Tên page + ngành nghề để customize
            style: Phong cách ảnh
            size: Kích thước
            count: Số lượng ảnh cần tạo
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[AGENT TOOL] generate_post_image called with:")
        logger.info(f"  - post_content length: {len(post_content)} chars")
        logger.info(f"  - page_context: {page_context}")
        logger.info(f"  - style: {style}")

        try:
            # Build image prompt từ content
            # Tóm tắt content để tạo prompt cho image
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

            # Generate multiple images
            results = AIImageService.generate_image(
                prompt=image_prompt,
                user=user,
                size=size,
                creativity='medium',
                count=count
            )

            # Create media records for each image
            media_list = []
            for idx, result in enumerate(results):
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
                    'variation': result.get('variation', idx + 1)
                })

            logger.info(f"[AGENT TOOL] Generated {len(media_list)} images")

            return {
                'media_ids': [m['media_id'] for m in media_list],
                'images': media_list,
                'count': len(media_list),
                'success': True,
                'message': f'Đã tạo {len(media_list)} hình ảnh phù hợp với nội dung'
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
        page_context: str = None
    ) -> Dict:
        """Tool: Lưu bài đăng hoàn chỉnh vào database

        CHỈ LƯU, không generate. Content và image phải được tạo trước bằng:
        - generate_post_content -> content
        - generate_post_image -> image_id (từ media_ids)

        Args:
            content: Nội dung đã generate từ generate_post_content
            image_id: ID của image đã tạo từ generate_post_image (optional)
            page_context: Tên page để reference
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[AGENT TOOL] save_agent_post called with:")
        logger.info(f"  - content length: {len(content)} chars")
        logger.info(f"  - content preview: {content[:200]}...")
        logger.info(f"  - image_id: {image_id}")
        logger.info(f"  - page_context: {page_context}")

        try:
            full_content = content

            # Add page context if provided
            if page_context:
                logger.info(f"[AGENT TOOL] Adding page_context: {page_context}")
                full_content += f"\n\n📍 {page_context}"

            # Get image if provided
            main_image = None
            if image_id:
                try:
                    # Convert to int in case LLM returns float (e.g., 191.0)
                    image_id = int(image_id)
                    main_image = Media.objects.get(id=image_id)
                    logger.info(f"[AGENT TOOL] Found image: {main_image.file_url}")
                except Media.DoesNotExist:
                    logger.warning(f"[AGENT TOOL] Image {image_id} not found")
                except (ValueError, TypeError) as e:
                    logger.warning(f"[AGENT TOOL] Invalid image_id: {image_id}, error: {e}")

            # Build strategy
            strategy = {}
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

            # If image provided, also save to AgentPostImage for multi-image support
            saved_images = []
            if main_image:
                post_image = AgentPostImage.objects.create(
                    agent_post=agent_post,
                    media=main_image,
                    order=0,
                    variation=1
                )
                saved_images.append({
                    'id': post_image.id,
                    'media_id': main_image.id,
                    'url': main_image.file_url,
                    'order': 0
                })

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
        logger.info(f"[AGENT TOOL] get_connected_accounts called!")
        logger.info(f"[AGENT TOOL] platform={platform}, active_only={active_only}")

        # Lấy tất cả pages trong hệ thống (tạm thời không phân quyền)
        queryset = SocialAccount.objects.all()
        logger.info(f"[AGENT TOOL] Total pages in DB: {queryset.count()}")

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

        return {
            'total': len(accounts),
            'accounts': accounts,
            'platform_summary': platform_summary,
            'message': f'Đang có {len(accounts)} tài khoản/pages được kết nối',
            'tip': 'Sử dụng category của page làm business_type khi tạo bài đăng để nội dung phù hợp hơn'
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
