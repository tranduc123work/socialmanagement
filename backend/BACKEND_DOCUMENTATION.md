# 📚 Facebook Manager Backend - Documentation Toàn Bộ

> Documentation chi tiết về cấu trúc, code và hoạt động của backend

---

## 📁 Cấu Trúc Thư Mục Tổng Quan

```
backend/
├── config/                      # Django configuration
│   ├── settings/               # Settings cho từng môi trường
│   │   ├── __init__.py
│   │   ├── base.py            # Cài đặt chung
│   │   ├── development.py     # Cài đặt dev
│   │   ├── production.py      # Cài đặt prod
│   │   └── testing.py         # Cài đặt test
│   ├── __init__.py            # Import Celery app
│   ├── celery.py              # Celery configuration
│   ├── urls.py                # URL routing chính
│   ├── wsgi.py                # WSGI application
│   └── asgi.py                # ASGI application
│
├── api/                        # API Core - Django Ninja
│   ├── __init__.py
│   ├── main.py                # API instance chính
│   ├── router.py              # Đăng ký tất cả routers
│   ├── exceptions.py          # Global exception handlers
│   ├── dependencies.py        # Auth dependencies
│   └── middleware.py          # Custom middlewares
│
├── apps/                       # Application modules
│   ├── __init__.py
│   │
│   ├── auth/                  # Authentication Module
│   │   ├── __init__.py
│   │   ├── apps.py           # App config
│   │   ├── models.py         # User, RefreshToken models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── services.py       # Business logic
│   │   ├── api.py            # API endpoints
│   │   ├── admin.py          # Django admin
│   │   ├── permissions.py    # Permission checks
│   │   └── tests/
│   │
│   ├── facebook_api/         # Facebook Graph API Module
│   │   ├── models.py         # FacebookAPILog
│   │   ├── services.py       # Graph API wrapper
│   │   ├── api.py            # Endpoints
│   │   └── admin.py
│   │
│   ├── posts/                # Posts Management Module
│   │   ├── models.py         # Post, PostVersion
│   │   ├── schemas.py        # Request/Response schemas
│   │   ├── services.py       # PostService, AIContentService
│   │   ├── api.py            # CRUD + AI endpoints
│   │   └── admin.py
│   │
│   ├── pages/                # Facebook Pages Module
│   │   ├── models.py         # FacebookPage
│   │   ├── services.py       # Sync pages
│   │   ├── api.py            # Endpoints
│   │   └── admin.py
│   │
│   ├── media/                # Media Library Module
│   │   ├── models.py         # Media, MediaFolder, MediaTag
│   │   ├── api.py            # Upload, list
│   │   └── admin.py
│   │
│   ├── scheduler/            # Task Scheduling Module
│   │   ├── tasks.py          # Celery tasks
│   │   └── apps.py
│   │
│   ├── analytics/            # Analytics Module
│   │   ├── services.py       # Facebook Insights
│   │   └── api.py            # Stats endpoints
│   │
│   ├── logs/                 # Logging Module
│   │   ├── models.py         # APILog
│   │   ├── api.py            # View logs
│   │   └── admin.py
│   │
│   └── notifications/        # Notifications Module
│       └── services.py       # Email, Telegram
│
├── tests/                     # Integration tests
│   ├── __init__.py
│   ├── conftest.py
│   └── test_integration.py
│
├── requirements.txt           # Python dependencies
├── requirements-dev.txt       # Dev dependencies
├── .env.example              # Environment template
├── .gitignore
├── manage.py                 # Django CLI
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── QUICK_SETUP.py           # Script tạo tất cả files
└── README.md

```

---

## 🔧 CONFIG - Django Configuration

### `config/settings/base.py` - Cài Đặt Chung

**Mục đích**: Cài đặt Django cơ bản cho tất cả môi trường

**Các phần quan trọng**:

