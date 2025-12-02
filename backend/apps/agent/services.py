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
            'create_agent_post': AgentToolExecutor.create_agent_post,
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
        business_type: str,
        topic: str,
        goal: str,
        tone: str = 'casual'
    ) -> Dict:
        """Tool: Generate nội dung bài đăng"""
        import logging
        logger = logging.getLogger(__name__)

        # Log input parameters
        logger.info(f"[AGENT TOOL] generate_post_content called with:")
        logger.info(f"  - business_type: {business_type}")
        logger.info(f"  - topic: {topic}")
        logger.info(f"  - goal: {goal}")
        logger.info(f"  - tone: {tone}")

        prompt = f"""
Tạo bài đăng Facebook cho {business_type} về: {topic}

Mục tiêu: {goal}
Giọng điệu: {tone}

YÊU CẦU:
- Viết nội dung CHẢY TỰ NHIÊN như người thật đang chia sẻ
- Bắt đầu bằng câu gây chú ý mạnh
- Nội dung chính có giá trị, chi tiết
- Đặt câu hỏi tương tác với người đọc
- Kết thúc bằng lời kêu gọi hành động
- Cuối bài đặt 5-7 hashtags phù hợp

QUAN TRỌNG: KHÔNG ghi các label như "Hook:", "Body:", "CTA:", "Hashtags:" - chỉ viết nội dung thôi!
"""

        logger.info(f"[AGENT TOOL] Generated prompt:\n{prompt}")

        result = AIContentService.generate_content(
            prompt=prompt,
            tone=tone,
            include_hashtags=True,
            language='vi'
        )

        # Get full content from AI (includes hashtags in text)
        full_ai_content = result.get('content', '')

        logger.info(f"[AGENT TOOL] AI returned full content length: {len(full_ai_content)} chars")
        logger.info(f"[AGENT TOOL] Content preview:\n{full_ai_content[:500]}...")

        return {
            'content': full_ai_content,  # Full content with hashtags embedded
            'success': True,
            'message': 'Đã tạo nội dung bài đăng đầy đủ'
        }

    @staticmethod
    def generate_post_image(
        user: User,
        description: str,
        style: str = 'professional',
        size: str = '1080x1080',
        count: int = 3
    ) -> Dict:
        """Tool: Generate nhiều hình ảnh (mặc định 3 ảnh)"""
        try:
            # Generate multiple images
            results = AIImageService.generate_image(
                prompt=description,
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

            return {
                'media_ids': [m['media_id'] for m in media_list],
                'images': media_list,
                'count': len(media_list),
                'success': True
            }
        except Exception as e:
            return {
                'error': str(e),
                'success': False
            }

    @staticmethod
    def create_agent_post(
        user: User,
        content: str,
        hashtags: List[str] = None,
        image_description: str = None,
        page_context: str = None,
        strategy: Dict = None,
        image_count: int = 3
    ) -> Dict:
        """Tool: Tạo bài đăng hoàn chỉnh với nhiều hình ảnh"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[AGENT TOOL] create_agent_post called with:")
        logger.info(f"  - content length: {len(content)} chars")
        logger.info(f"  - content preview: {content[:200]}...")
        logger.info(f"  - hashtags: {hashtags}")
        logger.info(f"  - image_description: {image_description}")
        logger.info(f"  - page_context: {page_context}")
        logger.info(f"  - image_count: {image_count}")
        logger.info(f"  - strategy: {strategy}")

        try:
            # Use content as-is (already includes hashtags from generate_post_content)
            # If additional hashtags provided separately, append them
            full_content = content

            # Add page context to content if provided (customize for specific page)
            if page_context:
                # Add page name at the end of content (before hashtags)
                # Format: "\n\n📍 {page_name}"
                logger.info(f"[AGENT TOOL] Adding page_context: {page_context}")
                full_content += f"\n\n📍 {page_context}"

            if hashtags and len(hashtags) > 0:
                full_content += '\n\n' + ' '.join(hashtags)

            logger.info(f"[AGENT TOOL] Full content to save: {len(full_content)} chars")
            logger.info(f"[AGENT TOOL] Full content preview:\n{full_content[:500]}...")

            # Generate multiple images if description provided
            first_image_media = None
            generated_images = []

            if image_description:
                image_result = AgentToolExecutor.generate_post_image(
                    user=user,
                    description=image_description,
                    style='professional',
                    size='1080x1080',
                    count=image_count
                )
                if image_result.get('success'):
                    generated_images = image_result.get('images', [])
                    if generated_images:
                        # Set first image as main image (backward compatible)
                        first_image_media = Media.objects.get(id=generated_images[0]['media_id'])

            # Build generation strategy with page context
            final_strategy = strategy or {}
            if page_context:
                final_strategy['page_context'] = page_context

            # Create AgentPost
            agent_post = AgentPost.objects.create(
                user=user,
                content=content,
                hashtags=hashtags or [],
                full_content=full_content,
                generated_image=first_image_media,  # Backward compatible
                generation_strategy=final_strategy,
                status='completed',
                completed_at=timezone.now()
            )

            # Save all images to AgentPostImage (new multi-image support)
            saved_images = []
            for idx, img_data in enumerate(generated_images):
                media = Media.objects.get(id=img_data['media_id'])
                post_image = AgentPostImage.objects.create(
                    agent_post=agent_post,
                    media=media,
                    order=idx,
                    variation=img_data.get('variation', idx + 1)
                )
                saved_images.append({
                    'id': post_image.id,
                    'media_id': media.id,
                    'url': media.file_url,
                    'order': idx
                })

            logger.info(f"[AGENT TOOL] Created post {agent_post.id} with {len(saved_images)} images")

            # Build success message
            page_info = f" cho page '{page_context}'" if page_context else ""
            image_info = f" với {len(saved_images)} hình ảnh" if saved_images else " (không có ảnh)"

            return {
                'post_id': agent_post.id,
                'content': agent_post.content,
                'image_url': agent_post.generated_image.file_url if agent_post.generated_image else None,
                'images': saved_images,
                'image_count': len(saved_images),
                'page_context': page_context,
                'success': True,
                'message': f'Bài đăng #{agent_post.id} đã được tạo thành công{page_info}{image_info}!'
            }

        except Exception as e:
            logger.error(f"[AGENT TOOL] Error creating post: {str(e)}")
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
        queryset = SocialAccount.objects.filter(user=user)

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
                function_results.append({
                    'function_name': fc['name'],
                    'result': result
                })

            # Continue conversation with tool results
            final_response = agent.continue_with_tool_results(
                chat_session=response.get('chat_session'),
                function_results=function_results,
                user=user  # Pass user for executing additional tools
            )

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
                'function_calls': response['function_calls']
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
                'function_calls': []
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
