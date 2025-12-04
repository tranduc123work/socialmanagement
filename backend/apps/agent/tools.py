"""
Tool Definitions cho Agent
Định nghĩa các tools (functions) mà Agent có thể sử dụng
Format theo Gemini API requirements (UPPERCASE types)
"""

from typing import List, Dict


def get_tool_definitions() -> List[Dict]:
    """
    Trả về danh sách tool definitions cho Gemini API
    """
    return [
        {
            "name": "get_current_datetime",
            "description": """Lấy thông tin thời gian hiện tại.
CẦN KHI: User nói "ngày mai", "hôm nay", "tuần sau", "tháng này"...
TRẢ VỀ: today, tomorrow, day_of_week, current_time, year, month.
THƯỜNG DÙNG CÙNG: get_scheduled_posts, get_agent_posts (khi cần filter theo ngày).""",
            "parameters": {
                "type": "OBJECT",
                "properties": {}
            }
        },
        {
            "name": "get_agent_posts",
            "description": """Lấy danh sách bài đăng đã được Agent tạo trước đó từ database.
CẦN KHI: User muốn xem lại posts agent đã tạo, kiểm tra bài đã tạo.
TRẢ VỀ: post_id, content, status, created_at, images.
THƯỜNG DÙNG CÙNG: get_current_datetime (khi filter theo ngày).""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "limit": {
                        "type": "INTEGER",
                        "description": "Số lượng posts cần lấy, mặc định 20"
                    },
                    "status": {
                        "type": "STRING",
                        "description": "Filter: all, pending, completed, failed"
                    }
                }
            }
        },
        {
            "name": "get_agent_post_details",
            "description": """Lấy chi tiết đầy đủ của một bài đăng Agent đã tạo theo ID.
CẦN KHI: User muốn xem/sửa bài đăng cụ thể, VD: "sửa bài đăng #123".
TRẢ VỀ: post_id, content, full_content, hashtags, status, images, agent_reasoning.
THƯỜNG DÙNG CÙNG: edit_agent_post (sau khi xem chi tiết và user xác nhận muốn sửa gì).""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "post_id": {
                        "type": "INTEGER",
                        "description": "ID bài đăng cần xem chi tiết (BẮT BUỘC)"
                    }
                },
                "required": ["post_id"]
            }
        },
        {
            "name": "get_scheduled_posts",
            "description": """Lấy danh sách lịch đăng bài đã schedule từ database.
CẦN KHI: User hỏi về lịch đăng, schedule, bài đã lên kế hoạch.
TRẢ VỀ: scheduled_date, business_type, full_content, goal, content_type.
THƯỜNG DÙNG: relative_day='today' (hôm nay), relative_day='tomorrow' (ngày mai), relative_day='this_week' (tuần này).
THƯỜNG DÙNG CÙNG: get_current_datetime (khi có từ thời gian), get_connected_accounts (khi tạo bài cho pages).""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "relative_day": {
                        "type": "STRING",
                        "description": "Ngày tương đối: 'today' (hôm nay), 'tomorrow' (ngày mai), 'this_week' (tuần này)"
                    },
                    "days_ahead": {
                        "type": "INTEGER",
                        "description": "Số ngày tới từ hôm nay (VD: 7 = hôm nay đến 7 ngày sau)"
                    },
                    "status": {
                        "type": "STRING",
                        "description": "Filter: draft, approved, scheduled, published"
                    },
                    "limit": {
                        "type": "INTEGER",
                        "description": "Số lượng, mặc định 10"
                    },
                    "start_date": {
                        "type": "STRING",
                        "description": "Ngày bắt đầu (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "STRING",
                        "description": "Ngày kết thúc (YYYY-MM-DD)"
                    }
                }
            }
        },
        {
            "name": "get_system_stats",
            "description": """Thống kê tổng quan hệ thống.
KHI NÀO DÙNG: User hỏi về stats, số lượng posts/pages/media.
INTENT: Chỉ XEM thống kê.""",
            "parameters": {
                "type": "OBJECT",
                "properties": {}
            }
        },
        {
            "name": "generate_post_content",
            "description": """Tạo/chau chuốt nội dung bài đăng bằng AI.
CẦN KHI: User muốn tạo bài mới HOẶC có content nháp cần chau chuốt.
TRẢ VỀ: content hoàn chỉnh (mặc định ~100 từ, có thể thay đổi nếu user yêu cầu).
SAU KHI GỌI: Gọi generate_post_image với content này, rồi save_agent_post.""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "draft_content": {
                        "type": "STRING",
                        "description": "Nội dung nháp cần chau chuốt (từ lịch hoặc user cung cấp)"
                    },
                    "page_context": {
                        "type": "STRING",
                        "description": "Tên page + category để customize nội dung. VD: 'Everest Light Bắc Ninh - Vật liệu xây dựng'"
                    },
                    "topic": {
                        "type": "STRING",
                        "description": "Chủ đề bài đăng (nếu không có draft_content)"
                    },
                    "goal": {
                        "type": "STRING",
                        "description": "Mục tiêu: awareness, engagement, conversion"
                    },
                    "tone": {
                        "type": "STRING",
                        "description": "Giọng điệu: professional, casual, friendly, funny"
                    },
                    "word_count": {
                        "type": "INTEGER",
                        "description": "Số từ mong muốn (mặc định 100). Chỉ dùng nếu user yêu cầu số từ khác."
                    }
                },
                "required": []
            }
        },
        {
            "name": "generate_post_image",
            "description": """Tạo hình ảnh bằng AI phù hợp với content bài đăng.
CẦN KHI: Đã có content hoàn chỉnh (từ generate_post_content) và cần tạo ảnh.
TRẢ VỀ: media_ids (list), images với URLs.
SAU KHI GỌI: Gọi save_agent_post với content và image_ids (truyền media_ids) để lưu TẤT CẢ ảnh.
MẶC ĐỊNH: Tạo 3 ảnh. User có thể yêu cầu số lượng khác.""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "post_content": {
                        "type": "STRING",
                        "description": "Content bài đăng đã generate (từ generate_post_content) - dùng để tạo ảnh phù hợp"
                    },
                    "page_context": {
                        "type": "STRING",
                        "description": "Tên page + ngành nghề để customize ảnh. VD: 'Everest Light Bắc Ninh - Vật liệu xây dựng'"
                    },
                    "style": {
                        "type": "STRING",
                        "description": "Phong cách: professional, modern, minimalist, colorful"
                    },
                    "size": {
                        "type": "STRING",
                        "description": "Kích thước: 1080x1080, 1200x628, 1080x1920"
                    },
                    "count": {
                        "type": "INTEGER",
                        "description": "Số lượng ảnh cần tạo (mặc định 3). Có thể từ 1-5 ảnh"
                    }
                },
                "required": ["post_content"]
            }
        },
        {
            "name": "save_agent_post",
            "description": """Lưu bài đăng hoàn chỉnh vào database.
CẦN KHI: Đã có content (từ generate_post_content) VÀ image (từ generate_post_image).
TRẢ VỀ: post_id, status, image_urls, layout.
QUAN TRỌNG: Tool này CHỈ LƯU, không generate. Phải gọi generate_post_content và generate_post_image trước.
LƯU Ý: Dùng image_ids để lưu TẤT CẢ hình ảnh từ generate_post_image (media_ids).
LAYOUT: Lấy từ kết quả generate_post_image để hiển thị đúng bố cục Facebook.""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "content": {
                        "type": "STRING",
                        "description": "Nội dung đã generate từ generate_post_content"
                    },
                    "image_ids": {
                        "type": "ARRAY",
                        "items": {"type": "INTEGER"},
                        "description": "Danh sách media_ids từ generate_post_image (để lưu TẤT CẢ hình ảnh)"
                    },
                    "image_id": {
                        "type": "INTEGER",
                        "description": "ID của 1 image (dùng image_ids thay thế để lưu nhiều ảnh)"
                    },
                    "page_context": {
                        "type": "STRING",
                        "description": "Tên page để reference. VD: 'Everest Light Bắc Ninh'"
                    },
                    "layout": {
                        "type": "STRING",
                        "description": "Layout từ generate_post_image: single, two_square, one_large_two_small, four_square, two_large_three_small"
                    }
                },
                "required": ["content"]
            }
        },
        {
            "name": "edit_agent_post",
            "description": """Chỉnh sửa bài đăng Agent đã tạo.
CẦN KHI: User muốn sửa/edit bài đăng đã có (post_id).
TRẢ VỀ: post_id, content mới, hashtags mới.
LƯU Ý: Nếu regenerate_images=true, sẽ tạo ảnh mới (tốn thời gian).""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "post_id": {
                        "type": "INTEGER",
                        "description": "ID bài đăng cần sửa (BẮT BUỘC)"
                    },
                    "new_content": {
                        "type": "STRING",
                        "description": "Nội dung mới cho bài đăng"
                    },
                    "new_hashtags": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Hashtags mới, VD: ['#sale', '#khuyenmai']"
                    },
                    "regenerate_images": {
                        "type": "BOOLEAN",
                        "description": "Có tạo ảnh mới không (mặc định false)"
                    },
                    "image_count": {
                        "type": "INTEGER",
                        "description": "Số ảnh cần tạo nếu regenerate_images=true (mặc định 3)"
                    }
                },
                "required": ["post_id"]
            }
        },
        {
            "name": "batch_edit_agent_posts",
            "description": """Chỉnh sửa NHIỀU bài đăng Agent cùng lúc.
CẦN KHI: User muốn sửa nhiều bài đăng, VD: "sửa bài #101, #102, #103: thêm hashtag..."
TRẢ VỀ: success_count, fail_count, results chi tiết.
LƯU Ý: Dùng edit_instruction để AI tự động sửa từng bài theo yêu cầu.""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "post_ids": {
                        "type": "ARRAY",
                        "items": {"type": "INTEGER"},
                        "description": "Danh sách ID các bài đăng cần sửa (BẮT BUỘC), VD: [101, 102, 103]"
                    },
                    "edit_instruction": {
                        "type": "STRING",
                        "description": "Hướng dẫn sửa đổi - AI sẽ áp dụng cho từng bài. VD: 'thêm hashtag #khuyenmai', 'viết lại ngắn gọn hơn'"
                    },
                    "new_hashtags": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Hashtags mới áp dụng cho TẤT CẢ bài đăng"
                    },
                    "regenerate_images": {
                        "type": "BOOLEAN",
                        "description": "Có tạo ảnh mới cho tất cả bài không (mặc định false, tốn thời gian)"
                    },
                    "image_count": {
                        "type": "INTEGER",
                        "description": "Số ảnh cần tạo nếu regenerate_images=true (mặc định 3)"
                    }
                },
                "required": ["post_ids"]
            }
        },
        {
            "name": "analyze_schedule",
            "description": """Phân tích lịch đăng, đưa ra insights và recommendations.
KHI NÀO DÙNG: User muốn phân tích, đánh giá lịch đăng.
INTENT: Chỉ XEM phân tích.""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "schedule_id": {
                        "type": "INTEGER",
                        "description": "ID của schedule cần phân tích"
                    }
                }
            }
        },
        {
            "name": "get_connected_accounts",
            "description": """Lấy danh sách pages/tài khoản mạng xã hội đang kết nối từ database.
CẦN KHI: User hỏi về pages, tài khoản Facebook, kết nối.
TRẢ VỀ: name, platform, category, is_active, token_status.
THƯỜNG DÙNG CÙNG: generate_post_content (dùng name làm page_context), get_scheduled_posts (khi tạo bài).""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "platform": {
                        "type": "STRING",
                        "description": "Filter theo platform: facebook, instagram, zalo, tiktok (mặc định: tất cả)"
                    },
                    "active_only": {
                        "type": "BOOLEAN",
                        "description": "Chỉ lấy tài khoản đang active (mặc định: true)"
                    }
                }
            }
        },
        {
            "name": "update_page_info",
            "description": """Cập nhật thông tin Facebook page.
CẦN KHI: User muốn sửa thông tin page như about, description, phone, website, emails.
TRẢ VỀ: success status, updated fields.
LƯU Ý: Cần account_id từ get_connected_accounts(). Chỉ cập nhật các trường được cung cấp.""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "account_id": {
                        "type": "INTEGER",
                        "description": "ID của page (từ get_connected_accounts)"
                    },
                    "about": {
                        "type": "STRING",
                        "description": "Giới thiệu ngắn về page (tối đa 255 ký tự)"
                    },
                    "description": {
                        "type": "STRING",
                        "description": "Mô tả chi tiết về page"
                    },
                    "phone": {
                        "type": "STRING",
                        "description": "Số điện thoại liên hệ"
                    },
                    "website": {
                        "type": "STRING",
                        "description": "Website URL"
                    },
                    "emails": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Danh sách email liên hệ"
                    }
                },
                "required": ["account_id"]
            }
        },
        {
            "name": "update_page_photo",
            "description": """Cập nhật ảnh đại diện hoặc ảnh bìa của Facebook page.
CẦN KHI: User muốn đổi avatar hoặc cover photo của page.
TRẢ VỀ: success status, photo info.
LƯU Ý: Dùng media_id từ thư viện ảnh hoặc image_url.""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "account_id": {
                        "type": "INTEGER",
                        "description": "ID của page (từ get_connected_accounts)"
                    },
                    "photo_type": {
                        "type": "STRING",
                        "description": "Loại ảnh: 'picture' (avatar) hoặc 'cover' (ảnh bìa)"
                    },
                    "media_id": {
                        "type": "INTEGER",
                        "description": "ID của ảnh từ thư viện media"
                    },
                    "image_url": {
                        "type": "STRING",
                        "description": "URL ảnh (nếu không dùng media_id)"
                    }
                },
                "required": ["account_id", "photo_type"]
            }
        },
        {
            "name": "batch_update_pages_info",
            "description": """Cập nhật thông tin cho NHIỀU Facebook pages cùng lúc.
CẦN KHI: User muốn sửa thông tin cho nhiều pages (VD: "sửa description cho tất cả pages").
TRẢ VỀ: success_count, fail_count, results chi tiết.
LƯU Ý: Dùng account_ids từ get_connected_accounts().""",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "account_ids": {
                        "type": "ARRAY",
                        "items": {"type": "INTEGER"},
                        "description": "Danh sách ID các pages cần cập nhật"
                    },
                    "about": {
                        "type": "STRING",
                        "description": "Giới thiệu ngắn (áp dụng cho tất cả pages)"
                    },
                    "description": {
                        "type": "STRING",
                        "description": "Mô tả chi tiết (áp dụng cho tất cả pages)"
                    },
                    "phone": {
                        "type": "STRING",
                        "description": "Số điện thoại (áp dụng cho tất cả pages)"
                    },
                    "website": {
                        "type": "STRING",
                        "description": "Website URL (áp dụng cho tất cả pages)"
                    },
                    "emails": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Danh sách email (áp dụng cho tất cả pages)"
                    }
                },
                "required": ["account_ids"]
            }
        }
    ]