#### 1. Installed Apps
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ... Django apps

    # Third party
    'corsheaders',              # CORS support
    'django_celery_beat',       # Celery scheduling

    # Local apps
    'apps.auth',                # Custom auth
    'apps.facebook_api',        # Facebook integration
    'apps.posts',               # Post management
    'apps.media',               # Media library
    'apps.pages',               # Facebook pages
    'apps.scheduler',           # Task scheduling
    'apps.analytics',           # Analytics
    'apps.logs',                # Logging
    'apps.notifications',       # Notifications
]
```

**Giải thích**:
- Đăng ký tất cả Django apps cần thiết
- Third party apps: CORS, Celery Beat
- Local apps: Các module của dự án

#### 2. Database Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='facebook_manager'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
```

**Giải thích**:
- Sử dụng PostgreSQL
- Lấy config từ environment variables (.env)
- Có giá trị mặc định cho development

#### 3. Custom User Model
```python
AUTH_USER_MODEL = 'custom_auth.User'
```

**Giải thích**: Sử dụng custom User model từ `apps.auth`

#### 4. Redis & Caching
```python
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
    }
}
```

**Giải thích**:
- Redis dùng cho caching và Celery
- Tăng performance

#### 5. Celery Configuration
```python
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

**Giải thích**:
- Celery dùng Redis làm message broker
- Lưu kết quả task vào Redis
- Dùng JSON để serialize data
- Beat scheduler lưu vào database

#### 6. Facebook API Config
```python
FACEBOOK_APP_ID = config('FACEBOOK_APP_ID', default='')
FACEBOOK_APP_SECRET = config('FACEBOOK_APP_SECRET', default='')
FACEBOOK_GRAPH_API_VERSION = config('FACEBOOK_GRAPH_API_VERSION', default='v19.0')
FACEBOOK_GRAPH_API_URL = f'https://graph.facebook.com/{FACEBOOK_GRAPH_API_VERSION}'
```

**Giải thích**: Cấu hình để gọi Facebook Graph API

#### 7. AI Services Config
```python
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
```

**Giải thích**: API keys cho các AI services

#### 8. JWT Config
```python
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=SECRET_KEY)
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = config('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=30, cast=int)
JWT_REFRESH_TOKEN_EXPIRE_DAYS = config('JWT_REFRESH_TOKEN_EXPIRE_DAYS', default=7, cast=int)
```

**Giải thích**: Cấu hình JWT authentication

#### 9. CORS Config
```python
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)
CORS_ALLOW_CREDENTIALS = True
```

**Giải thích**: Cho phép frontend (React) gọi API

---

### `config/settings/development.py` - Development Settings

```python
from .base import *

DEBUG = True

INSTALLED_APPS += [
    'django_extensions',  # Extra dev tools
]

CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins in dev
```

**Giải thích**:
- DEBUG mode bật
- Allow all CORS origins để dễ dev
- Thêm dev tools

---

### `config/celery.py` - Celery Configuration

```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('facebook_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat Schedule - Chạy định kỳ
app.conf.beat_schedule = {
    'check-scheduled-posts-every-minute': {
        'task': 'apps.scheduler.tasks.check_scheduled_posts',
        'schedule': crontab(minute='*/1'),  # Mỗi phút
    },
}
```

**Giải thích**:
- Tạo Celery app instance
- Auto-discover tasks từ tất cả apps
- Beat schedule: Task chạy định kỳ
- `check_scheduled_posts`: Chạy mỗi phút để check posts cần publish

---

### `config/urls.py` - URL Routing

```python
from django.contrib import admin
from django.urls import path
from api.main import api

urlpatterns = [
    path('admin/', admin.site.urls),      # Django admin
    path('api/', api.urls),               # Tất cả API endpoints
]
```

**Giải thích**:
- `/admin/`: Django admin panel
- `/api/`: Tất cả API endpoints (Django Ninja)

---

## 🔌 API CORE - Django Ninja

### `api/main.py` - API Instance Chính

```python
from ninja import NinjaAPI
from ninja.security import HttpBearer

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        from apps.auth.services import AuthService
        try:
            user = AuthService.verify_token(token)
            return user
        except Exception:
            return None

# Tạo API instance
api = NinjaAPI(
    title="Facebook Manager API",
    version="1.0.0",
    description="API for managing Facebook posts",
    docs_url="/docs",  # Auto-generated docs
)

# Health check
@api.get("/health", tags=["System"])
def health_check(request):
    return {"status": "healthy"}

# Register routers
from api.router import register_routers
register_routers(api)
```

**Giải thích**:
- `AuthBearer`: JWT authentication middleware
- `api`: Main API instance
- Auto docs tại `/api/docs`
- Health check endpoint
- Register tất cả routers

---

### `api/router.py` - Router Registration

```python
def register_routers(api):
    """Đăng ký tất cả routers"""

    from apps.auth.api import router as auth_router
    api.add_router("/auth/", auth_router, tags=["Authentication"])

    from apps.posts.api import router as posts_router
    api.add_router("/posts/", posts_router, tags=["Posts"])

    from apps.pages.api import router as pages_router
    api.add_router("/pages/", pages_router, tags=["Pages"])

    # ... other routers
```

**Giải thích**:
- Import router từ mỗi module
- Add vào main API với prefix và tags
- Tags giúp organize docs

---

### `api/exceptions.py` - Exception Handlers

```python
def custom_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"API Error: {str(exc)}")

    # Xác định status code
    if hasattr(exc, 'status_code'):
        status_code = exc.status_code
    elif isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, PermissionDenied):
        status_code = 403
    else:
        status_code = 500

    # Response
    error_response = {
        "error": True,
        "message": str(exc),
        "type": exc.__class__.__name__,
    }

    return JsonResponse(error_response, status=status_code)

