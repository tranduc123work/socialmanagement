from celery import shared_task
from django.utils import timezone


@shared_task
def publish_scheduled_post(post_id):
    """Publish a scheduled post"""
    from apps.posts.models import Post
    from apps.posts.services import PostService

    try:
        post = Post.objects.get(id=post_id)
        if post.status == 'scheduled':
            PostService.publish_post(post)
            return f"Published post {post_id}"
    except Exception as e:
        return f"Error publishing post {post_id}: {str(e)}"


@shared_task
def check_scheduled_posts():
    """Check and publish posts that are due"""
    from apps.posts.models import Post

    posts = Post.objects.filter(
        status='scheduled',
        scheduled_at__lte=timezone.now()
    )

    for post in posts:
        publish_scheduled_post.delay(post.id)

    return f"Checked {posts.count()} posts"
