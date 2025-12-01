# 🚀 Agent Quick Test Guide

Copy và paste các prompts này vào Agent Dashboard để test nhanh.

---

## ✅ Basic Queries (Nên pass ngay)

### 1. System Stats
```
Có bao nhiêu bài đăng đã lên lịch?
```
**Expect:** Agent gọi `get_system_stats()`, hiển thị thống kê tổng quan

---

### 2. Date Filtering - 7 days
```
Số bài đăng trong 7 ngày tới
```
**Expect:** Agent gọi `get_scheduled_posts(days_ahead=7)`, trả về số chính xác (không phải 8!)

---

### 3. Date Filtering - 3 days
```
Bài đăng nào sẽ được đăng trong 3 ngày tới?
```
**Expect:** Agent gọi `get_scheduled_posts(days_ahead=3)`, list ra các bài

---

### 4. Status Filter
```
Có bao nhiêu bài draft?
```
**Expect:** Agent gọi `get_scheduled_posts(status="draft")`, trả về số draft

---

### 5. Specific Date
```
Lấy nội dung của bài đăng ngày 27/11/2025
```
**Expect:** Agent filter theo ngày cụ thể, hiển thị nội dung

---

## 🔥 Advanced Tests (Post Creation)

### 6. Create Post - Full Details
```
Tạo 1 bài đăng về mái lợp nhựa, chủ đề tiết kiệm điện mùa hè, mục tiêu awareness
```
**Expect:**
1. Agent gọi `generate_post_content()`
2. Agent gọi `generate_post_image()`
3. Agent gọi `create_agent_post()`
4. Bài đăng xuất hiện ở Posts Gallery (bên phải)

⚠️ Lưu ý: Việc tạo image có thể mất 10-20s

---

### 7. Create Post - Minimal Info
```
Tạo bài đăng cho tôi
```
**Expect:** Agent hỏi thêm thông tin (business type, topic, goal)

---

### 8. Create Post - Restaurant
```
Tạo bài đăng về nhà hàng Việt Nam, giới thiệu món phở
```
**Expect:** Agent tự động infer business_type="Restaurant", tạo post về phở

---

## 🎯 Edge Cases

### 9. Invalid Date
```
Bài đăng ngày 99/99/9999
```
**Expect:** Agent handle gracefully, thông báo không tìm thấy hoặc ngày không hợp lệ

---

### 10. Empty Result
```
Số bài đăng trong 365 ngày tới
```
**Expect:** Nếu không có bài nào, agent nói "Không có bài đăng nào..."

---

### 11. Analyze Schedule
```
Phân tích lịch đăng của tôi
```
**Expect:** Agent gọi multiple tools, đưa ra insights

---

## ❌ What NOT to Expect

Agent KHÔNG nên:
- ❌ Hỏi "Bạn có muốn tôi..."
- ❌ Tự ý đoán số liệu (phải lấy từ database)
- ❌ Return error khi có data trong database
- ❌ Tạo post khi thiếu thông tin cần thiết

---

## ✅ Verification Checklist

Sau khi test, check:

- [ ] Agent TỰ ĐỘNG gọi tools (không hỏi permission)
- [ ] Số liệu CHÍNH XÁC với database
- [ ] Date filtering hoạt động ĐÚNG
- [ ] Post creation tạo được bài (nếu có đủ thông tin)
- [ ] Function calls được hiển thị trong UI
- [ ] Response bằng tiếng Việt tự nhiên
- [ ] Không có error trong console

---

## 🐛 Common Issues

### Issue 1: "Lỗi khi xử lý"
**Solution:** Check backend logs, có thể là Gemini API key hoặc model error

### Issue 2: Agent trả về số sai
**Solution:** Verify date filtering logic trong services.py

### Issue 3: Agent không gọi tools
**Solution:** Check system prompt và tool definitions

### Issue 4: Image generation fails
**Solution:** Check Gemini API key, model có hỗ trợ image generation không

### Issue 5: 401 Unauthorized
**Solution:** Check token trong localStorage, verify authentication

---

## 📊 Expected Performance

| Action | Time | Status |
|--------|------|--------|
| Query (no tools) | < 1s | Fast ⚡ |
| Query (with tools) | 1-3s | Normal ✅ |
| Generate content | 3-5s | Normal ✅ |
| Generate image | 10-20s | Slow 🐢 |
| Full post creation | 15-30s | Slow 🐢 |

---

## 🎉 Success Criteria

Test thành công khi:

1. ✅ Tất cả basic queries (1-5) hoạt động đúng
2. ✅ Date filtering trả về số chính xác
3. ✅ Agent không hỏi permission
4. ✅ Ít nhất 1 post creation thành công
5. ✅ Posts xuất hiện ở gallery
6. ✅ Không có error trong console

---

**Happy Testing! 🚀**
