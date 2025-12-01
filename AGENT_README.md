# 🤖 AI Agent Dashboard - Documentation

## 📋 Tổng quan

Tôi đã triển khai thành công một **LLM-powered AI Agent Dashboard** hoàn chỉnh cho hệ thống của bạn. Agent sử dụng **Gemini AI** làm "bộ não" để tự động tạo bài đăng và tương tác với user.

---

## ✅ Những gì đã hoàn thành

### 🔧 Backend (Django)

#### 1. **App mới: `apps/agent/`**
- ✅ **Models mới** (không ảnh hưởng code cũ):
  - `AgentPost`: Lưu bài đăng Agent tạo
  - `AgentConversation`: Lưu lịch sử chat
  - `AgentTask`: Track tasks Agent đang làm

- ✅ **LLM Agent Service** ([llm_agent.py](backend/apps/agent/llm_agent.py)):
  - Sử dụng Gemini 2.0 Flash với Function Calling
  - Agent tự động reasoning và quyết định
  - 6 tools cho Agent sử dụng:
    - `get_scheduled_posts`: Xem lịch đăng
    - `get_system_stats`: Thống kê hệ thống
    - `generate_post_content`: Tạo nội dung
    - `generate_post_image`: Tạo hình ảnh
    - `create_agent_post`: Tạo bài đăng hoàn chỉnh
    - `analyze_schedule`: Phân tích lịch

- ✅ **Services Layer** ([services.py](backend/apps/agent/services.py)):
  - `AgentToolExecutor`: Thực thi tools
  - `AgentConversationService`: Quản lý chat
  - `AgentPostService`: Quản lý posts

- ✅ **API Endpoints** ([api.py](backend/apps/agent/api.py)):
  ```
  POST   /api/agent/chat                 - Chat với Agent
  GET    /api/agent/chat/history         - Lịch sử chat
  DELETE /api/agent/chat/history         - Xóa lịch sử
  GET    /api/agent/posts                - Danh sách posts
  GET    /api/agent/posts/{id}           - Chi tiết post
  DELETE /api/agent/posts/{id}           - Xóa post
  GET    /api/agent/stats                - Thống kê
  ```

- ✅ **Database**:
  - Migrations đã tạo và chạy thành công
  - 3 tables mới: `agent_agentpost`, `agent_agentconversation`, `agent_agenttask`

---

### 🎨 Frontend (Next.js + React)

#### 1. **Components mới**

- ✅ **AgentChat** ([AgentChat.tsx](frontend/src/components/AgentChat.tsx)):
  - Chat interface đẹp, real-time
  - Hiển thị function calls Agent đã thực hiện
  - Auto-scroll, typing indicator
  - Xóa lịch sử conversation

- ✅ **AgentPostsGallery** ([AgentPostsGallery.tsx](frontend/src/components/AgentPostsGallery.tsx)):
  - Grid view hiển thị bài đăng
  - Preview nội dung + hình ảnh
  - Detail sidebar khi click vào post
  - Xóa posts

- ✅ **AgentDashboard** ([AgentDashboard.tsx](frontend/src/components/AgentDashboard.tsx)):
  - Split view: Chat bên trái, Posts bên phải
  - Responsive: Mobile có tabs

- ✅ **Service Layer** ([agentService.ts](frontend/src/services/agentService.ts)):
  - Tất cả API calls cho Agent
  - TypeScript interfaces

#### 2. **Integration với Dashboard chính**

- ✅ Tab "AI Agent" đã được thêm vào sidebar
- ✅ Icon Bot, highlight màu xanh khi active
- ✅ Không ảnh hưởng các tabs cũ

---

## 🚀 Cách sử dụng

### 1. **Start Backend**

```bash
cd backend
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Linux/Mac

python manage.py runserver
```

### 2. **Start Frontend**

```bash
cd frontend
npm run dev
```

### 3. **Truy cập Agent Dashboard**

