from ninja import Router
from typing import List
from api.dependencies import AuthBearer
from .models import FacebookPage
from .services import PageService
from .schemas import FacebookPageSchema

router = Router()


@router.get("/", response=List[FacebookPageSchema], auth=AuthBearer())
def list_pages(request):
    pages = FacebookPage.objects.filter(user=request.auth, is_active=True)
    return pages


@router.post("/sync", auth=AuthBearer())
def sync_pages(request):
    pages = PageService.sync_pages_from_facebook(request.auth)
    return {"message": f"Synced {pages.count()} pages", "success": True}


@router.get("/{page_id}", response=FacebookPageSchema, auth=AuthBearer())
def get_page(request, page_id: int):
    page = FacebookPage.objects.get(id=page_id, user=request.auth)
    return page
