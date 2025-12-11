from django.db.models import Avg, Min, Max, F, ExpressionWrapper, DurationField
from apps.facebook_api.services import FacebookAPIService


class AnalyticsService:
    @staticmethod
    def get_dashboard_stats(user):
        from apps.platforms.models import SocialPost, SocialAccount
        from apps.agent.models import AgentPost
        from apps.ai.models import ScheduledContent

        # Bài đăng lên platforms (SocialPost)
        social_posts = SocialPost.objects.filter(created_by=user)

        # Bài đăng do Agent tạo
        agent_posts = AgentPost.objects.filter(user=user)

        # Tài khoản kết nối
        connected_accounts = SocialAccount.objects.filter(user=user, is_active=True)

        # Lịch đăng
        scheduled_content = ScheduledContent.objects.filter(user=user)

        # Tính thống kê thời gian tạo bài của Agent
        completed_posts = agent_posts.filter(
            status='completed',
            completed_at__isnull=False
        ).annotate(
            generation_time=ExpressionWrapper(
                F('completed_at') - F('created_at'),
                output_field=DurationField()
            )
        )

        # Tính avg, min, max generation time (in seconds)
        time_stats = completed_posts.aggregate(
            avg_time=Avg('generation_time'),
            min_time=Min('generation_time'),
            max_time=Max('generation_time')
        )

        # Convert timedelta to seconds
        def timedelta_to_seconds(td):
            if td is None:
                return None
            return round(td.total_seconds(), 1)

        avg_seconds = timedelta_to_seconds(time_stats['avg_time'])
        min_seconds = timedelta_to_seconds(time_stats['min_time'])
        max_seconds = timedelta_to_seconds(time_stats['max_time'])

        # Lấy 5 bài gần nhất với thời gian tạo
        recent_posts = completed_posts.order_by('-created_at')[:5]
        recent_generation_times = [
            {
                'id': post.id,
                'content_preview': post.content[:50] + '...' if len(post.content) > 50 else post.content,
                'generation_time_seconds': round(post.generation_time.total_seconds(), 1),
                'created_at': post.created_at.isoformat()
            }
            for post in recent_posts
        ]

        return {
            # Bài đăng trên platforms
            'social_posts': {
                'total': social_posts.count(),
                'published': social_posts.filter(status='published').count(),
                'scheduled': social_posts.filter(status='scheduled').count(),
                'draft': social_posts.filter(status='draft').count(),
                'failed': social_posts.filter(status='failed').count(),
            },
            # Bài đăng do Agent tạo
            'agent_posts': {
                'total': agent_posts.count(),
                'completed': agent_posts.filter(status='completed').count(),
                'generating': agent_posts.filter(status='generating').count(),
                'failed': agent_posts.filter(status='failed').count(),
                # Thống kê thời gian tạo
                'generation_time': {
                    'avg_seconds': avg_seconds,
                    'min_seconds': min_seconds,
                    'max_seconds': max_seconds,
                    'recent_posts': recent_generation_times,
                }
            },
            # Tài khoản kết nối
            'connected_accounts': {
                'total': connected_accounts.count(),
                'facebook': connected_accounts.filter(platform='facebook').count(),
            },
            # Lịch đăng
            'scheduled_content': {
                'total': scheduled_content.count(),
                'draft': scheduled_content.filter(status='draft').count(),
                'approved': scheduled_content.filter(status='approved').count(),
            },
        }

    @staticmethod
    def get_post_insights(user, post_id):
        fb_api = FacebookAPIService(user.facebook_access_token, user)
        return fb_api.get_post_insights(post_id)

    @staticmethod
    def get_facebook_stats(user):
        """Get aggregated Facebook stats for all connected pages"""
        from apps.platforms.models import SocialAccount

        # Check if user has connected Facebook pages
        pages = SocialAccount.objects.filter(
            user=user,
            platform='facebook',
            is_active=True
        )

        if not pages.exists():
            return {
                'pages': [],
                'summary': {
                    'total_pages': 0,
                    'total_followers': 0,
                    'total_impressions_7d': 0,
                    'total_engagements_7d': 0,
                    'total_posts': 0,
                },
                'message': 'Chưa kết nối trang Facebook nào'
            }

        # Use the first page's token to initialize the service
        # (actual page tokens are used in get_all_pages_stats)
        fb_api = FacebookAPIService(pages.first().access_token, user)
        return fb_api.get_all_pages_stats(user)

    @staticmethod
    def get_facebook_page_stats(user, page_id: str):
        """Get detailed stats for a specific Facebook page"""
        from apps.platforms.models import SocialAccount

        try:
            page = SocialAccount.objects.get(
                user=user,
                platform='facebook',
                platform_account_id=page_id,
                is_active=True
            )
        except SocialAccount.DoesNotExist:
            return {
                'error': 'Không tìm thấy trang này hoặc trang đã bị ngắt kết nối'
            }

        fb_api = FacebookAPIService(page.access_token, user)

        # Get page insights with 28 days data
        page_insights = fb_api.get_page_insights(
            page_id,
            page.access_token,
            period='day',
            date_preset='last_28d'
        )

        # Get posts with insights
        posts_data = fb_api.get_page_posts_with_insights(
            page_id,
            page.access_token,
            limit=25
        )

        # Process insights to create daily chart data
        daily_data = {}
        for insight in page_insights.get('insights', []):
            name = insight.get('name')
            values = insight.get('values', [])
            for v in values:
                end_time = v.get('end_time', '')[:10]  # Get date part
                if end_time not in daily_data:
                    daily_data[end_time] = {}
                daily_data[end_time][name] = v.get('value', 0)

        # Convert to list sorted by date
        chart_data = [
            {
                'date': date,
                **metrics
            }
            for date, metrics in sorted(daily_data.items())
        ]

        posts = posts_data.get('posts', [])

        return {
            'page_info': {
                'id': page.platform_account_id,
                'name': page.name,
                'profile_picture': page.profile_picture_url,
                'category': page.category,
                'followers': page_insights.get('page_info', {}).get('followers_count', 0) or
                            page_insights.get('page_info', {}).get('fan_count', 0) or 0,
            },
            'chart_data': chart_data,
            'posts': posts,
            'summary': {
                'total_posts': len(posts),
                'total_reactions': sum(p.get('reactions_count', 0) for p in posts),
                'total_comments': sum(p.get('comments_count', 0) for p in posts),
                'total_shares': sum(p.get('shares_count', 0) for p in posts),
                'avg_engagement': round(
                    (sum(p.get('reactions_count', 0) + p.get('comments_count', 0) + p.get('shares_count', 0) for p in posts)) / max(len(posts), 1),
                    2
                )
            }
        }
