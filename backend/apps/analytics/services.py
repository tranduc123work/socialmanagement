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
                'pending': agent_posts.filter(status='pending').count(),
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
