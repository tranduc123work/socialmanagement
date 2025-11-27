"""
Main Django Ninja API instance
"""
from ninja import NinjaAPI
from ninja.security import HttpBearer
from django.http import JsonResponse
from api.exceptions import custom_exception_handler

# JWT Bearer Authentication
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        from apps.auth.services import AuthService
        try:
            user = AuthService.verify_token(token)
            return user
        except Exception:
            return None

# Create API instance
api = NinjaAPI(
    title="Facebook Manager API",
    version="1.0.0",
    description="API for managing Facebook posts, media, and analytics",
    docs_url="/docs",
)

# Register exception handler
api.exception_handler(Exception)(custom_exception_handler)

# Health check endpoint
@api.get("/health", tags=["System"])
def health_check(request):
    return {"status": "healthy", "message": "Facebook Manager API is running"}

# Register routers
from api.router import register_routers
register_routers(api)
