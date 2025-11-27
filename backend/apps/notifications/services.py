from django.core.mail import send_mail
from django.conf import settings
import requests


class NotificationService:
    @staticmethod
    def send_email(subject, message, recipient):
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [recipient],
            fail_silently=False,
        )

    @staticmethod
    def send_telegram(message):
        if not settings.TELEGRAM_BOT_TOKEN:
            return

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message
        }
        requests.post(url, data=data)

    @staticmethod
    def notify_token_expiry(user):
        message = f"Your Facebook token will expire soon. Please reconnect your account."
        NotificationService.send_email("Facebook Token Expiring", message, user.email)
        NotificationService.send_telegram(f"Token expiry warning for {user.email}")

    @staticmethod
    def notify_post_failed(user, post):
        message = f"Failed to publish post: {post.title}\nError: {post.error_message}"
        NotificationService.send_email("Post Publishing Failed", message, user.email)
