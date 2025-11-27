"""
API Router Registration
"""

def register_routers(api):
    """Register all API routers"""

    # Auth endpoints
    from apps.auth.api import router as auth_router
    api.add_router("/auth/", auth_router, tags=["Authentication"])

    # Facebook API endpoints
    from apps.facebook_api.api import router as facebook_router
    api.add_router("/facebook/", facebook_router, tags=["Facebook API"])

    # AI Content Generation endpoints
    from apps.ai.api import router as ai_router
    api.add_router("/ai/", ai_router, tags=["AI Content Generation"])

    # Posts endpoints
    from apps.posts.api import router as posts_router
    api.add_router("/posts/", posts_router, tags=["Posts"])

    # Media endpoints
    from apps.media.api import router as media_router
    api.add_router("/media/", media_router, tags=["Media"])

    # Pages endpoints
    from apps.pages.api import router as pages_router
    api.add_router("/pages/", pages_router, tags=["Pages"])

    # Platforms endpoints (Multi-platform social media)
    from apps.platforms.api import router as platforms_router
    api.add_router("/platforms/", platforms_router, tags=["Platforms"])

    # Analytics endpoints
    from apps.analytics.api import router as analytics_router
    api.add_router("/analytics/", analytics_router, tags=["Analytics"])

    # Logs endpoints
    from apps.logs.api import router as logs_router
    api.add_router("/logs/", logs_router, tags=["Logs"])
