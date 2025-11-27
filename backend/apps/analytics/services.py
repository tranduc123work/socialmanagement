from apps.facebook_api.services import FacebookAPIService


class AnalyticsService:
    @staticmethod
    def get_dashboard_stats(user):
        from apps.posts.models import Post

        posts = Post.objects.filter(created_by=user)

        return {
            'total_posts': posts.count(),
            'published': posts.filter(status='published').count(),
            'scheduled': posts.filter(status='scheduled').count(),
            'draft': posts.filter(status='draft').count(),
            'failed': posts.filter(status='failed').count(),
        }

    @staticmethod
    def get_post_insights(user, post_id):
        fb_api = FacebookAPIService(user.facebook_access_token, user)
        return fb_api.get_post_insights(post_id)
