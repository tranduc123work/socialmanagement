"""
Authentication Business Logic
"""
import jwt
import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User, RefreshToken
from api.exceptions import ValidationError, PermissionDenied

# Setup logger for authentication
logger = logging.getLogger('auth')


class AuthService:
    """Authentication Service"""

    @staticmethod
    def create_tokens(user: User) -> dict:
        """Create JWT access and refresh tokens"""

        # Create access token
        access_token_payload = {
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        access_token = jwt.encode(access_token_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        # Create refresh token
        refresh_token_payload = {
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        refresh_token = jwt.encode(refresh_token_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        # Save refresh token to database
        RefreshToken.objects.create(
            user=user,
            token=refresh_token,
            expires_at=timezone.now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    @staticmethod
    def verify_token(token: str) -> User:
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get('user_id')
            if not user_id:
                raise ValidationError("Invalid token")

            user = User.objects.get(id=user_id)
            return user
        except jwt.ExpiredSignatureError:
            raise ValidationError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValidationError("Invalid token")
        except User.DoesNotExist:
            raise ValidationError("User not found")

    @staticmethod
    def login(email: str, password: str) -> dict:
        """Login with email and password"""
        # Find user by email first
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"[LOGIN_FAILED] Email khong ton tai: {email}")
            raise ValidationError("Email không tồn tại trong hệ thống")

        # Authenticate using the user's username
        user = authenticate(username=user_obj.username, password=password)
        if not user:
            logger.warning(f"[LOGIN_FAILED] Sai mat khau cho email: {email}")
            raise ValidationError("Mật khẩu không chính xác")

        logger.info(f"[LOGIN_SUCCESS] User dang nhap thanh cong: {email} (ID: {user.id})")

        tokens = AuthService.create_tokens(user)
        return {
            'user': user,
            'tokens': tokens
        }

    @staticmethod
    def register(email: str, username: str, password: str, confirm_password: str) -> dict:
        """Register new user"""
        if password != confirm_password:
            logger.warning(
                f"[REGISTER_FAILED] Mật khẩu không khớp cho email: {email}"
            )
            raise ValidationError("Mật khẩu xác nhận không khớp")

        if User.objects.filter(email=email).exists():
            logger.warning(
                f"[REGISTER_FAILED] Email đã tồn tại: {email}"
            )
            raise ValidationError("Email đã được sử dụng")

        if User.objects.filter(username=username).exists():
            logger.warning(
                f"[REGISTER_FAILED] Username đã tồn tại: {username}"
            )
            raise ValidationError("Tên người dùng đã được sử dụng")

        user = User.objects.create_user(
            email=email,
            username=username,
            password=password
        )

        logger.info(
            f"[REGISTER_SUCCESS] User đăng ký thành công: {email} (ID: {user.id})"
        )

        tokens = AuthService.create_tokens(user)
        return {
            'user': user,
            'tokens': tokens
        }

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

            if payload.get('type') != 'refresh':
                raise ValidationError("Invalid token type")

            # Check if token exists and is not revoked
            token_obj = RefreshToken.objects.filter(token=refresh_token, is_revoked=False).first()
            if not token_obj or not token_obj.is_valid():
                raise ValidationError("Refresh token is invalid or expired")

            user = User.objects.get(id=payload['user_id'])
            tokens = AuthService.create_tokens(user)

            # Revoke old refresh token
            token_obj.is_revoked = True
            token_obj.save()

            return tokens
        except jwt.ExpiredSignatureError:
            raise ValidationError("Refresh token has expired")
        except jwt.InvalidTokenError:
            raise ValidationError("Invalid refresh token")

    @staticmethod
    def facebook_login(facebook_access_token: str) -> dict:
        """Login/Register with Facebook"""

        # Verify Facebook token and get user info
        try:
            response = requests.get(
                f"{settings.FACEBOOK_GRAPH_API_URL}/me",
                params={
                    'fields': 'id,email,name,picture',
                    'access_token': facebook_access_token
                }
            )
            response.raise_for_status()
            fb_data = response.json()
        except Exception as e:
            raise ValidationError(f"Failed to verify Facebook token: {str(e)}")

        # Get or create user
        facebook_user_id = fb_data.get('id')
        email = fb_data.get('email')
        name = fb_data.get('name', '')

        if not email:
            raise ValidationError("Facebook account must have an email")

        user, created = User.objects.get_or_create(
            facebook_user_id=facebook_user_id,
            defaults={
                'email': email,
                'username': email.split('@')[0],
                'first_name': name.split()[0] if name else '',
                'last_name': ' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
                'avatar': fb_data.get('picture', {}).get('data', {}).get('url'),
                'is_facebook_connected': True,
            }
        )

        # Update Facebook token
        user.facebook_access_token = facebook_access_token
        user.facebook_token_expires_at = timezone.now() + timedelta(days=60)  # Facebook tokens expire in 60 days
        user.is_facebook_connected = True
        user.save()

        tokens = AuthService.create_tokens(user)
        return {
            'user': user,
            'tokens': tokens
        }

    @staticmethod
    def get_facebook_token_status(user: User) -> dict:
        """Get Facebook token status"""
        if not user.is_facebook_connected:
            return {
                'is_valid': False,
                'needs_refresh': True,
                'expires_at': None,
                'days_until_expiry': None
            }

        is_valid = user.is_token_valid()
        days_until_expiry = None

        if user.facebook_token_expires_at:
            days_until_expiry = (user.facebook_token_expires_at - timezone.now()).days

        return {
            'is_valid': is_valid,
            'expires_at': user.facebook_token_expires_at,
            'days_until_expiry': days_until_expiry,
            'needs_refresh': not is_valid or (days_until_expiry and days_until_expiry < 7)
        }
