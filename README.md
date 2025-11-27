# Facebook Post Management Dashboard

Full-stack application for managing Facebook posts with AI-powered content generation.

## 🎯 Features

### Frontend (React + Vite + TypeScript)
- ✅ Post Composer with AI assistance
- ✅ Content Calendar view
- ✅ Media Library management
- ✅ Token Management
- ✅ Analytics Dashboard
- ✅ Modern UI with Tailwind CSS + shadcn/ui

### Backend (Django + Django Ninja)
- ✅ JWT Authentication + Facebook OAuth
- ✅ Facebook Graph API integration
- ✅ AI Content Generation (OpenAI, Gemini, Claude)
- ✅ Post Scheduling with Celery
- ✅ Media Upload (S3/Cloudflare R2)
- ✅ Analytics & Insights
- ✅ Multi-page posting

## 📋 Tech Stack

### Frontend
- React 18
- TypeScript 5
- Vite 6
- Tailwind CSS 4
- shadcn/ui components
- React Hook Form
- Recharts (Analytics)

### Backend
- Python 3.12
- Django 5.0
- Django Ninja (FastAPI-style)
- PostgreSQL 14+
- Redis 7+
- Celery (Task Queue)
- OpenAI, Gemini (AI)

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.12+
- PostgreSQL 14+
- Redis 7+
- Facebook App credentials

### 1. Clone Repository

```bash
git clone <repository-url>
cd dashboard
```

### 2. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will run at: **http://localhost:3000**

### 3. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Setup database
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Run server
python manage.py runserver 8000
```

Backend API: **http://localhost:8000/api/**
API Docs: **http://localhost:8000/api/docs**

### 4. Run Celery (for scheduling)

```bash
cd backend

# Celery Worker
celery -A config worker -l info

# Celery Beat (in separate terminal)
celery -A config beat -l info
```

## 🐳 Docker Setup (Recommended)

```bash
# Run everything with Docker
docker-compose up -d
```

This starts:
- Frontend (localhost:3000)
- Backend (localhost:8000)
- PostgreSQL (localhost:5432)
- Redis (localhost:6379)
- Celery Worker & Beat

## 📁 Project Structure

```
dashboard/
├── frontend/                 # React Frontend
│   ├── src/
│   │   ├── components/      # UI Components
│   │   │   ├── PostComposer.tsx
│   │   │   ├── ContentCalendar.tsx
│   │   │   ├── MediaLibrary.tsx
│   │   │   ├── TokenManagement.tsx
│   │   │   └── Analytics.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
└── backend/                 # Django Backend
    ├── config/             # Django settings
    ├── api/                # API core
    ├── apps/               # Application modules
    │   ├── auth/           # Authentication
    │   ├── facebook_api/   # Facebook API
    │   ├── posts/          # Post management
    │   ├── media/          # Media library
    │   ├── pages/          # Facebook pages
    │   ├── scheduler/      # Task scheduling
    │   ├── analytics/      # Analytics
    │   ├── logs/           # Logging
    │   └── notifications/  # Alerts
    ├── requirements.txt
    └── manage.py
```

## 🔑 Configuration

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000/api
```

### Backend (.env)
```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=facebook_manager
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Facebook
FACEBOOK_APP_ID=your-app-id
FACEBOOK_APP_SECRET=your-app-secret
FACEBOOK_GRAPH_API_VERSION=v19.0

# AI Services
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-anthropic-key

# AWS S3 (Optional)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=your-bucket

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

## 📚 API Documentation

Full API documentation available at: **http://localhost:8000/api/docs**

### Key Endpoints

#### Authentication
```
POST /api/auth/login              - Login
POST /api/auth/register           - Register
POST /api/auth/facebook/login     - Facebook OAuth
POST /api/auth/refresh            - Refresh token
GET  /api/auth/me                 - Current user
GET  /api/auth/status             - Token status
```

#### Posts
```
GET    /api/posts/                - List posts
POST   /api/posts/                - Create post
POST   /api/posts/{id}/publish    - Publish now
POST   /api/posts/{id}/schedule   - Schedule post
POST   /api/posts/ai/rewrite      - AI rewrite
POST   /api/posts/ai/hashtags     - Generate hashtags
```

#### Media
```
GET    /api/media/                - List media
POST   /api/media/upload          - Upload file
POST   /api/media/ai/generate     - AI image generation
DELETE /api/media/{id}            - Delete media
```

#### Pages
```
GET    /api/pages/                - List pages
POST   /api/pages/sync            - Sync from Facebook
```

#### Analytics
```
GET /api/analytics/overview       - Dashboard stats
GET /api/analytics/post/{id}      - Post insights
GET /api/analytics/trends         - Trends analysis
```

## 🎨 UI Components

The frontend uses **shadcn/ui** components:
- Tabs, Cards, Buttons
- Forms, Inputs, Textareas
- Dialogs, Dropdowns
- Charts (Recharts)
- Calendar component

## 🤖 AI Features

### Content Generation
- **AI Rewrite**: Improve post content using GPT-4/Gemini
- **Spin Content**: Generate variations
- **Hashtag Suggestions**: Auto-generate relevant hashtags
- **Caption Generation**: AI-powered captions

### Image Generation
- **AI Images**: Generate with SDXL/Imagen/DALL-E
- **Image Optimization**: Auto-resize for Facebook
- **Background Removal**: AI-powered background removal

## 📊 Analytics Features

- Post performance metrics
- Engagement tracking (likes, shares, comments)
- Reach and impressions
- Best posting times
- Content type analysis
- Trending topics

## 🔐 Security

- JWT token authentication
- Facebook token encryption
- CORS protection
- SQL injection prevention
- XSS protection
- Rate limiting
- Secure file uploads

## 🧪 Testing

### Frontend
```bash
cd frontend
npm run test
```

### Backend
```bash
cd backend
pytest
pytest --cov=apps  # With coverage
```

## 🚀 Deployment

### Frontend (Vercel/Netlify)
```bash
cd frontend
npm run build
# Deploy dist/ folder
```

### Backend (Railway/Heroku/VPS)
```bash
cd backend

# Collect static files
python manage.py collectstatic

# Run with Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Docker Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📖 Documentation

- [Frontend README](./frontend/README.md)
- [Backend README](./backend/README.md)
- [Implementation Guide](./backend/IMPLEMENTATION_GUIDE.md)
- [API Documentation](http://localhost:8000/api/docs)

## 🐛 Troubleshooting

### Frontend not connecting to backend
- Check CORS settings in backend
- Verify VITE_API_URL in frontend .env
- Ensure backend is running on port 8000

### Database connection error
```bash
# Check PostgreSQL is running
docker ps
# or
systemctl status postgresql
```

### Celery not working
```bash
# Check Redis
redis-cli ping

# Check Celery logs
celery -A config worker -l debug
```

### Facebook API errors
- Verify App credentials in .env
- Check token expiry: GET /api/auth/status
- Review API permissions
- Check rate limits

## 📞 Support & Contribution

### Issues
Report bugs and request features on GitHub Issues

### Contributing
1. Fork the repository
2. Create feature branch
3. Make changes
4. Write tests
5. Submit pull request

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- Django Ninja
- shadcn/ui
- Facebook Graph API
- OpenAI API
- Tailwind CSS

---

**Happy posting! 🚀**

For detailed setup instructions, see:
- [Backend Setup Guide](./backend/README.md)
- [Implementation Guide](./backend/IMPLEMENTATION_GUIDE.md)
