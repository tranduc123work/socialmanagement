# AI Agent Test Cases

## Mục đích
Test đầy đủ các chức năng của AI Agent để đảm bảo hoạt động chính xác.

---

## Test Case 1: Query với Date Filtering

### Prompt: "Số bài đăng trong 7 ngày tới"

**Expected Behavior:**
- Agent tự động gọi `get_scheduled_posts(days_ahead=7)`
- Trả về số lượng chính xác từ database
- Không tự ý đoán số liệu

**Expected Response:**
```
Đã thực hiện: get_scheduled_posts
Trong 7 ngày tới (từ [ngày bắt đầu] đến [ngày kết thúc]), có tổng cộng [X] bài đăng đã được lên lịch.
```

**Validation:**
- [ ] Agent gọi function với `days_ahead=7`
- [ ] Số lượng bài đăng chính xác với database
- [ ] Không có câu "Bạn có muốn tôi..."

---

## Test Case 2: Query Scheduled Posts General

### Prompt: "Có bao nhiêu bài đăng đã lên lịch?"

**Expected Behavior:**
- Agent gọi `get_system_stats()` hoặc `get_scheduled_posts()`
- Trả về thống kê tổng quan

**Expected Response:**
```
Đã thực hiện: get_system_stats
Bạn có [X] bài đăng đã lên lịch, [Y] bài do Agent tạo, và [Z] file media.
```

**Validation:**
- [ ] Agent tự động gọi tool
- [ ] Số liệu chính xác
- [ ] Response rõ ràng, dễ hiểu

---

## Test Case 3: Get Specific Post Content

### Prompt: "Lấy nội dung của bài đăng ngày 27/11/2025"

**Expected Behavior:**
- Agent gọi `get_scheduled_posts(start_date="2025-11-27", end_date="2025-11-27")`
- Trả về nội dung chi tiết của bài đăng đó

**Expected Response:**
```
Đã thực hiện: get_scheduled_posts
Bài đăng ngày 27/11/2025:
- Chủ đề: [title]
- Nội dung: [preview]
- Loại hình: [business_type]
- Mục tiêu: [goal]
```

**Validation:**
- [ ] Agent filter đúng ngày
- [ ] Hiển thị đầy đủ thông tin bài đăng
- [ ] Format dễ đọc

---

## Test Case 4: Create Post - Full Workflow

### Prompt: "Tạo 1 bài đăng về mái lợp nhựa, chủ đề tiết kiệm điện mùa hè"

**Expected Behavior:**
- Agent tự động gọi `generate_post_content()`
- Agent tự động gọi `generate_post_image()`
- Agent gọi `create_agent_post()` để lưu vào database
- Bài đăng xuất hiện ở Posts Gallery

**Expected Response:**
```
Đã thực hiện:
- generate_post_content
- generate_post_image
- create_agent_post

Đã tạo xong bài đăng! Bạn có thể xem ở phần Bài đăng.

Nội dung: [preview]
Hashtags: [hashtags]
```

**Validation:**
- [ ] Agent gọi 3 tools theo thứ tự
- [ ] Content được generate
- [ ] Image được generate và lưu vào Media
- [ ] AgentPost được tạo trong database
- [ ] Post xuất hiện ở gallery trong UI

---

## Test Case 5: Create Post - Simple Request

### Prompt: "Tạo bài đăng cho tôi"

**Expected Behavior:**
- Agent hỏi thêm thông tin (business type, topic, goal)
- Không tự động generate với thông tin thiếu

**Expected Response:**
```
Để tôi tạo bài đăng cho bạn nhé. Vui lòng cho tôi biết thêm thông tin:
- Loại hình kinh doanh: Bạn đang kinh doanh về lĩnh vực gì?
- Chủ đề bài đăng: Bạn muốn bài đăng nói về điều gì?
- Mục tiêu: Bạn muốn đạt được điều gì?
```

**Validation:**
- [ ] Agent không tự ý đoán thông tin
- [ ] Hỏi rõ ràng những gì cần
- [ ] Response thân thiện

---

## Test Case 6: Analyze Schedule

### Prompt: "Phân tích lịch đăng của tôi"

**Expected Behavior:**
- Agent gọi `get_scheduled_posts()` để lấy data
- Agent gọi `analyze_schedule()` để phân tích
- Đưa ra insights về lịch đăng

**Expected Response:**
```
Đã thực hiện:
- get_scheduled_posts
- analyze_schedule

Phân tích lịch đăng của bạn:
- Tổng số bài: [X]
- Phân bố: [breakdown by status/date]
- Recommendations: [suggestions]
```

**Validation:**
- [ ] Agent gọi multiple tools
- [ ] Phân tích có insights hữu ích
- [ ] Format dễ đọc

---

## Test Case 7: Query Posts by Status

### Prompt: "Có bao nhiêu bài draft?"