# Custom Exceptions
class ValidationError(Exception):
    status_code = 400

class PermissionDenied(Exception):
    status_code = 403

class FacebookAPIError(Exception):
    status_code = 502
```

**Giải thích**:
- Bắt tất cả exceptions
- Trả về JSON response thống nhất
- Custom exception classes

---

### `api/dependencies.py` - Dependencies

```python
class AuthBearer(HttpBearer):
    """JWT Bearer Authentication"""

    def authenticate(self, request: HttpRequest, token: str):
        from apps.auth.services import AuthService
        try:
            user = AuthService.verify_token(token)
            return user
        except Exception:
            return None

def require_auth(request):
    """Require authentication"""
    user = get_current_user(request)
    if not user:
        raise PermissionDenied("Authentication required")
    return user
```

**Giải thích**:
- AuthBearer: Verify JWT token
- require_auth: Dependency cho protected endpoints
- Throw exception nếu không auth

---

## 👤 AUTH MODULE - Authentication

### `apps/auth/models.py` - User Models

#### User Model
```python
class User(AbstractUser):
    """Custom User Model với Facebook integration"""

    # Basic fields (inherited from AbstractUser)
    # - username
    # - email
    # - password
    # - first_name, last_name
    # - is_active, is_staff, is_superuser

    # Facebook fields
    facebook_user_id = models.CharField(max_length=100, unique=True, null=True)
    facebook_access_token = models.TextField(blank=True, null=True)
    facebook_token_expires_at = models.DateTimeField(blank=True, null=True)
    is_facebook_connected = models.BooleanField(default=False)

    # Extra fields
    avatar = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_token_valid(self):
        """Check if Facebook token còn hạn"""
        if not self.facebook_token_expires_at:
            return False
        return self.facebook_token_expires_at > timezone.now()
