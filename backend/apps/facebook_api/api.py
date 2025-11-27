from ninja import Router
from api.dependencies import AuthBearer
from .services import FacebookAPIService

router = Router()


@router.get("/me", auth=AuthBearer())
def get_me(request):
    fb_api = FacebookAPIService(request.auth.facebook_access_token, request.auth)
    return fb_api.get_me()


@router.get("/pages", auth=AuthBearer())
def get_pages(request):
    fb_api = FacebookAPIService(request.auth.facebook_access_token, request.auth)
    return fb_api.get_pages()
