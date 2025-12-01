"""
Platforms API Endpoints
Unified API for managing multiple social media platforms
"""
import os
import secrets
import logging
from ninja import Router, Form
from typing import List, Optional
from django.utils import timezone
from django.http import Http404, HttpResponseRedirect

logger = logging.getLogger('platforms')


def get_base_url(request) -> str:
    """
    Get base URL, respecting X-Forwarded-Proto header from reverse proxy (Nginx).
    """
    base_url = os.getenv('BASE_URL')
    if base_url:
        return base_url

    # Check for X-Forwarded-Proto header (set by Nginx/reverse proxy)
    forwarded_proto = request.META.get('HTTP_X_FORWARDED_PROTO')
    if forwarded_proto:
        scheme = forwarded_proto
    else:
        scheme = request.scheme

    host = request.get_host()
    return f"{scheme}://{host}"


from api.dependencies import AuthBearer
from .models import SocialAccount, SocialPost, PostPublishStatus, PlatformType
from .schemas import (
    SocialAccountSchema,
    SocialPostSchema,
    SocialPostCreateSchema,
    PostDetailSchema,
    PublishStatusSchema,
    OAuthUrlSchema,
    PlatformInfoSchema,
    ValidationResultSchema,
)
from .services import get_platform_service

router = Router()


# ===========================================
# Platform Information
# ===========================================

@router.get("/info", response=List[PlatformInfoSchema])
def get_platforms_info(request):
    """Get information about all supported platforms"""
    platforms = [
        {
            'id': 'facebook',
            'name': 'Facebook',
            'icon': 'Facebook',
            'supported_features': ['text', 'image', 'video', 'carousel', 'link', 'schedule'],
        },
        # Instagram, Zalo, TikTok - Coming soon
        # {
        #     'id': 'instagram',
        #     'name': 'Instagram',
        #     'icon': 'Instagram',
        #     'supported_features': ['image', 'video', 'carousel', 'reels'],
        # },
        # {
        #     'id': 'zalo',
        #     'name': 'Zalo OA',
        #     'icon': 'MessageCircle',
        #     'supported_features': ['text', 'image'],
        # },
        # {
        #     'id': 'tiktok',
        #     'name': 'TikTok',
        #     'icon': 'Music',
        #     'supported_features': ['video'],
        # },
    ]

    # Add connected accounts count if user is authenticated
    if hasattr(request, 'auth') and request.auth:
        for platform in platforms:
            platform['connected_accounts'] = SocialAccount.objects.filter(
                user=request.auth,
                platform=platform['id'],
                is_active=True
            ).count()

    return platforms


# ===========================================
# OAuth Authentication
# ===========================================

@router.get("/oauth/{platform}/url", auth=AuthBearer(), response=OAuthUrlSchema)
def get_oauth_url(request, platform: str):
    """Get OAuth authorization URL for a platform"""
    try:
        service = get_platform_service(platform)
    except ValueError as e:
        raise Http404(str(e))

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session or cache (for production)
    # For now, we'll include user_id in state
    state = f"{request.auth.id}_{state}"

    # Dynamic base URL - supports reverse proxy (Nginx) with HTTPS
    base_url = get_base_url(request)
    redirect_uri = f"{base_url}/api/platforms/oauth/{platform}/callback"

    auth_url = service.get_auth_url(redirect_uri, state)

    return {
        'auth_url': auth_url,
        'state': state,
    }