**Expected Behavior:**
- Agent gọi `get_scheduled_posts(status="draft")`
- Trả về số lượng bài draft

**Expected Response:**
```
Đã thực hiện: get_scheduled_posts
Bạn có [X] bài đăng ở trạng thái draft.
```

**Validation:**
- [ ] Filter đúng status
- [ ] Số lượng chính xác
- [ ] Response ngắn gọn

---

## Test Case 8: Query Future Posts

### Prompt: "Bài đăng nào sẽ được đăng trong 3 ngày tới?"

**Expected Behavior:**
- Agent gọi `get_scheduled_posts(days_ahead=3, status="scheduled")`
- List ra các bài sẽ đăng

**Expected Response:**
```
Đã thực hiện: get_scheduled_posts
Trong 3 ngày tới, có [X] bài sẽ được đăng:
1. [date] - [title]
2. [date] - [title]
...
```

**Validation:**
- [ ] Filter đúng date range
- [ ] Filter đúng status
- [ ] List format dễ đọc

---

## Test Case 9: System Stats

### Prompt: "Tổng quan hệ thống hiện tại"

**Expected Behavior:**
- Agent gọi `get_system_stats()`
- Trả về đầy đủ thống kê

**Expected Response:**
```
Đã thực hiện: get_system_stats
Tổng quan hệ thống:
- Scheduled posts: [X] (draft: [Y], published: [Z])
- Agent posts: [A]
- Media files: [B]
```

**Validation:**
- [ ] Hiển thị đầy đủ stats
- [ ] Số liệu chính xác
- [ ] Format rõ ràng

---

## Test Case 10: Invalid/Edge Cases

### 10.1 Prompt: "Xóa tất cả bài đăng"

**Expected Behavior:**
- Agent từ chối hoặc cảnh báo
- Không thực hiện hành động nguy hiểm

### 10.2 Prompt: "asdfasdfasdf"

**Expected Behavior:**
- Agent trả lời lịch sự
- Hỏi lại hoặc suggest các câu hỏi hợp lệ

### 10.3 Prompt: "Bài đăng ngày 99/99/9999"

**Expected Behavior:**
- Agent handle date không hợp lệ
- Thông báo lỗi rõ ràng

---

## Checklist tổng quan

### Auto Tool Execution
- [ ] Agent tự động gọi tools khi cần thông tin
- [ ] Không hỏi permission ("Bạn có muốn tôi...")
- [ ] Luôn trả về data thực tế từ database

### Data Accuracy
- [ ] Số liệu từ database luôn chính xác
- [ ] Date filtering hoạt động đúng
- [ ] Status filtering chính xác

### Post Creation
- [ ] Generate content hoạt động
- [ ] Generate image hoạt động
- [ ] Create post lưu vào database
- [ ] Post hiển thị trong UI

### Response Quality
- [ ] Tiếng Việt tự nhiên
- [ ] Response rõ ràng, dễ hiểu
- [ ] Hiển thị function calls đã thực hiện
- [ ] Không tự ý đoán thông tin

### Error Handling
- [ ] Handle invalid input
- [ ] Handle missing parameters
- [ ] Handle tool execution errors
- [ ] Error messages rõ ràng

---

## Cách Test

### Manual Testing (Recommended)
1. Start backend server: `python manage.py runserver`
2. Start frontend: `npm run dev`
3. Vào Agent Dashboard
4. Thử từng prompt ở trên
5. Verify expected behavior
6. Check database nếu cần

### Backend Testing
```bash
cd backend
python manage.py shell

# Test tool execution
from apps.agent.services import AgentToolExecutor
from apps.auth.models import User

user = User.objects.first()

# Test get_scheduled_posts with days_ahead
result = AgentToolExecutor.get_scheduled_posts(user, days_ahead=7)
print(result)

# Test create post
result = AgentToolExecutor.create_agent_post(
    user=user,
    content="Test content",
    hashtags=["#test"],
    image_description="Test image"
)
print(result)
```

### Check Database
```sql
-- Check scheduled posts count
SELECT COUNT(*) FROM ai_scheduledcontent
WHERE schedule_date >= CURRENT_DATE
  AND schedule_date <= CURRENT_DATE + INTERVAL '7 days';

-- Check agent posts
SELECT * FROM agent_agentpost ORDER BY created_at DESC LIMIT 5;
```

---

## Expected Results Summary

| Test Case | Priority | Expected Result |
|-----------|----------|-----------------|
| Date Filtering | HIGH | ✅ Works correctly |
| Create Post | HIGH | ✅ Full workflow |
| System Stats | MEDIUM | ✅ Accurate data |
| Analyze Schedule | MEDIUM | ✅ Useful insights |
| Error Handling | HIGH | ✅ Graceful errors |

---

## Notes
- Tất cả test cases nên pass trước khi deploy
- Nếu có test case fail, cần fix ngay
- Document bất kỳ behavior không mong đợi nào
