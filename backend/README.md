# Facebook Manager Backend

Backend API for managing Facebook posts, media, and analytics using Django Ninja.

## 🚀 Features

- ✅ **Authentication**: JWT + Facebook OAuth
- ✅ **Post Management**: Create, schedule, publish posts with AI assistance
- ✅ **Media Library**: Upload images/videos, AI image generation
- ✅ **Analytics**: Facebook Insights integration
- ✅ **Scheduler**: Automated post publishing with Celery
- ✅ **Multi-Page Support**: Manage multiple Facebook pages

## 📋 Requirements

- Python 3.12+
- PostgreSQL 14+
- Redis 7+
- Facebook App (for API access)

## 🛠️ Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Windows
venv\\Scripts\\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
- `SECRET_KEY`: Django secret key
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL credentials
- `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`: Facebook App credentials
- `OPENAI_API_KEY`, `GEMINI_API_KEY`: AI service keys (optional)
- `REDIS_URL`: Redis connection URL

### 4. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver 8000
```

API will be available at: `http://localhost:8000/api/`
API Documentation: `http://localhost:8000/api/docs`

### 6. Run Celery Worker (for scheduled posts)

```bash
# In a separate terminal
celery -A config worker -l info

# Celery Beat (for scheduling)
celery -A config beat -l info
```

## 🐳 Docker Setup

```bash
docker-compose up -d
```

This will start:
- Django API (port 8000)
- PostgreSQL (port 5432)
- Redis (port 6379)
- Celery Worker
- Celery Beat

## 📚 API Endpoints

### Authentication
- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/register` - Register new user
- `POST /api/auth/facebook/login` - Login with Facebook
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user
- `GET /api/auth/status` - Check Facebook token status

### Posts
- `GET /api/posts/` - List all posts
- `POST /api/posts/` - Create new post
- `POST /api/posts/{id}/publish` - Publish post immediately
- `POST /api/posts/{id}/schedule` - Schedule post
- `POST /api/posts/draft` - Save as draft
- `POST /api/posts/ai/rewrite` - AI rewrite content
- `POST /api/posts/ai/hashtags` - Generate hashtags

### Media
- `POST /api/media/upload` - Upload image/video
- `GET /api/media/` - List media library
- `POST /api/media/ai/generate` - Generate image with AI
- `DELETE /api/media/{id}` - Delete media

### Pages
- `GET /api/pages/` - List Facebook pages
- `POST /api/pages/sync` - Sync pages from Facebook
- `GET /api/pages/{id}` - Get page details

### Analytics
- `GET /api/analytics/overview` - Dashboard statistics
- `GET /api/analytics/post/{id}` - Post performance
- `GET /api/analytics/trends` - Trending analysis

### Logs
- `GET /api/logs/` - API call history
- `GET /api/logs/errors` - Error logs

## 📁 Project Structure

```
backend/
├── config/              # Django configuration
│   ├── settings/       # Settings (dev, prod, test)
│   ├── urls.py         # Main URL routing
│   ├── wsgi.py         # WSGI application
│   └── asgi.py         # ASGI application
│
├── api/                # API core
│   ├── main.py         # Django Ninja API instance
│   ├── router.py       # API router registration
│   ├── middleware.py   # Custom middlewares
│   ├── exceptions.py   # Global exception handlers
│   └── dependencies.py # Common dependencies
│
├── apps/               # Application modules
│   ├── auth/           # Authentication & authorization
│   ├── facebook_api/   # Facebook Graph API wrapper
│   ├── posts/          # Post management
│   ├── media/          # Media library
│   ├── pages/          # Facebook pages
│   ├── scheduler/      # Task scheduling
│   ├── analytics/      # Analytics & insights
│   ├── logs/           # Logging
│   └── notifications/  # Email/Telegram alerts
│
└── tests/              # Integration tests
```

## 🔧 Module Details

### Auth Module
- Custom User model with Facebook integration
- JWT token authentication
- Facebook OAuth login
- Token refresh mechanism
- Permission system

### Facebook API Module
- Graph API wrapper
- Auto token refresh
- Request logging
- Error handling
- Rate limiting

### Posts Module
- Post creation with AI assistance
- Content spinning
- Hashtag generation
- AI rewrite (OpenAI, Gemini, Claude)
- Schedule publishing
- Multi-page posting
- Draft management

### Media Module
- Local file upload (on-premise storage)
- Image optimization and resizing
- User-specific directory structure
- File validation (size, type)
- Folder organization
- Tag system

### Scheduler Module
- Celery task queue
- Automated publishing
- Retry failed posts
- Cron job management

### Analytics Module
- Facebook Insights API
- Post performance metrics
- Engagement tracking
- Trending analysis
- Dashboard statistics

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps

# Run specific module
pytest apps/auth/tests/
```

## 📝 Development

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8 .

# Type checking
mypy .
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## 🔒 Security

- JWT token authentication
- CORS protection
- SQL injection prevention (Django ORM)
- XSS protection
- CSRF protection
- Rate limiting
- Encrypted Facebook tokens

## 📊 Monitoring

- Sentry integration for error tracking
- Request logging
- Facebook API call logging
- Performance monitoring

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY`
- [ ] Configure PostgreSQL database
- [ ] Setup Redis for caching
- [ ] Configure local media storage directory
- [ ] Setup backup strategy for media files
- [ ] Setup Celery workers
- [ ] Configure HTTPS
- [ ] Setup domain and DNS
- [ ] Configure Sentry (optional)

### Environment Variables (Production)

```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
SECRET_KEY=your-production-secret-key
DB_HOST=your-db-host
REDIS_URL=redis://your-redis-host
MEDIA_ROOT=media
MAX_UPLOAD_SIZE=10485760
SENTRY_DSN=your-sentry-dsn
```

## 📖 Additional Resources

- [Django Ninja Documentation](https://django-ninja.rest-framework.com/)
- [Facebook Graph API](https://developers.facebook.com/docs/graph-api/)
- [Celery Documentation](https://docs.celeryq.dev/)

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Write tests
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License

## 💡 Tips

### AI Content Generation

The system supports multiple AI providers:
- **OpenAI GPT-4**: Best for content rewriting
- **Google Gemini**: Good for Vietnamese content
- **Anthropic Claude**: Best for long-form content

### Facebook Token Management

Facebook tokens expire after 60 days. The system will:
- Auto-refresh tokens when possible
- Send notifications 7 days before expiry
- Prompt user to reconnect if needed

### Scheduling Posts

Best practices:
- Schedule posts during peak engagement hours
- Use AI to optimize posting times
- Monitor analytics to adjust schedule

## 🐛 Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
docker ps
# or
systemctl status postgresql
```

### Celery Not Working
```bash
# Check Redis is running
redis-cli ping

# Check Celery worker logs
celery -A config worker -l debug
```

### Facebook API Errors
- Check token validity: `/api/auth/status`
- Verify App permissions
- Check API rate limits

## 📞 Support

For issues and questions:
- GitHub Issues
- Email: support@example.com