@router.get("/oauth/{platform}/callback")
def oauth_callback(request, platform: str, code: str, state: str):
    """Handle OAuth callback and save connected account"""
    logger.info("=" * 80)
    logger.info(f"[OAUTH_CALLBACK_START] Platform: {platform}")
    logger.info(f"[OAUTH_CALLBACK] Received code: {code[:20]}... (truncated)")
    logger.info(f"[OAUTH_CALLBACK] Received state: {state}")

    try:
        service = get_platform_service(platform)
        logger.info(f"[OAUTH_CALLBACK] Platform service loaded: {service.__class__.__name__}")
    except ValueError as e:
        logger.error(f"[OAUTH_CALLBACK_ERROR] Invalid platform: {platform} - {str(e)}")
        raise Http404(str(e))

    # Extract user_id from state
    try:
        user_id = int(state.split('_')[0])
        logger.info(f"[OAUTH_CALLBACK] Extracted user_id from state: {user_id}")
    except Exception as e:
        logger.error(f"[OAUTH_CALLBACK_ERROR] Failed to extract user_id from state: {state} - {str(e)}")
        raise Http404("Invalid state parameter")

    from apps.auth.models import User
    try:
        user = User.objects.get(id=user_id)
        logger.info(f"[OAUTH_CALLBACK] User found: {user.email} (ID: {user.id})")
    except User.DoesNotExist:
        logger.error(f"[OAUTH_CALLBACK_ERROR] User not found with ID: {user_id}")
        raise Http404("User not found")

    # Dynamic base URL - must match the URL used in get_oauth_url
    base_url = get_base_url(request)
    redirect_uri = f"{base_url}/api/platforms/oauth/{platform}/callback"
    logger.info(f"[OAUTH_CALLBACK] Base URL: {base_url}")
    logger.info(f"[OAUTH_CALLBACK] Redirect URI: {redirect_uri}")

    # Exchange code for token
    try:
        logger.info(f"[OAUTH_CALLBACK] Exchanging authorization code for access token...")
        token_data = service.exchange_code_for_token(code, redirect_uri)
        logger.info(f"[OAUTH_CALLBACK] ✓ Token exchange successful!")
        logger.info(f"[OAUTH_CALLBACK] Token (first 30 chars): {token_data['access_token'][:30]}...")
        if 'expires_at' in token_data:
            logger.info(f"[OAUTH_CALLBACK] Token expires at: {token_data['expires_at']}")
    except Exception as e:
        logger.error(f"[OAUTH_CALLBACK_ERROR] Token exchange failed: {str(e)}")
        logger.exception("Full exception traceback:")
        raise

    # Get accounts list
    try:
        logger.info(f"[OAUTH_CALLBACK] Fetching accounts list from {platform}...")
        accounts = service.get_accounts_list(token_data['access_token'])
        logger.info(f"[OAUTH_CALLBACK] ✓ Found {len(accounts)} account(s)")
    except Exception as e:
        logger.error(f"[OAUTH_CALLBACK_ERROR] Failed to get accounts list: {str(e)}")
        logger.exception("Full exception traceback:")
        raise

    # Save each account
    saved_accounts = []
    logger.info(f"[OAUTH_CALLBACK] Saving {len(accounts)} account(s) to database...")

    for idx, account_info in enumerate(accounts, 1):
        try:
            # Get page-specific access token if available
            access_token = account_info.metadata.get('page_access_token', token_data['access_token'])

            logger.info(f"[OAUTH_CALLBACK] [{idx}/{len(accounts)}] Processing account:")
            logger.info(f"  - Platform Account ID: {account_info.platform_account_id}")
            logger.info(f"  - Name: {account_info.name}")
            logger.info(f"  - Username: {account_info.username or '(not set)'}")
            logger.info(f"  - Category: {account_info.category or '(not set)'}")
            logger.info(f"  - Access Token length: {len(access_token)} chars")

            social_account, created = SocialAccount.objects.update_or_create(
                platform=platform,
                platform_account_id=account_info.platform_account_id,
                defaults={
                    'user': user,
                    'name': account_info.name,
                    'username': account_info.username or '',
                    'profile_picture_url': account_info.profile_picture_url,
                    'category': account_info.category or '',
                    'access_token': access_token,
                    'token_expires_at': token_data.get('expires_at'),
                    'metadata': account_info.metadata or {},
                    'is_active': True,
                    'last_synced_at': timezone.now(),
                }
            )

            action = "Created new" if created else "Updated existing"
            logger.info(f"  ✓ {action} account in database (DB ID: {social_account.id})")
            saved_accounts.append(social_account)

        except Exception as e:
            logger.error(f"[OAUTH_CALLBACK_ERROR] Failed to save account {account_info.platform_account_id}: {str(e)}")
            logger.exception("Full exception traceback:")

    logger.info(f"[OAUTH_CALLBACK] ✓ Successfully saved {len(saved_accounts)}/{len(accounts)} account(s)")

    # Redirect to frontend - use dynamic URL from env
    frontend_url = os.getenv('FRONTEND_URL')
    if not frontend_url:
        # Build from individual env vars or auto-detect
        forwarded_proto = request.META.get('HTTP_X_FORWARDED_PROTO')
        scheme = forwarded_proto if forwarded_proto else request.scheme
        host = os.getenv('FRONTEND_HOST') or request.get_host().split(':')[0]
        port = os.getenv('FRONTEND_PORT', '')

        if port:
            frontend_url = f"{scheme}://{host}:{port}"
        else:
            frontend_url = f"{scheme}://{host}"

    redirect_url = f"{frontend_url}/?platform={platform}&connected={len(saved_accounts)}"
    logger.info(f"[OAUTH_CALLBACK] Redirecting to frontend: {redirect_url}")
    logger.info(f"[OAUTH_CALLBACK_END] ✓ OAuth flow completed successfully!")
    logger.info("=" * 80)

    return HttpResponseRedirect(redirect_url)


