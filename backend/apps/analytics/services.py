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
