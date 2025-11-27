from ninja import Router, Form
from api.dependencies import AuthBearer

router = Router()


@router.get("/", auth=AuthBearer())
def list_posts(request):
    """Get all posts for the authenticated user"""
    from .models import Post
    posts = Post.objects.filter(user=request.auth).order_by('-created_at')[:50]
    return [{"id": p.id, "content": p.content, "status": p.status} for p in posts]


@router.post("/", auth=AuthBearer())
def create_post(request):
    """Create a new post"""
    return {"message": "Post created"}


@router.get("/{post_id}", auth=AuthBearer())
def get_post(request, post_id: int):
    """Get a specific post"""
    from .models import Post
    post = Post.objects.get(id=post_id, user=request.auth)
    return {"id": post.id, "content": post.content, "status": post.status}


@router.delete("/{post_id}", auth=AuthBearer())
def delete_post(request, post_id: int):
    """Delete a post"""
    from .models import Post
    Post.objects.filter(id=post_id, user=request.auth).delete()
    return {"message": "Post deleted"}