# ===========================================
# Account Management
# ===========================================

@router.get("/accounts", auth=AuthBearer(), response=List[SocialAccountSchema])
def list_accounts(request, platform: Optional[str] = None):
    """List all connected social accounts"""
    queryset = SocialAccount.objects.filter(user=request.auth, is_active=True)

    if platform:
        queryset = queryset.filter(platform=platform)

    return queryset.order_by('platform', 'name')


@router.get("/accounts/{account_id}", auth=AuthBearer(), response=SocialAccountSchema)
def get_account(request, account_id: int):
    """Get a specific social account"""
    try:
        return SocialAccount.objects.get(id=account_id, user=request.auth)
    except SocialAccount.DoesNotExist:
        raise Http404("Account not found")


@router.delete("/accounts/{account_id}", auth=AuthBearer())
def disconnect_account(request, account_id: int):
    """Disconnect/remove a social account"""
    try:
        account = SocialAccount.objects.get(id=account_id, user=request.auth)
        account.is_active = False
        account.save()
        return {"success": True, "message": "Account disconnected"}
    except SocialAccount.DoesNotExist:
        raise Http404("Account not found")


@router.post("/accounts/{account_id}/refresh", auth=AuthBearer())
def refresh_account_token(request, account_id: int):
    """Refresh access token for an account"""
    try:
        account = SocialAccount.objects.get(id=account_id, user=request.auth)
    except SocialAccount.DoesNotExist:
        raise Http404("Account not found")

    service = get_platform_service(account.platform)

    try:
        token_data = service.refresh_access_token(account.refresh_token or account.access_token)
        account.access_token = token_data['access_token']
        account.token_expires_at = token_data.get('expires_at')
        account.last_synced_at = timezone.now()
        account.save()
        return {"success": True, "message": "Token refreshed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ===========================================
# Post Management
# ===========================================

@router.get("/posts", auth=AuthBearer(), response=List[SocialPostSchema])
def list_posts(request, status: Optional[str] = None):
    """List all social posts"""
    queryset = SocialPost.objects.filter(created_by=request.auth)

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by('-created_at')


@router.get("/posts/{post_id}", auth=AuthBearer(), response=PostDetailSchema)
def get_post(request, post_id: int):
    """Get a specific post with publish statuses"""
    try:
        post = SocialPost.objects.get(id=post_id, created_by=request.auth)
    except SocialPost.DoesNotExist:
        raise Http404("Post not found")

    # Get publish statuses
    statuses = []
    for ps in post.publish_statuses.all():
        statuses.append({
            'account_id': ps.account.id,
            'account_name': ps.account.name,
            'platform': ps.account.platform,
            'status': ps.status,
            'platform_post_id': ps.platform_post_id,
            'platform_post_url': ps.platform_post_url,
            'error_message': ps.error_message,
            'published_at': ps.published_at,
        })

    return {
        'id': post.id,
        'content': post.content,
        'title': post.title,
        'media_urls': post.media_urls,
        'media_type': post.media_type,
        'status': post.status,
        'scheduled_at': post.scheduled_at,
        'publish_statuses': statuses,
        'created_at': post.created_at,
    }


@router.post("/posts", auth=AuthBearer(), response=SocialPostSchema)
def create_post(request, data: SocialPostCreateSchema):
    """Create a new social post"""
    # Validate target accounts belong to user
    accounts = SocialAccount.objects.filter(
        id__in=data.target_account_ids,
        user=request.auth,
        is_active=True
    )

    if not accounts.exists():
        raise Http404("No valid target accounts found")

    # Create post
    post = SocialPost.objects.create(
        created_by=request.auth,
        content=data.content,
        title=data.title,
        media_urls=data.media_urls,
        media_type=data.media_type,
        link_url=data.link_url,
        scheduled_at=data.scheduled_at,
        status='scheduled' if data.scheduled_at else 'draft',
    )

    # Create publish status for each account
    for account in accounts:
        PostPublishStatus.objects.create(
            post=post,
            account=account,
            status='pending',
        )

    return post


@router.post("/posts/{post_id}/publish", auth=AuthBearer())
def publish_post(request, post_id: int):
    """Publish a post to all target accounts"""
    logger.info(f"[PUBLISH_START] Post ID: {post_id}, User: {request.auth.email}")

    try:
        post = SocialPost.objects.get(id=post_id, created_by=request.auth)
    except SocialPost.DoesNotExist:
        logger.error(f"[PUBLISH_ERROR] Post {post_id} not found for user {request.auth.email}")
        raise Http404("Post not found")

    if post.status == 'published':
        logger.warning(f"[PUBLISH_SKIP] Post {post_id} already published")
        return {"success": False, "error": "Post already published"}

    logger.info(f"[PUBLISH_INFO] Post {post_id} | Content length: {len(post.content)} | Media type: {post.media_type} | Media URLs: {post.media_urls}")

    post.status = 'publishing'
    post.save()

    results = []
    success_count = 0
    fail_count = 0

    for publish_status in post.publish_statuses.filter(status='pending'):
        account = publish_status.account
        logger.info(f"[PUBLISH_ACCOUNT] Post {post_id} → {account.platform}/{account.name} (ID: {account.platform_account_id})")

        service = get_platform_service(account.platform)

        # Validate content
        validation = service.validate_content(post.content, post.media_type)
        if not validation['valid']:
            error_msg = '; '.join(validation['errors'])
            logger.error(f"[PUBLISH_VALIDATION_FAILED] Post {post_id} → {account.name}: {error_msg}")
            publish_status.status = 'failed'
            publish_status.error_message = error_msg
            publish_status.save()
            fail_count += 1
            results.append({
                'account': account.name,
                'success': False,
                'error': publish_status.error_message
            })
            continue

        # Publish
        publish_status.status = 'publishing'
        publish_status.save()

        logger.info(f"[PUBLISH_ATTEMPT] Post {post_id} → {account.platform}/{account.name} | Media: {post.media_urls}")

        result = service.publish_post(
            access_token=account.access_token,
            account_id=account.platform_account_id,
            content=post.content,
            media_urls=post.media_urls if post.media_urls else None,
            media_type=post.media_type,
            link_url=post.link_url,
        )

        if result.success:
            logger.info(f"[PUBLISH_SUCCESS] Post {post_id} → {account.name} | Platform post ID: {result.platform_post_id} | URL: {result.platform_post_url}")
            publish_status.status = 'published'
            publish_status.platform_post_id = result.platform_post_id
            publish_status.platform_post_url = result.platform_post_url
            publish_status.published_at = timezone.now()
            success_count += 1
        else:
            logger.error(f"[PUBLISH_FAILED] Post {post_id} → {account.name} | Error: {result.error_message}")
            publish_status.status = 'failed'
            publish_status.error_message = result.error_message
            publish_status.retry_count += 1
            fail_count += 1

        publish_status.save()
        results.append({
            'account': account.name,
            'platform': account.platform,
            'success': result.success,
            'post_url': result.platform_post_url,
            'error': result.error_message,
        })

    # Update post status
    if fail_count == 0:
        post.status = 'published'
        post.published_at = timezone.now()
    elif success_count > 0:
        post.status = 'partial'
    else:
        post.status = 'failed'

    post.save()

    response_data = {
        'success': fail_count == 0,
        'total': success_count + fail_count,
        'success_count': success_count,
        'fail_count': fail_count,
        'results': results,
    }

    # Return appropriate HTTP status
    if fail_count == 0:
        return response_data  # 200 OK
    elif success_count > 0:
        return 207, response_data  # 207 Multi-Status (partial success)
    else:
        return 400, response_data  # 400 Bad Request (all failed)


@router.post("/validate", auth=AuthBearer(), response=ValidationResultSchema)
def validate_content(
    request,
    platform: str = Form(...),
    content: str = Form(...),
    media_type: str = Form('none')
):
    """Validate content for a specific platform"""
    try:
        service = get_platform_service(platform)
    except ValueError as e:
        raise Http404(str(e))

    return service.validate_content(content, media_type)


# ===========================================
# Test Endpoints (No Auth - Development Only)
# ===========================================

@router.get("/accounts-test", response=List[SocialAccountSchema])
def list_accounts_test(request, platform: Optional[str] = None):
    """List all social accounts (TEST - no auth)"""
    queryset = SocialAccount.objects.filter(is_active=True)

    if platform:
        queryset = queryset.filter(platform=platform)

    return queryset.order_by('platform', 'name')