```

**Giải thích**:
- Extend AbstractUser của Django
- Thêm Facebook integration fields
- Method check token expiry

#### RefreshToken Model
```python
class RefreshToken(models.Model):
    """JWT Refresh Token"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)

    def is_valid(self):
        """Check if token valid"""
        return not self.is_revoked and self.expires_at > timezone.now()
```

**Giải thích**:
- Lưu refresh tokens
- Track revoked tokens (logout)
- Check expiry

---

### `apps/auth/services.py` - Business Logic

#### AuthService Class

**1. Create Tokens**
```python
@staticmethod
def create_tokens(user: User) -> dict:
    """Tạo JWT access & refresh tokens"""

    # Access token (expires in 30 minutes)
    access_token_payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(minutes=30),
        'type': 'access'
    }
    access_token = jwt.encode(access_token_payload, SECRET_KEY, algorithm='HS256')

    # Refresh token (expires in 7 days)
    refresh_token_payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(days=7),
        'type': 'refresh'
    }
    refresh_token = jwt.encode(refresh_token_payload, SECRET_KEY, algorithm='HS256')

    # Save refresh token to DB
    RefreshToken.objects.create(
        user=user,
        token=refresh_token,
        expires_at=timezone.now() + timedelta(days=7)
    )

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 1800  # 30 minutes in seconds
    }
```

**Giải thích**:
- Access token: Dùng cho API calls, expires nhanh (30 min)
- Refresh token: Dùng để lấy access token mới, expires lâu (7 days)
- Save refresh token vào DB để có thể revoke

**2. Verify Token**
```python
@staticmethod
def verify_token(token: str) -> User:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        user = User.objects.get(id=user_id)
        return user
    except jwt.ExpiredSignatureError:
        raise ValidationError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValidationError("Invalid token")
```

**Giải thích**:
- Decode JWT token
- Check expiry
- Return user object

**3. Facebook Login**
```python
@staticmethod
def facebook_login(facebook_access_token: str) -> dict:
    """Login/Register with Facebook"""

    # 1. Verify token với Facebook
    response = requests.get(
        f"{FACEBOOK_GRAPH_API_URL}/me",
        params={
            'fields': 'id,email,name,picture',
            'access_token': facebook_access_token
        }
    )
    fb_data = response.json()

    # 2. Get or create user
    facebook_user_id = fb_data.get('id')
    email = fb_data.get('email')

    user, created = User.objects.get_or_create(
        facebook_user_id=facebook_user_id,
        defaults={
            'email': email,
            'username': email.split('@')[0],
            'is_facebook_connected': True,
        }
    )

    # 3. Update Facebook token
    user.facebook_access_token = facebook_access_token
    user.facebook_token_expires_at = timezone.now() + timedelta(days=60)
    user.save()

    # 4. Create JWT tokens
    tokens = AuthService.create_tokens(user)

    return {'user': user, 'tokens': tokens}
```

**Giải thích**:
- Verify Facebook token với Graph API
- Get hoặc create user
- Save Facebook token
- Return JWT tokens cho app

---

### `apps/auth/api.py` - API Endpoints

```python
router = Router()

@router.post("/login", response=AuthResponseSchema)
def login(request, data: LoginSchema):
    """Login with email/password"""
    result = AuthService.login(data.email, data.password)
    return result

@router.post("/register", response=AuthResponseSchema)
def register(request, data: RegisterSchema):
    """Register new user"""
    result = AuthService.register(...)
    return result

@router.post("/facebook/login", response=AuthResponseSchema)
def facebook_login(request, data: FacebookLoginSchema):
    """Login with Facebook"""
    result = AuthService.facebook_login(data.facebook_access_token)
    return result

@router.get("/me", response=UserSchema, auth=AuthBearer())
def get_current_user(request):
    """Get current user info"""
    return request.auth  # AuthBearer đã verify token

@router.get("/status", response=FacebookTokenStatusSchema, auth=AuthBearer())
def get_token_status(request):
    """Check Facebook token status"""
    status = AuthService.get_facebook_token_status(request.auth)
    return status
```

**Giải thích**:
- Each endpoint map to một service method
- `auth=AuthBearer()`: Endpoint cần authentication
- `request.auth`: User object sau khi auth

---

## 📘 POSTS MODULE - Post Management

### `apps/posts/models.py` - Post Models

```python
class Post(models.Model):
    """Post Model"""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    # Who created
    created_by = models.ForeignKey('custom_auth.User', on_delete=models.CASCADE)

    # Content
    content = models.TextField()
    original_content = models.TextField(blank=True)  # Before AI rewrite

    # Media
    media_urls = models.JSONField(default=list)
    link_url = models.URLField(blank=True, null=True)

    # Hashtags & AI
    hashtags = models.JSONField(default=list)
    ai_generated = models.BooleanField(default=False)
    ai_provider = models.CharField(max_length=50, blank=True)  # openai/gemini/claude

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # Facebook
    facebook_post_id = models.CharField(max_length=100, blank=True)
    facebook_pages = models.ManyToManyField('pages.FacebookPage')

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
```

**Giải thích**:
- `content`: Nội dung post hiện tại (có thể đã AI rewrite)
- `original_content`: Nội dung gốc trước khi AI rewrite
- `status`: Draft → Scheduled → Published/Failed
- `facebook_pages`: ManyToMany - 1 post có thể đăng lên nhiều pages
- `retry_count`: Số lần retry nếu failed

---

### `apps/posts/services.py` - Business Logic

#### AIContentService - AI Features

**1. Rewrite với OpenAI**
```python
@staticmethod
def rewrite_with_openai(content: str, tone: str = 'engaging') -> str:
    """Rewrite content using GPT-4"""

    openai.api_key = settings.OPENAI_API_KEY

    prompt = f"Rewrite this post in a {tone} tone: {content}"

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a social media expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )

    return response.choices[0].message.content.strip()
```

**Giải thích**:
- Gọi OpenAI GPT-4 API
- System prompt: Define AI's role
- User prompt: Nội dung cần rewrite + tone
- Temperature 0.7: Balanced creativity

**2. Generate Hashtags**
```python
@staticmethod
def generate_hashtags(content: str, count: int = 10) -> list:
    """Generate hashtags using AI"""

    prompt = f"Generate {count} hashtags for: {content}"

    response = openai.ChatCompletion.create(...)

    hashtags_text = response.choices[0].message.content
    hashtags = [tag.strip() for tag in hashtags_text.split('\n')
                if tag.startswith('#')]

    return hashtags[:count]
```

**Giải thích**:
- Generate relevant hashtags
- Parse response to list
- Return top N hashtags

**3. Spin Content**
```python
@staticmethod
def spin_content(content: str, variations: int = 3) -> list:
    """Create content variations"""

    prompt = f"Create {variations} variations of: {content}"

    response = openai.ChatCompletion.create(...)

    variations_text = response.choices[0].message.content
    variations_list = [v.strip() for v in variations_text.split('\n\n')]

    return variations_list
```

**Giải thích**:
- Tạo nhiều phiên bản content
- Cùng ý nghĩa nhưng khác wording
- Useful để test A/B

#### PostService - Post Management

**1. Publish Post**
```python
@staticmethod
def publish_post(post: Post, page_ids: list = None) -> Post:
    """Publish post to Facebook"""

    user = post.created_by
    fb_api = FacebookAPIService(user.facebook_access_token, user)

    pages = post.facebook_pages.all()
    if page_ids:
        pages = pages.filter(id__in=page_ids)

    for page in pages:
        try:
            # Publish to Facebook
            result = fb_api.publish_post(
                page_id=page.facebook_page_id,
                message=post.content,
                link=post.link_url
            )

            post.facebook_post_id = result.get('id')
            post.status = 'published'
            post.published_at = timezone.now()

        except Exception as e:
            post.status = 'failed'
            post.error_message = str(e)
            post.retry_count += 1

    post.save()
    return post
```

**Giải thích**:
- Get Facebook API service
- Loop qua các pages
- Gọi Facebook API để publish
- Update post status
- Catch errors và retry

**2. Schedule Post**
```python
@staticmethod
def schedule_post(post: Post, scheduled_at, page_ids: list) -> Post:
    """Schedule post for later"""

    post.scheduled_at = scheduled_at
    post.status = 'scheduled'
    post.save()

    # Tạo Celery task
    from apps.scheduler.tasks import publish_scheduled_post
    publish_scheduled_post.apply_async(
        (post.id,),
        eta=scheduled_at  # Execute at this time
    )

    return post
```

**Giải thích**:
- Save scheduled time
- Create Celery task với ETA (estimated time of arrival)
- Task sẽ tự động chạy vào lúc đó

---

### `apps/posts/api.py` - API Endpoints

```python
@router.post("/", response=PostSchema, auth=AuthBearer())
def create_post(request, data: PostCreateSchema):
    """Create new post"""
    post = PostService.create_post(request.auth, data.dict())
    return post

@router.post("/{post_id}/publish", auth=AuthBearer())
def publish_post(request, post_id: int, data: PostPublishSchema):
    """Publish immediately"""
    post = Post.objects.get(id=post_id, created_by=request.auth)
    post = PostService.publish_post(post, data.page_ids)
    return post

@router.post("/{post_id}/schedule", auth=AuthBearer())
def schedule_post(request, post_id: int, data: PostScheduleSchema):
    """Schedule for later"""
    post = Post.objects.get(id=post_id)
    post = PostService.schedule_post(post, data.scheduled_at, data.page_ids)
    return post

@router.post("/ai/rewrite", auth=AuthBearer())
def ai_rewrite(request, data: AIRewriteSchema):
    """AI rewrite content"""
    rewritten = AIContentService.rewrite_content(
        data.content,
        provider=data.provider,
        tone=data.tone
    )
    return {"original": data.content, "rewritten": rewritten}

@router.post("/ai/hashtags", auth=AuthBearer())
def generate_hashtags(request, data: AIHashtagSchema):
    """Generate hashtags"""
    hashtags = AIContentService.generate_hashtags(data.content, data.count)
    return {"hashtags": hashtags}
```

**Giải thích**:
- CRUD endpoints cho posts
- AI endpoints riêng biệt
- Mỗi endpoint validate với schema
- Return typed response

---

## 📄 PAGES MODULE - Facebook Pages

### `apps/pages/models.py`

```python
class FacebookPage(models.Model):
    """Facebook Page Model"""

    user = models.ForeignKey('custom_auth.User', on_delete=models.CASCADE)
    facebook_page_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    access_token = models.TextField()  # Page access token
    picture_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
```

**Giải thích**:
- Lưu pages của user
- `access_token`: Page-specific token (khác user token)
- Used để post lên page đó

---

### `apps/pages/services.py`

```python
class PageService:
    @staticmethod
    def sync_pages_from_facebook(user):
        """Sync pages from Facebook"""

        fb_api = FacebookAPIService(user.facebook_access_token, user)

        # Get pages từ Facebook
        pages_data = fb_api.get_pages()

        # Update or create trong DB
        for page_data in pages_data.get('data', []):
            FacebookPage.objects.update_or_create(
                facebook_page_id=page_data['id'],
                user=user,
                defaults={
                    'name': page_data['name'],
                    'category': page_data.get('category', ''),
                    'access_token': page_data['access_token'],  # Important!
                    'picture_url': page_data.get('picture', {}).get('data', {}).get('url')
                }
            )

        return FacebookPage.objects.filter(user=user, is_active=True)
```

**Giải thích**:
- Gọi Facebook API lấy danh sách pages
- Save vào DB với update_or_create
- Lưu page access token để dùng sau

---

## 🔌 FACEBOOK API MODULE

### `apps/facebook_api/services.py`

```python
class FacebookAPIService:
    """Facebook Graph API Wrapper"""

    BASE_URL = settings.FACEBOOK_GRAPH_API_URL

    def __init__(self, access_token: str, user=None):
        self.access_token = access_token
        self.user = user

    def _make_request(self, method, endpoint, params=None, data=None):
        """Make request to Facebook API"""

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params['access_token'] = self.access_token

        response = requests.request(
            method=method,
            url=url,
            params=params if method == 'GET' else None,
            data=data if method != 'GET' else None,
            timeout=30
        )

        # Log request
        if self.user:
            FacebookAPILog.objects.create(
                user=self.user,
                endpoint=endpoint,
                method=method,
                request_data=data or params,
                response_data=response.json() if response.ok else None,
                status_code=response.status_code
            )

        response.raise_for_status()
        return response.json()

    def get_pages(self):
        """Get user's pages"""
        return self.get('me/accounts', params={'fields': 'id,name,access_token,picture'})

    def publish_post(self, page_id, message, link=None):
        """Publish post to page"""
        data = {'message': message}
        if link:
            data['link'] = link

        return self.post(f"{page_id}/feed", data=data)

    def get_post_insights(self, post_id, metrics=None):
        """Get post insights"""
        metrics = metrics or ['post_impressions', 'post_engaged_users']
        return self.get(f"{post_id}/insights", params={'metric': ','.join(metrics)})
