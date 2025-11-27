from .models import FacebookPage
from apps.facebook_api.services import FacebookAPIService


class PageService:
    @staticmethod
    def sync_pages_from_facebook(user):
        fb_api = FacebookAPIService(user.facebook_access_token, user)
        pages_data = fb_api.get_pages()

        for page_data in pages_data.get('data', []):
            FacebookPage.objects.update_or_create(
                facebook_page_id=page_data['id'],
                user=user,
                defaults={
                    'name': page_data['name'],
                    'category': page_data.get('category', ''),
                    'access_token': page_data['access_token'],
                    'picture_url': page_data.get('picture', {}).get('data', {}).get('url')
                }
            )

        return FacebookPage.objects.filter(user=user, is_active=True)
