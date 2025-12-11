"""
Facebook API Service for interacting with Facebook Graph API
"""
import requests
from django.conf import settings
from django.core.exceptions import ValidationError


class FacebookAPIService:
    """Service for Facebook Graph API operations"""

    def __init__(self, access_token: str, user=None):
        self.access_token = access_token
        self.user = user
        self.base_url = settings.FACEBOOK_GRAPH_API_URL

    def _make_request(self, endpoint: str, method: str = 'GET', params: dict = None, data: dict = None):
        """Make a request to Facebook Graph API"""
        url = f"{self.base_url}/{endpoint}"

        if params is None:
            params = {}
        params['access_token'] = self.access_token

        try:
            if method == 'GET':
                response = requests.get(url, params=params)
            elif method == 'POST':
                response = requests.post(url, params=params, data=data)
            elif method == 'DELETE':
                response = requests.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ValidationError(f"Facebook API error: {str(e)}")

    def get_me(self):
        """Get current user information"""
        return self._make_request('me', params={'fields': 'id,name,email,picture'})

    def get_pages(self):
        """Get pages managed by the user"""
        result = self._make_request('me/accounts', params={
            'fields': 'id,name,access_token,picture,category,fan_count'
        })
        return result.get('data', [])

    def get_page_info(self, page_id: str):
        """Get detailed information about a page"""
        return self._make_request(page_id, params={
            'fields': 'id,name,about,picture,cover,fan_count,followers_count,category'
        })

    def create_post(self, page_id: str, page_access_token: str, message: str, link: str = None):
        """Create a text post on a page"""
        data = {'message': message}
        if link:
            data['link'] = link

        # Use page access token for posting
        original_token = self.access_token
        self.access_token = page_access_token

        try:
            result = self._make_request(f'{page_id}/feed', method='POST', data=data)
            return result
        finally:
            self.access_token = original_token

    def create_photo_post(self, page_id: str, page_access_token: str, photo_url: str, caption: str = None):
        """Create a photo post on a page"""
        data = {'url': photo_url}
        if caption:
            data['caption'] = caption

        original_token = self.access_token
        self.access_token = page_access_token

        try:
            result = self._make_request(f'{page_id}/photos', method='POST', data=data)
            return result
        finally:
            self.access_token = original_token

    def get_page_posts(self, page_id: str, limit: int = 25):
        """Get posts from a page"""
        return self._make_request(f'{page_id}/posts', params={
            'fields': 'id,message,created_time,full_picture,permalink_url,shares,reactions.summary(true),comments.summary(true)',
            'limit': limit
        })

    def get_post_insights(self, post_id: str):
        """Get insights for a specific post"""
        return self._make_request(f'{post_id}/insights', params={
            'metric': 'post_impressions,post_engaged_users,post_reactions_by_type_total'
        })

    def delete_post(self, post_id: str, page_access_token: str):
        """Delete a post"""
        original_token = self.access_token
        self.access_token = page_access_token

        try:
            result = self._make_request(post_id, method='DELETE')
            return result
        finally:
            self.access_token = original_token

    def get_page_insights(self, page_id: str, page_access_token: str, period: str = 'day', date_preset: str = 'last_28d'):
        """
        Get page-level insights
        Available metrics (as of 2024):
        - page_impressions: Total impressions
        - page_impressions_unique: Reach (unique users)
        - page_engaged_users: Users who engaged
        - page_post_engagements: Total engagements on posts
        - page_fans: Total page likes/followers
        - page_fan_adds: New followers
        - page_views_total: Total page views

        Note: Many demographic metrics require 100+ followers
        """
        original_token = self.access_token
        self.access_token = page_access_token

        try:
            # Get page fans (followers) - this is a lifetime metric
            fans_result = self._make_request(f'{page_id}', params={
                'fields': 'followers_count,fan_count'
            })

            # Get time-based metrics
            metrics = [
                'page_impressions',
                'page_impressions_unique',
                'page_engaged_users',
                'page_post_engagements',
                'page_fan_adds',
                'page_views_total',
            ]

            insights_result = self._make_request(f'{page_id}/insights', params={
                'metric': ','.join(metrics),
                'period': period,
                'date_preset': date_preset,
            })

            return {
                'page_info': fans_result,
                'insights': insights_result.get('data', [])
            }
        except Exception as e:
            # Return partial data if insights fail
            return {
                'page_info': fans_result if 'fans_result' in dir() else {},
                'insights': [],
                'error': str(e)
            }
        finally:
            self.access_token = original_token

    def get_page_posts_with_insights(self, page_id: str, page_access_token: str, limit: int = 10):
        """
        Get posts with their engagement metrics
        Returns: posts with reactions, comments, shares
        Note: Post-level insights require page to have sufficient activity/followers
        """
        original_token = self.access_token
        self.access_token = page_access_token

        try:
            # Fetch posts with basic engagement metrics only (no insights)
            # insights.metric() causes 400 error for new/small pages
            result = self._make_request(f'{page_id}/posts', params={
                'fields': 'id,message,created_time,full_picture,permalink_url,'
                         'shares,reactions.summary(total_count),'
                         'comments.summary(total_count)',
                'limit': limit
            })

            posts = result.get('data', [])
            processed_posts = []

            for post in posts:
                processed_post = {
                    'id': post.get('id'),
                    'message': post.get('message', ''),
                    'created_time': post.get('created_time'),
                    'full_picture': post.get('full_picture'),
                    'permalink_url': post.get('permalink_url'),
                    'shares_count': post.get('shares', {}).get('count', 0),
                    'reactions_count': post.get('reactions', {}).get('summary', {}).get('total_count', 0),
                    'comments_count': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                    'insights': {}
                }

                # Try to get post insights separately (optional - may fail for small pages)
                try:
                    insights_result = self._make_request(f"{post.get('id')}/insights", params={
                        'metric': 'post_impressions,post_engaged_users'
                    })
                    for insight in insights_result.get('data', []):
                        name = insight.get('name')
                        values = insight.get('values', [])
                        if values:
                            processed_post['insights'][name] = values[0].get('value', 0)
                except Exception:
                    # Insights not available for this post - skip silently
                    pass

                processed_posts.append(processed_post)

            return {
                'posts': processed_posts,
                'paging': result.get('paging', {})
            }
        except Exception as e:
            # Return empty if posts request fails entirely
            return {
                'posts': [],
                'paging': {},
                'error': str(e)
            }
        finally:
            self.access_token = original_token

    def get_all_pages_stats(self, user):
        """
        Get aggregated stats across all connected Facebook pages for a user
        """
        from apps.platforms.models import SocialAccount

        pages = SocialAccount.objects.filter(
            user=user,
            platform='facebook',
            is_active=True
        )

        all_stats = []
        total_followers = 0
        total_impressions = 0
        total_engagements = 0
        total_posts_count = 0

        for page in pages:
            try:
                # Get page insights
                page_insights = self.get_page_insights(
                    page.platform_account_id,
                    page.access_token,
                    period='day',
                    date_preset='last_7d'
                )

                # Get recent posts
                posts_data = self.get_page_posts_with_insights(
                    page.platform_account_id,
                    page.access_token,
                    limit=10
                )

                # Extract metrics
                followers = page_insights.get('page_info', {}).get('followers_count', 0) or \
                           page_insights.get('page_info', {}).get('fan_count', 0) or 0

                # Sum up insights values
                page_impressions = 0
                page_engagements = 0

                for insight in page_insights.get('insights', []):
                    name = insight.get('name')
                    values = insight.get('values', [])
                    total_value = sum(v.get('value', 0) for v in values if isinstance(v.get('value'), (int, float)))

                    if name == 'page_impressions':
                        page_impressions = total_value
                    elif name == 'page_post_engagements':
                        page_engagements = total_value

                # Calculate post metrics
                posts = posts_data.get('posts', [])
                post_stats = {
                    'total_reactions': sum(p.get('reactions_count', 0) for p in posts),
                    'total_comments': sum(p.get('comments_count', 0) for p in posts),
                    'total_shares': sum(p.get('shares_count', 0) for p in posts),
                }

                page_stat = {
                    'page_id': page.platform_account_id,
                    'page_name': page.name,
                    'profile_picture': page.profile_picture_url,
                    'followers': followers,
                    'impressions_7d': page_impressions,
                    'engagements_7d': page_engagements,
                    'posts_count': len(posts),
                    'recent_posts': posts[:5],  # Top 5 recent posts
                    'post_stats': post_stats,
                    'engagement_rate': round((post_stats['total_reactions'] + post_stats['total_comments'] + post_stats['total_shares']) / max(len(posts), 1), 2) if posts else 0
                }

                all_stats.append(page_stat)
                total_followers += followers
                total_impressions += page_impressions
                total_engagements += page_engagements
                total_posts_count += len(posts)

            except Exception as e:
                all_stats.append({
                    'page_id': page.platform_account_id,
                    'page_name': page.name,
                    'profile_picture': page.profile_picture_url,
                    'error': str(e),
                    'followers': 0,
                    'impressions_7d': 0,
                    'engagements_7d': 0,
                    'posts_count': 0,
                })

        return {
            'pages': all_stats,
            'summary': {
                'total_pages': len(pages),
                'total_followers': total_followers,
                'total_impressions_7d': total_impressions,
                'total_engagements_7d': total_engagements,
                'total_posts': total_posts_count,
            }
        }