```

**Giải thích**:
- Wrapper around Facebook Graph API
- `_make_request`: Base method cho tất cả requests
- Auto log mỗi request
- Specific methods cho từng use case

---

## ⏰ SCHEDULER MODULE

### `apps/scheduler/tasks.py` - Celery Tasks

```python
from celery import shared_task

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
        return f"Error: {str(e)}"

@shared_task
def check_scheduled_posts():
    """Check and publish posts that are due"""

    from apps.posts.models import Post
    from django.utils import timezone

    # Find posts đến giờ publish
    posts = Post.objects.filter(
        status='scheduled',
        scheduled_at__lte=timezone.now()
    )

    for post in posts:
        publish_scheduled_post.delay(post.id)

    return f"Checked {posts.count()} posts"
```

**Giải thích**:
- `@shared_task`: Celery decorator
- `publish_scheduled_post`: Publish 1 post
- `check_scheduled_posts`: Check tất cả posts (chạy định kỳ)
- `.delay()`: Async task execution

**Celery Beat Schedule** (trong `config/celery.py`):
```python
app.conf.beat_schedule = {
    'check-scheduled-posts-every-minute': {
        'task': 'apps.scheduler.tasks.check_scheduled_posts',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
}
```

**Giải thích**:
- Beat: Celery scheduler
- Chạy `check_scheduled_posts` mỗi phút
- Tự động publish posts đúng giờ

---

## 📊 ANALYTICS MODULE

### `apps/analytics/services.py`

```python
class AnalyticsService:
    @staticmethod
    def get_dashboard_stats(user):
        """Get overview statistics"""

        from apps.posts.models import Post

        posts = Post.objects.filter(created_by=user)

        return {
            'total_posts': posts.count(),
            'published': posts.filter(status='published').count(),
            'scheduled': posts.filter(status='scheduled').count(),
            'draft': posts.filter(status='draft').count(),
            'failed': posts.filter(status='failed').count(),
        }

    @staticmethod
    def get_post_insights(user, post_id):
        """Get Facebook Insights for a post"""

        fb_api = FacebookAPIService(user.facebook_access_token, user)

        insights = fb_api.get_post_insights(
            post_id,
            metrics=['post_impressions', 'post_engaged_users', 'post_clicks']
        )

        return insights
```

**Giải thích**:
- Dashboard stats: Count từ database
- Post insights: Gọi Facebook Insights API
- Return metrics như impressions, engagement, clicks

---

## 📝 LOGS MODULE

### `apps/logs/models.py`

```python
class APILog(models.Model):
    """Log all API requests"""

    user = models.ForeignKey('custom_auth.User', on_delete=models.CASCADE, null=True)
    endpoint = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    request_data = models.JSONField(null=True)
    response_data = models.JSONField(null=True)
    error_message = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Giải thích**:
- Log mọi API call
- Useful để debug
- Track user activity
- Monitor errors

---

## 📧 NOTIFICATIONS MODULE

### `apps/notifications/services.py`

```python
class NotificationService:
    @staticmethod
    def send_email(subject, message, recipient):
        """Send email notification"""
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [recipient],
            fail_silently=False,
        )

    @staticmethod
    def send_telegram(message):
        """Send Telegram notification"""
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
        """Notify user about token expiry"""
        message = f"Your Facebook token will expire soon. Please reconnect."

        NotificationService.send_email("Facebook Token Expiring", message, user.email)
        NotificationService.send_telegram(f"Token expiry warning for {user.email}")

    @staticmethod
    def notify_post_failed(user, post):
        """Notify about failed post"""
        message = f"Failed to publish: {post.title}\nError: {post.error_message}"

        NotificationService.send_email("Post Failed", message, user.email)
```

**Giải thích**:
- Multiple notification channels
- Email: Django built-in
- Telegram: Via Telegram Bot API
- Called từ các services khác khi cần

---

## 🔄 Luồng Hoạt Động

### 1. User Login Flow
```
1. Frontend gọi POST /api/auth/login {email, password}
2. AuthService.login() verify credentials
3. Create JWT access + refresh tokens
4. Return tokens to frontend
5. Frontend lưu tokens vào localStorage
6. Subsequent requests include: Authorization: Bearer <access_token>
```

### 2. Facebook OAuth Flow
```
1. Frontend redirect user to Facebook login
2. Facebook returns access_token
3. Frontend gọi POST /api/auth/facebook/login {facebook_access_token}
4. AuthService.facebook_login() verify với Facebook
5. Get user info từ Facebook
6. Create/Update user trong DB
7. Create JWT tokens
8. Return to frontend
```

### 3. Create & Publish Post Flow
```
1. POST /api/posts/ {content, page_ids}
   → PostService.create_post()
   → Save to DB with status='draft'

2. (Optional) POST /api/posts/ai/rewrite {content}
   → AIContentService.rewrite_with_openai()
   → Return rewritten content

3. POST /api/posts/{id}/publish {page_ids}
   → PostService.publish_post()
   → FacebookAPIService.publish_post() cho mỗi page
   → Update status='published'
   → FacebookAPILog ghi lại request
```

### 4. Schedule Post Flow
```
1. POST /api/posts/{id}/schedule {scheduled_at, page_ids}
   → PostService.schedule_post()
   → Save scheduled_at
   → status='scheduled'
   → Create Celery task với ETA

2. Celery Beat chạy mỗi phút:
   → check_scheduled_posts task
   → Find posts với scheduled_at <= now
   → Queue publish_scheduled_post tasks

3. Celery Worker execute:
   → publish_scheduled_post(post_id)
   → PostService.publish_post()
   → Publish to Facebook
   → Update status
```

### 5. Sync Facebook Pages Flow
```
1. POST /api/pages/sync
   → PageService.sync_pages_from_facebook()
   → FacebookAPIService.get_pages()
   → Call Facebook: GET /me/accounts
   → Parse response
   → Update DB với update_or_create()
   → Return synced pages
```

---

## 🔐 Security

### Authentication Flow
```
1. Login → Nhận JWT tokens
2. Store tokens securely (httpOnly cookies or localStorage)
3. Mỗi request include: Authorization: Bearer <access_token>
4. Backend verify token với AuthBearer middleware
5. If expired → Return 401
6. Frontend refresh using refresh_token
7. POST /api/auth/refresh {refresh_token}
8. Get new access_token
```

### Permission Checks
```python
# In api.py
@router.post("/posts/{id}/delete", auth=AuthBearer())
def delete_post(request, post_id):
    post = Post.objects.get(id=post_id)

    # Permission check
    if post.created_by != request.auth and not request.auth.is_staff:
        raise PermissionDenied("You can't delete this post")

    post.delete()
```

---

## 📊 Database Schema

### Relationships
```
User (1) ----< (N) Post
User (1) ----< (N) FacebookPage
User (1) ----< (N) RefreshToken
User (1) ----< (N) Media

Post (N) ----< (N) FacebookPage  # ManyToMany
Post (1) ----< (N) PostVersion

FacebookPage (1) ----< (N) Post (through ManyToMany)

Media (N) ----< (1) MediaFolder
Media (N) ----< (N) MediaTag
```

---

## 🚀 Deployment

### Production Checklist
- [ ] `DEBUG=False`
- [ ] Strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use PostgreSQL
- [ ] Setup Redis
- [ ] Configure Celery workers
- [ ] Setup HTTPS
- [ ] Configure CORS properly
- [ ] Setup logging
- [ ] Configure Sentry (error tracking)
- [ ] Backup database
- [ ] Monitor with tools

---

## 📚 Tài Liệu Tham Khảo

- [Django Documentation](https://docs.djangoproject.com/)
- [Django Ninja](https://django-ninja.rest-framework.com/)
- [Celery](https://docs.celeryq.dev/)
- [Facebook Graph API](https://developers.facebook.com/docs/graph-api/)
- [OpenAI API](https://platform.openai.com/docs/)
- [JWT](https://jwt.io/)

---

**Documentation này giải thích chi tiết về:**
- ✅ Cấu trúc toàn bộ backend
- ✅ Mục đích mỗi file
- ✅ Code trong từng module
- ✅ Luồng hoạt động
- ✅ Database relationships
- ✅ Security & Authentication
- ✅ Deployment guidelines

Sử dụng làm tài liệu reference khi phát triển!
