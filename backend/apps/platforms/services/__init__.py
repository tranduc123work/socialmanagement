from .base import BasePlatformService
from .facebook import FacebookService

__all__ = ['BasePlatformService', 'FacebookService', 'get_platform_service']


def get_platform_service(platform: str):
    """
    Factory function to get the appropriate service for a platform
    """
    services = {
        'facebook': FacebookService,
        # Add more platforms here:
        # 'instagram': InstagramService,
        # 'zalo': ZaloService,
        # 'tiktok': TikTokService,
    }

    service_class = services.get(platform)
    if not service_class:
        raise ValueError(f"Unsupported platform: {platform}")

    return service_class()
