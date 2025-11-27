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