1. Login vào hệ thống: `http://localhost:3000`
2. Click vào tab **"AI Agent"** ở sidebar
3. Bạn sẽ thấy 2 phần:
   - **Bên trái**: Chat với Agent
   - **Bên phải**: Bài đăng Agent đã tạo

---

## 💬 Ví dụ Chat với Agent

### **Hỏi về hệ thống:**
```
User: "Có bao nhiêu bài đăng đã tạo?"
Agent: *Gọi get_system_stats()*
       "Bạn có 15 bài đăng đã lên lịch, 3 bài do Agent tạo..."
```

### **Yêu cầu tạo bài đăng:**
```
User: "Tạo bài đăng về sản phẩm mới cho nhà hàng"
Agent: *Reasoning...*
       *Gọi generate_post_content()*
       *Gọi generate_post_image()*
       *Gọi create_agent_post()*
       "Đã tạo xong bài đăng! Bạn có thể xem ở bên phải."
```

### **Phân tích lịch đăng:**
```
User: "Phân tích lịch đăng của tôi"
Agent: *Gọi get_scheduled_posts()*
       *Gọi analyze_schedule()*
       "Bạn có 10 bài draft, 5 bài scheduled..."
```

---

## 📂 Cấu trúc File đã tạo

### Backend:
```
backend/
├── apps/agent/               # ✨ NEW APP
│   ├── __init__.py
│   ├── models.py            # AgentPost, AgentConversation, AgentTask
│   ├── admin.py             # Django admin
│   ├── api.py               # API endpoints
│   ├── services.py          # Business logic & tools
│   ├── llm_agent.py         # Gemini LLM Agent
│   └── migrations/
│       └── 0001_initial.py  # Database migrations
│
└── api/
    └── router.py            # ✏️ UPDATED - Added agent router
```

### Frontend:
```
frontend/src/
├── components/
│   ├── AgentChat.tsx              # ✨ NEW - Chat interface
│   ├── AgentPostsGallery.tsx      # ✨ NEW - Posts gallery
│   ├── AgentDashboard.tsx         # ✨ NEW - Main dashboard
│   └── Dashboard.tsx              # ✏️ UPDATED - Added Agent tab
│
└── services/
    └── agentService.ts            # ✨ NEW - API service
```

---

## 🎯 Workflow hoàn chỉnh

```
1. User chat với Agent:
   "Tạo bài đăng về đồ ăn Việt Nam"

2. Agent (Gemini) tự động reasoning:
   - "Hmm, user muốn tạo bài về đồ ăn VN"
   - "Tôi sẽ tạo content hấp dẫn"
   - "Cần tạo hình ảnh món ăn"

3. Agent tự động gọi tools:
   - generate_post_content(business_type="Restaurant", topic="Đồ ăn VN")
   - generate_post_image(description="Traditional Vietnamese food...")
   - create_agent_post(content=..., image=...)

4. Kết quả:
   ✅ Bài đăng xuất hiện ở Posts Gallery
   ✅ Có cả content và hình ảnh
   ✅ User có thể xem, xóa, hoặc sử dụng
```

---

## 🔑 API Key Setup

Agent sử dụng Gemini API key từ `.env`:

```bash
# backend/.env
GEMINI_API_KEY=AIzaSyBHq5LxXtqENgENbDiU6O3b9_LmVQkt-bc
```

**✅ Đã có sẵn và đang hoạt động!**

---

## 🛠️ Troubleshooting

### Backend không start?
```bash
# Check migrations
python manage.py migrate

# Check if Agent app loaded
python manage.py check
```

### Frontend lỗi?
```bash
# Reinstall dependencies
npm install

# Clear cache
rm -rf .next
npm run dev
```

### Agent không trả lời?
- Check console logs
- Verify Gemini API key
- Check network tab trong DevTools

---

## 📊 Database Schema

### AgentPost
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| user_id | ForeignKey | User owner |
| content | Text | Nội dung bài đăng |
| hashtags | JSON | Array hashtags |
| generated_image_id | ForeignKey | Media ID |
| status | String | generating/completed/failed |
| created_at | DateTime | Thời gian tạo |

