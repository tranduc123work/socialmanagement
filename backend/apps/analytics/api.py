from ninja import Router
from api.dependencies import AuthBearer
from .services import AnalyticsService

router = Router()


@router.get("/overview", auth=AuthBearer())
def get_overview(request):
    stats = AnalyticsService.get_dashboard_stats(request.auth)
    return stats


@router.get("/post/{post_id}", auth=AuthBearer())
def get_post_insights(request, post_id: str):
    insights = AnalyticsService.get_post_insights(request.auth, post_id)
    return insights


@router.get("/facebook", auth=AuthBearer())
def get_facebook_stats(request):
    """Get Facebook pages statistics with insights"""
    stats = AnalyticsService.get_facebook_stats(request.auth)
    return stats


@router.get("/facebook/page/{page_id}", auth=AuthBearer())
def get_facebook_page_stats(request, page_id: str):
    """Get detailed statistics for a specific Facebook page"""
    stats = AnalyticsService.get_facebook_page_stats(request.auth, page_id)
    return stats
