"""
Facebook Platform Service
Handles Facebook Pages API integration
"""
import requests
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from django.conf import settings

from .base import BasePlatformService, PostResult, AccountInfo


class FacebookService(BasePlatformService):
    """Service for Facebook Pages API"""

    PLATFORM_NAME = "facebook"

    def __init__(self):
        self.app_id = settings.FACEBOOK_APP_ID
        self.app_secret = settings.FACEBOOK_APP_SECRET
        self.api_version = settings.FACEBOOK_GRAPH_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Generate Facebook OAuth URL"""
        from urllib.parse import quote

        scopes = [
            'pages_show_list',
            'pages_read_engagement',
            'pages_manage_posts',
            'pages_manage_engagement',
            'pages_read_user_content',
            'pages_manage_metadata',  # Required for updating page info (about, description, etc.)
            'business_management',  # Required for accessing Business assets in newer API versions
        ]

        # Build query string manually, only encode redirect_uri
        # Facebook is particular about scope format (must be comma-separated, not encoded)
        scope_string = ','.join(scopes)
        query_string = f"client_id={self.app_id}&redirect_uri={quote(redirect_uri, safe='')}&state={state}&scope={scope_string}&response_type=code"

        return f"https://www.facebook.com/{self.api_version}/dialog/oauth?{query_string}"

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        import logging
        logger = logging.getLogger('platforms')

        logger.info("=" * 80)
        logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Starting token exchange process")
        logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Authorization code (first 30 chars): {code[:30]}...")
        logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Redirect URI: {redirect_uri}")
        logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] App ID: {self.app_id}")

        try:
            # Step 1: Exchange authorization code for short-lived token
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Step 1: Exchanging authorization code for short-lived token...")
            url = f"{self.base_url}/oauth/access_token"
            params = {
                'client_id': self.app_id,
                'client_secret': self.app_secret,
                'redirect_uri': redirect_uri,
                'code': code,
            }

            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Request URL: {url}")
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Request params: client_id={self.app_id}, redirect_uri={redirect_uri}")

            response = requests.get(url, params=params, timeout=30)

            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Response Status: {response.status_code}")
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Response Headers: {dict(response.headers)}")

            if response.status_code != 200:
                logger.error(f"[FACEBOOK_TOKEN_EXCHANGE] ✗ Failed to exchange code for token!")
                logger.error(f"[FACEBOOK_TOKEN_EXCHANGE] Response Status: {response.status_code}")
                logger.error(f"[FACEBOOK_TOKEN_EXCHANGE] Response Body: {response.text}")
                try:
                    error_data = response.json()
                    logger.error(f"[FACEBOOK_TOKEN_EXCHANGE] Error: {error_data}")
                except:
                    pass

            response.raise_for_status()
            data = response.json()

            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] ✓ Short-lived token obtained!")
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Short-lived token (first 30 chars): {data['access_token'][:30]}...")
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Short-lived token length: {len(data['access_token'])} chars")
            if 'expires_in' in data:
                logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Short-lived token expires in: {data['expires_in']} seconds (~{data['expires_in']/3600:.1f} hours)")

        except requests.exceptions.Timeout as e:
            logger.error(f"[FACEBOOK_TOKEN_EXCHANGE_ERROR] Timeout while exchanging code: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"[FACEBOOK_TOKEN_EXCHANGE_ERROR] Request exception: {str(e)}")
            logger.exception("Full exception traceback:")
            raise

        # Step 2: Exchange for long-lived token
        try:
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Step 2: Exchanging for long-lived token (60 days)...")
            long_lived = self._get_long_lived_token(data['access_token'])

            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] ✓ Long-lived token obtained!")
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Long-lived token (first 30 chars): {long_lived['access_token'][:30]}...")
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Long-lived token length: {len(long_lived['access_token'])} chars")

            if 'expires_in' in long_lived:
                expires_days = long_lived['expires_in'] / 86400  # Convert seconds to days
                logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Long-lived token expires in: {long_lived['expires_in']} seconds (~{expires_days:.0f} days)")
            else:
                logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Long-lived token expires in: 60 days (default)")

            expires_at = datetime.now() + timedelta(seconds=long_lived.get('expires_in', 5184000))
            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE] Token expiration date: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

            result = {
                'access_token': long_lived['access_token'],
                'expires_at': expires_at,
            }

            logger.info(f"[FACEBOOK_TOKEN_EXCHANGE_END] ✓ Token exchange completed successfully!")
            logger.info("=" * 80)

            return result

        except Exception as e:
            logger.error(f"[FACEBOOK_TOKEN_EXCHANGE_ERROR] Failed to get long-lived token: {str(e)}")
            logger.exception("Full exception traceback:")
            raise

    def _get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """Exchange short-lived token for long-lived token (60 days)"""
        import logging
        logger = logging.getLogger('platforms')

        logger.info(f"[FACEBOOK_LONG_LIVED_TOKEN] Exchanging short-lived token for long-lived token...")
        logger.info(f"[FACEBOOK_LONG_LIVED_TOKEN] Short-lived token (first 30 chars): {short_lived_token[:30]}...")

        try:
            url = f"{self.base_url}/oauth/access_token"
            params = {
                'grant_type': 'fb_exchange_token',
                'client_id': self.app_id,
                'client_secret': self.app_secret,
                'fb_exchange_token': short_lived_token,
            }

            logger.info(f"[FACEBOOK_LONG_LIVED_TOKEN] Request URL: {url}")
            logger.info(f"[FACEBOOK_LONG_LIVED_TOKEN] Grant type: fb_exchange_token")

            response = requests.get(url, params=params, timeout=30)

            logger.info(f"[FACEBOOK_LONG_LIVED_TOKEN] Response Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"[FACEBOOK_LONG_LIVED_TOKEN] ✗ Failed to get long-lived token!")
                logger.error(f"[FACEBOOK_LONG_LIVED_TOKEN] Response Status: {response.status_code}")
                logger.error(f"[FACEBOOK_LONG_LIVED_TOKEN] Response Body: {response.text}")

            response.raise_for_status()
            data = response.json()

            logger.info(f"[FACEBOOK_LONG_LIVED_TOKEN] ✓ Long-lived token exchange successful!")

            return data

        except Exception as e:
            logger.error(f"[FACEBOOK_LONG_LIVED_TOKEN_ERROR] Exception occurred: {str(e)}")
            logger.exception("Full exception traceback:")
            raise

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Facebook doesn't use refresh tokens for Pages.
        Page tokens don't expire if obtained from long-lived user token.
        """
        # For Facebook, we need to re-authenticate or extend the token
        return {
            'access_token': refresh_token,
            'expires_at': None,  # Page tokens don't expire
        }

    def get_account_info(self, access_token: str, account_id: Optional[str] = None) -> AccountInfo:
        """Get Facebook Page information"""
        endpoint = f"{self.base_url}/{account_id or 'me'}"
        fields = 'id,name,username,picture,category,followers_count,fan_count'

        response = requests.get(
            endpoint,
            params={'access_token': access_token, 'fields': fields}
        )
        response.raise_for_status()
        data = response.json()

        return AccountInfo(
            platform_account_id=data['id'],
            name=data.get('name', ''),
            username=data.get('username'),
            profile_picture_url=data.get('picture', {}).get('data', {}).get('url'),
            category=data.get('category'),
            followers_count=data.get('followers_count') or data.get('fan_count'),
            metadata={
                'fan_count': data.get('fan_count'),
            }
        )

    def get_accounts_list(self, access_token: str) -> List[AccountInfo]:
        """Get list of Facebook Pages the user manages"""
        import logging
        logger = logging.getLogger('platforms')

        logger.info("=" * 80)
        logger.info(f"[FACEBOOK_GET_PAGES] Starting to fetch Facebook Pages")
        logger.info(f"[FACEBOOK_GET_PAGES] API Version: {self.api_version}")
        logger.info(f"[FACEBOOK_GET_PAGES] Base URL: {self.base_url}")
        logger.info(f"[FACEBOOK_GET_PAGES] Access token (first 30 chars): {access_token[:30]}...")
        logger.info(f"[FACEBOOK_GET_PAGES] Access token length: {len(access_token)} chars")

        # Step 1: Verify token and get user info
        logger.info(f"[FACEBOOK_GET_PAGES] Step 1: Verifying token and getting user info...")
        try:
            me_url = f"{self.base_url}/me"
            me_params = {
                'access_token': access_token,
                'fields': 'id,name,email'
            }
            logger.info(f"[FACEBOOK_GET_PAGES] Request URL: {me_url}")
            logger.info(f"[FACEBOOK_GET_PAGES] Request params: fields={me_params['fields']}")

            me_response = requests.get(me_url, params=me_params, timeout=30)

            logger.info(f"[FACEBOOK_GET_PAGES] /me Response Status: {me_response.status_code}")
            logger.info(f"[FACEBOOK_GET_PAGES] /me Response Headers: {dict(me_response.headers)}")

            if me_response.status_code == 200:
                me_data = me_response.json()
                logger.info(f"[FACEBOOK_GET_PAGES] ✓ Token is valid!")
                logger.info(f"[FACEBOOK_GET_PAGES] User Name: {me_data.get('name')}")
                logger.info(f"[FACEBOOK_GET_PAGES] User ID: {me_data.get('id')}")
                logger.info(f"[FACEBOOK_GET_PAGES] User Email: {me_data.get('email', '(not provided)')}")
            else:
                logger.error(f"[FACEBOOK_GET_PAGES] ✗ Failed to get user info!")
                logger.error(f"[FACEBOOK_GET_PAGES] Response Status: {me_response.status_code}")
                logger.error(f"[FACEBOOK_GET_PAGES] Response Body: {me_response.text}")
                try:
                    error_data = me_response.json()
                    logger.error(f"[FACEBOOK_GET_PAGES] Error Type: {error_data.get('error', {}).get('type')}")
                    logger.error(f"[FACEBOOK_GET_PAGES] Error Message: {error_data.get('error', {}).get('message')}")
                    logger.error(f"[FACEBOOK_GET_PAGES] Error Code: {error_data.get('error', {}).get('code')}")
                except:
                    pass
                me_response.raise_for_status()

        except requests.exceptions.Timeout as e:
            logger.error(f"[FACEBOOK_GET_PAGES_ERROR] Timeout while getting user info: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"[FACEBOOK_GET_PAGES_ERROR] Request exception while getting user info: {str(e)}")
            logger.exception("Full exception traceback:")
            raise

        # Step 2: Get list of pages
        logger.info(f"[FACEBOOK_GET_PAGES] Step 2: Fetching pages managed by user...")
        try:
            accounts_url = f"{self.base_url}/me/accounts"
            accounts_params = {
                'access_token': access_token,
                'fields': 'id,name,username,picture,category,followers_count,access_token'
            }
            logger.info(f"[FACEBOOK_GET_PAGES] Request URL: {accounts_url}")
            logger.info(f"[FACEBOOK_GET_PAGES] Request params: fields={accounts_params['fields']}")

            response = requests.get(accounts_url, params=accounts_params, timeout=30)

            logger.info(f"[FACEBOOK_GET_PAGES] /me/accounts Response Status: {response.status_code}")
            logger.info(f"[FACEBOOK_GET_PAGES] /me/accounts Response Headers: {dict(response.headers)}")

            if response.status_code != 200:
                logger.error(f"[FACEBOOK_GET_PAGES] ✗ Failed to get pages!")
                logger.error(f"[FACEBOOK_GET_PAGES] Response Status: {response.status_code}")
                logger.error(f"[FACEBOOK_GET_PAGES] Response Body: {response.text}")
                try:
                    error_data = response.json()
                    logger.error(f"[FACEBOOK_GET_PAGES] Error Type: {error_data.get('error', {}).get('type')}")
                    logger.error(f"[FACEBOOK_GET_PAGES] Error Message: {error_data.get('error', {}).get('message')}")
                    logger.error(f"[FACEBOOK_GET_PAGES] Error Code: {error_data.get('error', {}).get('code')}")
                    logger.error(f"[FACEBOOK_GET_PAGES] Error Subcode: {error_data.get('error', {}).get('error_subcode')}")
                    logger.error(f"[FACEBOOK_GET_PAGES] Error User Title: {error_data.get('error', {}).get('error_user_title')}")
                    logger.error(f"[FACEBOOK_GET_PAGES] Error User Message: {error_data.get('error', {}).get('error_user_msg')}")
                except:
                    pass
                response.raise_for_status()

            data = response.json()
            logger.info(f"[FACEBOOK_GET_PAGES] ✓ API call successful!")
            logger.info(f"[FACEBOOK_GET_PAGES] Full API Response (formatted):")
            import json
            logger.info(json.dumps(data, indent=2, ensure_ascii=False))

            pages_data = data.get('data', [])
            logger.info(f"[FACEBOOK_GET_PAGES] Found {len(pages_data)} Facebook Page(s)")

            if len(pages_data) == 0:
                logger.warning(f"[FACEBOOK_GET_PAGES] ⚠️ No pages found! User may not manage any Facebook Pages.")
                logger.warning(f"[FACEBOOK_GET_PAGES] Please ensure:")
                logger.warning(f"  1. User has at least one Facebook Page")
                logger.warning(f"  2. User is an admin/editor of the Page")
                logger.warning(f"  3. Required permissions were granted: pages_show_list, pages_read_engagement, pages_manage_posts")

        except requests.exceptions.Timeout as e:
            logger.error(f"[FACEBOOK_GET_PAGES_ERROR] Timeout while getting pages: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"[FACEBOOK_GET_PAGES_ERROR] Request exception while getting pages: {str(e)}")
            logger.exception("Full exception traceback:")
            raise

        # Step 3: Parse and convert to AccountInfo objects
        logger.info(f"[FACEBOOK_GET_PAGES] Step 3: Parsing page data...")
        accounts = []

        for idx, page in enumerate(pages_data, 1):
            try:
                logger.info(f"[FACEBOOK_GET_PAGES] [{idx}/{len(pages_data)}] Processing page:")
                logger.info(f"  - Page ID: {page.get('id')}")
                logger.info(f"  - Page Name: {page.get('name')}")
                logger.info(f"  - Username: {page.get('username', '(not set)')}")
                logger.info(f"  - Category: {page.get('category', '(not set)')}")
                logger.info(f"  - Followers: {page.get('followers_count', 'N/A')}")
                logger.info(f"  - Has page access token: {'Yes' if page.get('access_token') else 'No'}")
                if page.get('access_token'):
                    logger.info(f"  - Page token (first 30 chars): {page.get('access_token')[:30]}...")

                account_info = AccountInfo(
                    platform_account_id=page['id'],
                    name=page.get('name', ''),
                    username=page.get('username'),
                    profile_picture_url=page.get('picture', {}).get('data', {}).get('url'),
                    category=page.get('category'),
                    followers_count=page.get('followers_count'),
                    metadata={
                        'page_access_token': page.get('access_token'),
                    }
                )
                accounts.append(account_info)
                logger.info(f"  ✓ Page parsed successfully")

            except Exception as e:
                logger.error(f"[FACEBOOK_GET_PAGES_ERROR] Failed to parse page {page.get('id', 'UNKNOWN')}: {str(e)}")
                logger.exception("Full exception traceback:")
                continue

        logger.info(f"[FACEBOOK_GET_PAGES] ✓ Successfully parsed {len(accounts)}/{len(pages_data)} page(s)")
        logger.info(f"[FACEBOOK_GET_PAGES_END] Returning {len(accounts)} account(s)")
        logger.info("=" * 80)

        return accounts

    def publish_post(
        self,
        access_token: str,
        account_id: str,
        content: str,
        media_urls: Optional[List[str]] = None,
        media_type: str = 'none',
        link_url: Optional[str] = None,
        scheduled_time: Optional[datetime] = None,
        **kwargs
    ) -> PostResult:
        """Publish a post to Facebook Page"""
        try:
            if media_type == 'video' and media_urls:
                return self._publish_video(access_token, account_id, content, media_urls[0], scheduled_time)
            elif media_type in ['image', 'carousel'] and media_urls:
                return self._publish_photos(access_token, account_id, content, media_urls, scheduled_time)
            else:
                return self._publish_text(access_token, account_id, content, link_url, scheduled_time)

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    pass
            return PostResult(success=False, error_message=error_msg)

    def _publish_text(
        self,
        access_token: str,
        account_id: str,
        content: str,
        link_url: Optional[str] = None,
        scheduled_time: Optional[datetime] = None
    ) -> PostResult:
        """Publish text/link post"""
        data = {
            'message': content,
            'access_token': access_token,
        }

        if link_url:
            data['link'] = link_url

        if scheduled_time:
            data['published'] = False
            data['scheduled_publish_time'] = int(scheduled_time.timestamp())

        response = requests.post(f"{self.base_url}/{account_id}/feed", data=data)
        response.raise_for_status()
        result = response.json()

        return PostResult(
            success=True,
            platform_post_id=result.get('id'),
            platform_post_url=f"https://facebook.com/{result.get('id')}"
        )

    def _publish_photos(
        self,
        access_token: str,
        account_id: str,
        content: str,
        photo_urls: List[str],
        scheduled_time: Optional[datetime] = None
    ) -> PostResult:
        """Publish photo(s) post"""
        if len(photo_urls) == 1:
            # Single photo - upload file directly
            file_path = self._get_local_file_path(photo_urls[0])

            if file_path and os.path.exists(file_path):
                # Upload file directly (works with localhost)
                with open(file_path, 'rb') as image_file:
                    files = {'source': image_file}
                    data = {
                        'caption': content,
                        'access_token': access_token,
                    }

                    if scheduled_time:
                        data['published'] = False
                        data['scheduled_publish_time'] = int(scheduled_time.timestamp())

                    response = requests.post(
                        f"{self.base_url}/{account_id}/photos",
                        data=data,
                        files=files
                    )
                    response.raise_for_status()
                    result = response.json()

                    return PostResult(
                        success=True,
                        platform_post_id=result.get('id'),
                        platform_post_url=f"https://facebook.com/{result.get('id')}"
                    )
            else:
                # Fallback to URL method (for public URLs)
                data = {
                    'url': photo_urls[0],
                    'caption': content,
                    'access_token': access_token,
                }

                if scheduled_time:
                    data['published'] = False
                    data['scheduled_publish_time'] = int(scheduled_time.timestamp())

                response = requests.post(f"{self.base_url}/{account_id}/photos", data=data)
                response.raise_for_status()
                result = response.json()

                return PostResult(
                    success=True,
                    platform_post_id=result.get('id'),
                    platform_post_url=f"https://facebook.com/{result.get('id')}"
                )
        else:
            # Multiple photos - create unpublished photos first
            photo_ids = []
            for url in photo_urls:
                file_path = self._get_local_file_path(url)

                if file_path and os.path.exists(file_path):
                    # Upload file directly
                    with open(file_path, 'rb') as image_file:
                        files = {'source': image_file}
                        data = {
                            'published': False,
                            'access_token': access_token,
                        }
                        response = requests.post(
                            f"{self.base_url}/{account_id}/photos",
                            data=data,
                            files=files
                        )
                        response.raise_for_status()
                        photo_ids.append(response.json()['id'])
                else:
                    # Fallback to URL method
                    response = requests.post(
                        f"{self.base_url}/{account_id}/photos",
                        data={
                            'url': url,
                            'published': False,
                            'access_token': access_token,
                        }
                    )
                    response.raise_for_status()
                    photo_ids.append(response.json()['id'])

            # Create post with attached photos
            data = {
                'message': content,
                'access_token': access_token,
            }

            for i, photo_id in enumerate(photo_ids):
                data[f'attached_media[{i}]'] = f'{{"media_fbid":"{photo_id}"}}'

            if scheduled_time:
                data['published'] = False
                data['scheduled_publish_time'] = int(scheduled_time.timestamp())

            response = requests.post(f"{self.base_url}/{account_id}/feed", data=data)
            response.raise_for_status()
            result = response.json()

            return PostResult(
                success=True,
                platform_post_id=result.get('id'),
                platform_post_url=f"https://facebook.com/{result.get('id')}"
            )

    def _publish_video(
        self,
        access_token: str,
        account_id: str,
        content: str,
        video_url: str,
        scheduled_time: Optional[datetime] = None
    ) -> PostResult:
        """Publish video post"""
        file_path = self._get_local_file_path(video_url)

        if file_path and os.path.exists(file_path):
            # Upload file directly (works with localhost)
            with open(file_path, 'rb') as video_file:
                files = {'source': video_file}
                data = {
                    'description': content,
                    'access_token': access_token,
                }

                if scheduled_time:
                    data['published'] = False
                    data['scheduled_publish_time'] = int(scheduled_time.timestamp())

                response = requests.post(
                    f"{self.base_url}/{account_id}/videos",
                    data=data,
                    files=files
                )
                response.raise_for_status()
                result = response.json()

                return PostResult(
                    success=True,
                    platform_post_id=result.get('id'),
                    platform_post_url=f"https://facebook.com/{result.get('id')}"
                )
        else:
            # Fallback to URL method (for public URLs)
            data = {
                'file_url': video_url,
                'description': content,
                'access_token': access_token,
            }

            if scheduled_time:
                data['published'] = False
                data['scheduled_publish_time'] = int(scheduled_time.timestamp())

            response = requests.post(f"{self.base_url}/{account_id}/videos", data=data)
            response.raise_for_status()
            result = response.json()

            return PostResult(
                success=True,
                platform_post_id=result.get('id'),
                platform_post_url=f"https://facebook.com/{result.get('id')}"
            )

    # ============ Story Publishing Methods ============

    def _publish_photo_story(
        self,
        access_token: str,
        account_id: str,
        photo_url: str,
    ) -> PostResult:
        """
        Publish a photo to Facebook Page Story.

        Steps:
        1. Upload photo as unpublished to get photo_id
        2. Create story using photo_id
        """
        import logging
        logger = logging.getLogger('platforms')

        try:
            # Step 1: Upload photo as unpublished
            file_path = self._get_local_file_path(photo_url)

            if file_path and os.path.exists(file_path):
                # Upload from local file
                with open(file_path, 'rb') as image_file:
                    files = {'source': image_file}
                    data = {
                        'published': 'false',
                        'access_token': access_token,
                    }
                    response = requests.post(
                        f"{self.base_url}/{account_id}/photos",
                        data=data,
                        files=files
                    )
            else:
                # Upload from URL
                data = {
                    'url': photo_url,
                    'published': 'false',
                    'access_token': access_token,
                }
                response = requests.post(
                    f"{self.base_url}/{account_id}/photos",
                    data=data
                )

            response.raise_for_status()
            photo_result = response.json()
            photo_id = photo_result.get('id')

            if not photo_id:
                return PostResult(
                    success=False,
                    platform_post_id=None,
                    platform_post_url=None,
                    error_message="Failed to upload photo for story"
                )

            logger.info(f"[FACEBOOK_STORY] Uploaded unpublished photo: {photo_id}")

            # Step 2: Create story using photo_id
            story_response = requests.post(
                f"{self.base_url}/{account_id}/photo_stories",
                data={
                    'photo_id': photo_id,
                    'access_token': access_token,
                }
            )
            story_response.raise_for_status()
            story_result = story_response.json()

            logger.info(f"[FACEBOOK_STORY] Photo story created: {story_result}")

            return PostResult(
                success=True,
                platform_post_id=story_result.get('post_id') or story_result.get('id'),
                platform_post_url=None  # Stories don't have permanent URLs
            )

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    pass
            logger.error(f"[FACEBOOK_STORY] Photo story failed: {error_msg}")
            return PostResult(
                success=False,
                platform_post_id=None,
                platform_post_url=None,
                error_message=error_msg
            )

    def _publish_video_story(
        self,
        access_token: str,
        account_id: str,
        video_url: str,
    ) -> PostResult:
        """
        Publish a video to Facebook Page Story.

        Steps:
        1. Initialize upload session
        2. Upload video file
        3. Finish and publish story

        Note: Video must be <= 60 seconds for stories
        """
        import logging
        logger = logging.getLogger('platforms')

        try:
            # Step 1: Initialize upload session
            init_response = requests.post(
                f"{self.base_url}/{account_id}/video_stories",
                data={
                    'upload_phase': 'start',
                    'access_token': access_token,
                }
            )
            init_response.raise_for_status()
            init_data = init_response.json()

            video_id = init_data.get('video_id')
            upload_url = init_data.get('upload_url')

            if not video_id or not upload_url:
                return PostResult(
                    success=False,
                    platform_post_id=None,
                    platform_post_url=None,
                    error_message="Failed to initialize video story upload"
                )

            logger.info(f"[FACEBOOK_STORY] Video upload initialized: video_id={video_id}")

            # Step 2: Upload video file
            file_path = self._get_local_file_path(video_url)

            if file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as video_file:
                    upload_response = requests.post(
                        upload_url,
                        files={'file': video_file}
                    )
            else:
                # For remote URLs, use file_url header
                upload_response = requests.post(
                    upload_url,
                    headers={'file_url': video_url}
                )

            upload_response.raise_for_status()
            logger.info(f"[FACEBOOK_STORY] Video uploaded successfully")

            # Step 3: Finish and publish
            finish_response = requests.post(
                f"{self.base_url}/{account_id}/video_stories",
                data={
                    'upload_phase': 'finish',
                    'video_id': video_id,
                    'access_token': access_token,
                }
            )
            finish_response.raise_for_status()
            finish_result = finish_response.json()

            logger.info(f"[FACEBOOK_STORY] Video story created: {finish_result}")

            return PostResult(
                success=True,
                platform_post_id=finish_result.get('post_id') or finish_result.get('id'),
                platform_post_url=None
            )

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    pass
            logger.error(f"[FACEBOOK_STORY] Video story failed: {error_msg}")
            return PostResult(
                success=False,
                platform_post_id=None,
                platform_post_url=None,
                error_message=error_msg
            )

    def publish_story(
        self,
        access_token: str,
        account_id: str,
        media_url: str,
        media_type: str = 'image',
    ) -> PostResult:
        """
        Publish content as a Facebook Page Story.

        Args:
            access_token: Page access token
            account_id: Facebook Page ID
            media_url: URL or path to media file
            media_type: 'image' or 'video'

        Returns:
            PostResult with success status

        Note: Stories require image or video. Text-only stories are not supported.
        """
        try:
            if media_type == 'video':
                return self._publish_video_story(access_token, account_id, media_url)
            elif media_type in ['image', 'carousel']:
                # For carousel, use first image for story
                return self._publish_photo_story(access_token, account_id, media_url)
            else:
                return PostResult(
                    success=False,
                    platform_post_id=None,
                    platform_post_url=None,
                    error_message="Stories require image or video content"
                )
        except Exception as e:
            return PostResult(
                success=False,
                platform_post_id=None,
                platform_post_url=None,
                error_message=str(e)
            )

    def delete_post(self, access_token: str, post_id: str) -> bool:
        """Delete a Facebook post"""
        response = requests.delete(
            f"{self.base_url}/{post_id}",
            params={'access_token': access_token}
        )
        return response.status_code == 200

    def _get_local_file_path(self, url: str) -> Optional[str]:
        """
        Convert a media URL to local file path if it's a localhost/LAN URL or relative path.
        Returns None if URL is external.
        """
        from urllib.parse import urlparse

        # Handle relative paths directly (e.g., /media/uploads/4/uuid.jpg)
        if url.startswith('/media/'):
            relative_path = url[len('/media/'):]  # Remove /media/ prefix
            absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            if os.path.exists(absolute_path):
                return absolute_path

        parsed = urlparse(url)

        # Check if it's a local URL (localhost or LAN IP)
        if parsed.hostname in ['localhost', '127.0.0.1'] or (
            parsed.hostname and parsed.hostname.startswith('192.168.')
        ):
            # Extract the path (e.g., /media/uploads/4/uuid.jpg)
            media_path = parsed.path

            # Convert to absolute file path
            # MEDIA_URL is /media/ and MEDIA_ROOT is the actual directory
            if media_path.startswith('/media/'):
                relative_path = media_path[len('/media/'):]  # Remove /media/ prefix
                absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                return absolute_path

        return None

    def validate_content(self, content: str, media_type: str = 'none') -> Dict[str, Any]:
        """Validate Facebook post content"""
        errors = []

        # Facebook has 63,206 character limit
        if len(content) > 63206:
            errors.append("Content exceeds Facebook's 63,206 character limit")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    # ============ Page Settings Methods ============

    def get_page_details(self, access_token: str, page_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a Facebook Page.
        Returns all editable fields.
        """
        import logging
        logger = logging.getLogger('platforms')

        fields = [
            'id', 'name', 'username', 'about', 'description', 'category',
            'category_list', 'phone', 'website', 'emails', 'single_line_address',
            'location', 'hours', 'cover', 'picture.type(large)',
            'fan_count', 'followers_count', 'link'
        ]

        endpoint = f"{self.base_url}/{page_id}"
        params = {
            'access_token': access_token,
            'fields': ','.join(fields)
        }

        logger.info(f"[FACEBOOK_PAGE_DETAILS] Fetching details for page {page_id}")

        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            logger.info(f"[FACEBOOK_PAGE_DETAILS] Successfully fetched details for {data.get('name')}")

            return {
                'success': True,
                'data': {
                    'id': data.get('id'),
                    'name': data.get('name'),
                    'username': data.get('username'),
                    'about': data.get('about', ''),
                    'description': data.get('description', ''),
                    'category': data.get('category'),
                    'category_list': data.get('category_list', []),
                    'phone': data.get('phone', ''),
                    'website': data.get('website', ''),
                    'emails': data.get('emails', []),
                    'single_line_address': data.get('single_line_address', ''),
                    'location': data.get('location', {}),
                    'hours': data.get('hours', {}),
                    'cover': data.get('cover', {}),
                    'picture': data.get('picture', {}).get('data', {}),
                    'fan_count': data.get('fan_count', 0),
                    'followers_count': data.get('followers_count', 0),
                    'link': data.get('link', ''),
                }
            }
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    pass
            logger.error(f"[FACEBOOK_PAGE_DETAILS] Error: {error_msg}")
            return {'success': False, 'error': error_msg}

    def update_page_info(
        self,
        access_token: str,
        page_id: str,
        about: Optional[str] = None,
        description: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        emails: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update Facebook Page information.
        Only updates fields that are provided (not None).
        """
        import logging
        logger = logging.getLogger('platforms')

        endpoint = f"{self.base_url}/{page_id}"

        data = {'access_token': access_token}

        # Only add fields that are provided
        if about is not None:
            data['about'] = about
        if description is not None:
            data['description'] = description
        if phone is not None:
            data['phone'] = phone
        if website is not None:
            data['website'] = website
        if emails is not None:
            data['emails'] = emails

        if len(data) <= 1:  # Only access_token
            return {'success': False, 'error': 'No fields to update'}

        logger.info(f"[FACEBOOK_UPDATE_PAGE] Updating page {page_id} with fields: {list(data.keys())}")

        try:
            response = requests.post(endpoint, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"[FACEBOOK_UPDATE_PAGE] Successfully updated page {page_id}")

            return {
                'success': result.get('success', True),
                'message': 'Page information updated successfully'
            }
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    pass
            logger.error(f"[FACEBOOK_UPDATE_PAGE] Error: {error_msg}")
            return {'success': False, 'error': error_msg}

    def update_page_picture(
        self,
        access_token: str,
        page_id: str,
        image_url: Optional[str] = None,
        image_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update Facebook Page profile picture.
        Can use either a URL or a local file path.

        Note: This endpoint may be unstable according to Facebook API reports.
        """
        import logging
        logger = logging.getLogger('platforms')

        endpoint = f"{self.base_url}/{page_id}/picture"

        logger.info(f"[FACEBOOK_UPDATE_PICTURE] Updating profile picture for page {page_id}")

        try:
            if image_file_path and os.path.exists(image_file_path):
                # Upload from local file
                with open(image_file_path, 'rb') as image_file:
                    files = {'source': image_file}
                    data = {'access_token': access_token}
                    response = requests.post(endpoint, data=data, files=files, timeout=60)
            elif image_url:
                # Upload from URL
                data = {
                    'access_token': access_token,
                    'picture': image_url,
                }
                response = requests.post(endpoint, data=data, timeout=60)
            else:
                return {'success': False, 'error': 'No image provided'}

            response.raise_for_status()
            result = response.json()

            logger.info(f"[FACEBOOK_UPDATE_PICTURE] Successfully updated profile picture for page {page_id}")

            return {
                'success': result.get('success', True),
                'message': 'Profile picture updated successfully'
            }
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                    error_code = error_data.get('error', {}).get('code')
                    if error_code == 100:
                        error_msg = "Facebook API error: This endpoint may be temporarily unavailable. Please try again later."
                except:
                    pass
            logger.error(f"[FACEBOOK_UPDATE_PICTURE] Error: {error_msg}")
            return {'success': False, 'error': error_msg}

    def update_page_cover(
        self,
        access_token: str,
        page_id: str,
        image_url: Optional[str] = None,
        image_file_path: Optional[str] = None,
        offset_y: int = 0,
    ) -> Dict[str, Any]:
        """
        Update Facebook Page cover photo.
        Can use either a URL or a local file path.

        Args:
            offset_y: Vertical offset for the cover photo (0-100)
        """
        import logging
        logger = logging.getLogger('platforms')

        logger.info(f"[FACEBOOK_UPDATE_COVER] Updating cover photo for page {page_id}")

        try:
            # First, upload the photo to the page's photos
            photos_endpoint = f"{self.base_url}/{page_id}/photos"

            if image_file_path and os.path.exists(image_file_path):
                with open(image_file_path, 'rb') as image_file:
                    files = {'source': image_file}
                    data = {
                        'access_token': access_token,
                        'published': 'false',
                    }
                    response = requests.post(photos_endpoint, data=data, files=files, timeout=60)
            elif image_url:
                # Check if it's a local URL
                local_path = self._get_local_file_path(image_url)
                if local_path and os.path.exists(local_path):
                    with open(local_path, 'rb') as image_file:
                        files = {'source': image_file}
                        data = {
                            'access_token': access_token,
                            'published': 'false',
                        }
                        response = requests.post(photos_endpoint, data=data, files=files, timeout=60)
                else:
                    data = {
                        'access_token': access_token,
                        'url': image_url,
                        'published': 'false',
                    }
                    response = requests.post(photos_endpoint, data=data, timeout=60)
            else:
                return {'success': False, 'error': 'No image provided'}

            response.raise_for_status()
            photo_result = response.json()
            photo_id = photo_result.get('id')

            if not photo_id:
                return {'success': False, 'error': 'Failed to upload cover photo'}

            # Now set this photo as the cover
            page_endpoint = f"{self.base_url}/{page_id}"
            cover_data = {
                'access_token': access_token,
                'cover': photo_id,
                'offset_y': offset_y,
            }

            cover_response = requests.post(page_endpoint, data=cover_data, timeout=30)
            cover_response.raise_for_status()

            logger.info(f"[FACEBOOK_UPDATE_COVER] Successfully updated cover photo for page {page_id}")

            return {
                'success': True,
                'message': 'Cover photo updated successfully',
                'photo_id': photo_id
            }
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    pass
            logger.error(f"[FACEBOOK_UPDATE_COVER] Error: {error_msg}")
            return {'success': False, 'error': error_msg}