### AgentConversation
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| user_id | ForeignKey | User owner |
| role | String | user/agent/system |
| message | Text | Nội dung tin nhắn |
| function_calls | JSON | Tools đã gọi |
| created_at | DateTime | Thời gian tạo |

---

## ✨ Tính năng nổi bật

### 1. **LLM-Powered Reasoning**
- Agent tự suy nghĩ và quyết định
- Không phải hard-code logic
- Adapt theo context tự động

### 2. **Function Calling**
- Agent có thể gọi 6 tools khác nhau
- Tự động chọn tool phù hợp
- Chain multiple tools lại với nhau

### 3. **Isolated & Safe**
- Code hoàn toàn độc lập
- Không ảnh hưởng features cũ
- Có thể bật/tắt dễ dàng

### 4. **Beautiful UI**
- Split view desktop
- Responsive mobile
- Real-time updates
- Smooth animations

---

## 🎉 Kết luận

✅ **Hoàn thành 100%** theo yêu cầu của bạn:
- ✅ Agent sử dụng Gemini LLM
- ✅ Chat interface để hỏi Agent
- ✅ Agent tự động tạo bài đăng (content + image)
- ✅ Hiển thị bài đăng Agent tạo
- ✅ Không ảnh hưởng code cũ
- ✅ Code riêng biệt, dễ maintain

Bạn có thể bắt đầu sử dụng ngay! 🚀

---

## 🧪 Testing Agent

### Automated Testing

Chạy test suite để verify tất cả chức năng:

```bash
cd backend
python test_agent.py
```

Test suite sẽ kiểm tra:
- ✅ Tool definitions (date parameters)
- ✅ Get scheduled posts với date filtering
- ✅ System stats
- ✅ Generate content
- ✅ Create agent post
- ✅ Full conversation flow

### Manual Testing - Quick Prompts

Vào Agent Dashboard và thử các prompt sau:

#### 1. **Query với Date Filtering** ✨ NEW
```
"Số bài đăng trong 7 ngày tới"
```
Expected: Agent gọi `get_scheduled_posts(days_ahead=7)` và trả về số chính xác

#### 2. **System Stats**
```
"Có bao nhiêu bài đăng đã lên lịch?"
```
Expected: Agent gọi `get_system_stats()` và hiển thị thống kê

#### 3. **Get Specific Post**
```
"Lấy nội dung của bài đăng ngày 27/11/2025"
```
Expected: Agent filter theo ngày và hiển thị chi tiết

#### 4. **Create Post** 🔥
```
"Tạo 1 bài đăng về mái lợp nhựa, chủ đề tiết kiệm điện mùa hè"
```
Expected:
- Agent gọi `generate_post_content()`
- Agent gọi `generate_post_image()`
- Agent gọi `create_agent_post()`
- Bài đăng xuất hiện ở Posts Gallery

#### 5. **Filter by Status**
```
"Có bao nhiêu bài draft?"
```
Expected: Agent filter theo status và trả về số lượng

### Test Cases Document

Chi tiết đầy đủ: Xem [AGENT_TEST_CASES.md](AGENT_TEST_CASES.md)

---

## 📝 Notes

- Agent dừng ở bước **gửi thông báo** (không publish lên Facebook)
- Để thêm auto-publish, cần implement phần approval workflow
- Agent có thể mở rộng thêm nhiều tools khác

---

## 🔄 Recent Updates

### ✨ Date Filtering (Latest)
- ✅ Thêm `days_ahead`, `start_date`, `end_date` parameters
- ✅ Agent có thể query posts theo khoảng thời gian
- ✅ Fix vấn đề agent trả về số liệu không chính xác
- ✅ Tool definition updated với date parameters

### 🐛 Bug Fixes
- ✅ Fix conversation flow (chat_session vs raw_response)
- ✅ Fix token authentication (access_token từ tokens object)
- ✅ Fix tool type definitions (UPPERCASE format)
- ✅ Fix agent auto-execution (không hỏi permission)

---

**Tạo bởi Claude Code** 🤖
