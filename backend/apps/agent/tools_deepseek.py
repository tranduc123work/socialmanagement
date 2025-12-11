"""
Tool Definitions cho DeepSeek Agent
Format theo OpenAI API (lowercase types, wrapped in function object)
"""

from typing import List, Dict


def get_tool_definitions() -> List[Dict]:
    """
    Trả về danh sách tool definitions cho OpenAI/DeepSeek API
    Format: {"type": "function", "function": {...}}
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": """Lấy thông tin thời gian hiện tại.
CẦN KHI: User nói "ngày mai", "hôm nay", "tuần sau", "tháng này"...
TRẢ VỀ: today, tomorrow, day_of_week, current_time, year, month.
THƯỜNG DÙNG CÙNG: get_scheduled_posts, get_agent_posts (khi cần filter theo ngày).""",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_agent_settings",
                "description": """Lấy thông tin cài đặt Fugu Settings của user.
CẦN KHI: User muốn dùng logo/brand settings đã cài đặt.
TRẢ VỀ: logo_id, logo_url, logo_position, logo_size, hotline, website, slogan, brand_colors, default_tone.
⚠️ QUAN TRỌNG: Dùng logo_id để cập nhật ảnh đại diện page TRỰC TIẾP với update_page_photo.
VD: User nói "đổi avatar tất cả pages bằng logo trong settings" → get_agent_settings() → update_page_photo(media_id=logo_id)""",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_agent_posts",
                "description": """Lấy danh sách bài đăng đã được Agent tạo trước đó từ database.
CẦN KHI: User muốn xem lại posts agent đã tạo, kiểm tra bài đã tạo.
TRẢ VỀ: post_id, content, status, created_at, images.
THƯỜNG DÙNG CÙNG: get_current_datetime (khi filter theo ngày).""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Số lượng posts cần lấy, mặc định 20"
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter: all, pending, completed, failed"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_agent_post_details",
                "description": """Lấy chi tiết đầy đủ của một bài đăng Agent đã tạo theo ID.
CẦN KHI: User muốn xem/sửa bài đăng cụ thể, VD: "sửa bài đăng #123".
TRẢ VỀ: post_id, content, full_content, hashtags, status, images, agent_reasoning.
THƯỜNG DÙNG CÙNG: edit_agent_post (sau khi xem chi tiết và user xác nhận muốn sửa gì).""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer",
                            "description": "ID bài đăng cần xem chi tiết (BẮT BUỘC)"
                        }
                    },
                    "required": ["post_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_scheduled_posts",
                "description": """Lấy danh sách lịch đăng bài đã schedule từ database.
CẦN KHI: User hỏi về lịch đăng, schedule, bài đã lên kế hoạch.
TRẢ VỀ: scheduled_date, business_type, full_content, goal, content_type.
CÁCH DÙNG:
- Ngày cụ thể (VD: 6/12): specific_date='2024-12-06'
- Ngày tương đối: relative_day='today'/'tomorrow'/'this_week'
- Khoảng ngày: start_date + end_date""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "specific_date": {
                            "type": "string",
                            "description": "Ngày cụ thể cần lấy (YYYY-MM-DD). VD: ngày 6/12/2025 → '2025-12-06'"
                        },
                        "relative_day": {
                            "type": "string",
                            "description": "Ngày tương đối: 'today', 'tomorrow', 'this_week'"
                        },
                        "days_ahead": {
                            "type": "integer",
                            "description": "Số ngày tới từ hôm nay"
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter: draft, approved, scheduled, published"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Số lượng, mặc định 10"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Ngày bắt đầu (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Ngày kết thúc (YYYY-MM-DD)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_system_stats",
                "description": """Thống kê tổng quan hệ thống.
KHI NÀO DÙNG: User hỏi về stats, số lượng posts/pages/media.
INTENT: Chỉ XEM thống kê.""",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_post_content",
                "description": """Tạo/chau chuốt nội dung bài đăng bằng AI.
CẦN KHI: User muốn tạo bài mới HOẶC có content nháp cần chau chuốt.
TRẢ VỀ: content hoàn chỉnh (mặc định ~100 từ, có thể thay đổi nếu user yêu cầu).
SAU KHI GỌI: Gọi generate_post_image với content này, rồi save_agent_post.
⚠️ LƯU Ý: Nếu có business_type và marketing_goals từ lịch đăng, PHẢI truyền vào để content được tối ưu cho ngành nghề.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "draft_content": {
                            "type": "string",
                            "description": "Nội dung nháp cần chau chuốt (từ lịch hoặc user cung cấp)"
                        },
                        "page_context": {
                            "type": "string",
                            "description": "Tên page + category để customize nội dung. VD: 'Everest Light Bắc Ninh - Vật liệu xây dựng'"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Chủ đề bài đăng (nếu không có draft_content)"
                        },
                        "goal": {
                            "type": "string",
                            "description": "Mục tiêu: awareness, engagement, conversion"
                        },
                        "tone": {
                            "type": "string",
                            "description": "Giọng điệu: professional, casual, friendly, funny"
                        },
                        "word_count": {
                            "type": "integer",
                            "description": "Số từ mong muốn (mặc định 100). Chỉ dùng nếu user yêu cầu số từ khác."
                        },
                        "business_type": {
                            "type": "string",
                            "description": "Ngành nghề/loại sản phẩm (từ lịch đăng). VD: 'Vật liệu xây dựng', 'Thời trang', 'F&B'"
                        },
                        "marketing_goals": {
                            "type": "string",
                            "description": "Mục tiêu marketing tổng thể (từ lịch đăng). VD: 'Tăng nhận diện thương hiệu', 'Ra mắt sản phẩm mới'"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_post_image",
                "description": """Tạo hình ảnh MỚI bằng AI phù hợp với content bài đăng.
CẦN KHI:
  - Đã có content hoàn chỉnh và cần tạo ảnh MỚI bằng AI
  - User gửi ảnh làm THAM CHIẾU để AI tạo ảnh TƯƠNG TỰ (dùng reference_image_data)
TRẢ VỀ: media_ids (list), images với URLs.
SAU KHI GỌI: Gọi save_agent_post với content và image_ids (truyền media_ids) để lưu TẤT CẢ ảnh.
MẶC ĐỊNH: Tạo 3 ảnh. User có thể yêu cầu số lượng khác.
TEXT TRÊN ẢNH: AI tự quyết định có thêm text/slogan hay không, trừ khi user chỉ định text_overlay.
⚠️ LƯU Ý: Nếu có business_type và marketing_goals từ lịch đăng, PHẢI truyền vào để ảnh được tối ưu cho ngành nghề.
KHÁC VỚI edit_image: Tool này TẠO ẢNH MỚI bằng AI, không sửa ảnh gốc.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_content": {
                            "type": "string",
                            "description": "Content bài đăng đã generate (từ generate_post_content) - dùng để tạo ảnh phù hợp"
                        },
                        "reference_image_data": {
                            "type": "string",
                            "description": "Base64 encoded image từ file user gửi - AI sẽ tạo ảnh MỚI lấy cảm hứng/tương tự ảnh này"
                        },
                        "reference_media_id": {
                            "type": "integer",
                            "description": "Media ID từ thư viện làm ảnh tham chiếu cho AI"
                        },
                        "text_overlay": {
                            "type": "string",
                            "description": "Text/slogan cụ thể để thêm vào ảnh (VD: 'SALE 50%', 'Hotline: 0901234567'). Nếu không có, AI tự quyết định."
                        },
                        "page_context": {
                            "type": "string",
                            "description": "Tên page + ngành nghề để customize ảnh. VD: 'Everest Light Bắc Ninh - Vật liệu xây dựng'"
                        },
                        "style": {
                            "type": "string",
                            "description": "Phong cách: professional, modern, minimalist, colorful"
                        },
                        "size": {
                            "type": "string",
                            "description": "Kích thước: 1080x1080, 1200x628, 1080x1920"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Số lượng ảnh cần tạo (mặc định 3). Có thể từ 1-5 ảnh"
                        },
                        "business_type": {
                            "type": "string",
                            "description": "Ngành nghề/loại sản phẩm (từ lịch đăng). VD: 'Vật liệu xây dựng', 'Thời trang', 'F&B'"
                        },
                        "marketing_goals": {
                            "type": "string",
                            "description": "Mục tiêu marketing tổng thể (từ lịch đăng). VD: 'Tăng nhận diện thương hiệu', 'Ra mắt sản phẩm mới'"
                        }
                    },
                    "required": ["post_content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_agent_post",
                "description": """Lưu bài đăng hoàn chỉnh vào database.
CẦN KHI: Đã có content (từ generate_post_content) VÀ image (từ generate_post_image).
TRẢ VỀ: post_id, status, image_urls, layout, target_account.
QUAN TRỌNG: Tool này CHỈ LƯU, không generate. Phải gọi generate_post_content và generate_post_image trước.
LƯU Ý:
- Dùng image_ids để lưu TẤT CẢ hình ảnh từ generate_post_image (media_ids).
- Dùng target_account_id để GẮN bài với page cụ thể (để sau này đăng lên page đó).
LAYOUT: Lấy từ kết quả generate_post_image để hiển thị đúng bố cục Facebook.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Nội dung đã generate từ generate_post_content"
                        },
                        "image_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Danh sách media_ids từ generate_post_image (để lưu TẤT CẢ hình ảnh)"
                        },
                        "image_id": {
                            "type": "integer",
                            "description": "ID của 1 image (dùng image_ids thay thế để lưu nhiều ảnh)"
                        },
                        "target_account_id": {
                            "type": "integer",
                            "description": "ID của page sẽ đăng bài này (từ get_connected_accounts). Gắn để sau này tự động đăng lên đúng page."
                        },
                        "page_context": {
                            "type": "string",
                            "description": "Tên page để reference. VD: 'Everest Light Bắc Ninh'"
                        },
                        "layout": {
                            "type": "string",
                            "description": "Layout từ generate_post_image: single, two_square, one_large_two_small, four_square, two_large_three_small"
                        }
                    },
                    "required": ["content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_agent_post",
                "description": """Chỉnh sửa bài đăng Agent đã tạo.
CẦN KHI: User muốn sửa/edit bài đăng đã có (post_id).
TRẢ VỀ: post_id, content mới, hashtags mới.
LƯU Ý: Nếu regenerate_images=true, sẽ tạo ảnh mới (tốn thời gian).""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer",
                            "description": "ID bài đăng cần sửa (BẮT BUỘC)"
                        },
                        "new_content": {
                            "type": "string",
                            "description": "Nội dung mới cho bài đăng"
                        },
                        "new_hashtags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Hashtags mới, VD: ['#sale', '#khuyenmai']"
                        },
                        "regenerate_images": {
                            "type": "boolean",
                            "description": "Có tạo ảnh mới không (mặc định false)"
                        },
                        "image_count": {
                            "type": "integer",
                            "description": "Số ảnh cần tạo nếu regenerate_images=true (mặc định 3)"
                        }
                    },
                    "required": ["post_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "batch_edit_agent_posts",
                "description": """Chỉnh sửa NHIỀU bài đăng Agent cùng lúc.
CẦN KHI: User muốn sửa nhiều bài đăng, VD: "sửa bài #101, #102, #103: thêm hashtag..."
TRẢ VỀ: success_count, fail_count, results chi tiết.
LƯU Ý: Dùng edit_instruction để AI tự động sửa từng bài theo yêu cầu.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Danh sách ID các bài đăng cần sửa (BẮT BUỘC), VD: [101, 102, 103]"
                        },
                        "edit_instruction": {
                            "type": "string",
                            "description": "Hướng dẫn sửa đổi - AI sẽ áp dụng cho từng bài. VD: 'thêm hashtag #khuyenmai', 'viết lại ngắn gọn hơn'"
                        },
                        "new_hashtags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Hashtags mới áp dụng cho TẤT CẢ bài đăng"
                        },
                        "regenerate_images": {
                            "type": "boolean",
                            "description": "Có tạo ảnh mới cho tất cả bài không (mặc định false, tốn thời gian)"
                        },
                        "image_count": {
                            "type": "integer",
                            "description": "Số ảnh cần tạo nếu regenerate_images=true (mặc định 3)"
                        }
                    },
                    "required": ["post_ids"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_schedule",
                "description": """Phân tích lịch đăng, đưa ra insights và recommendations.
KHI NÀO DÙNG: User muốn phân tích, đánh giá lịch đăng.
INTENT: Chỉ XEM phân tích.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {
                            "type": "integer",
                            "description": "ID của schedule cần phân tích"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_connected_accounts",
                "description": """Lấy danh sách pages/tài khoản mạng xã hội đang kết nối từ database.
CẦN KHI: User hỏi về pages, tài khoản Facebook, kết nối.
TRẢ VỀ: name, platform, category, is_active, token_status.
THƯỜNG DÙNG CÙNG: generate_post_content (dùng name làm page_context), get_scheduled_posts (khi tạo bài).""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "platform": {
                            "type": "string",
                            "description": "Filter theo platform: facebook, instagram, zalo, tiktok (mặc định: tất cả)"
                        },
                        "active_only": {
                            "type": "boolean",
                            "description": "Chỉ lấy tài khoản đang active (mặc định: true)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_page_info",
                "description": """Cập nhật thông tin Facebook page.
CẦN KHI: User muốn sửa thông tin page như about, description, phone, website, emails.
TRẢ VỀ: success status, updated fields.
LƯU Ý: Cần account_id từ get_connected_accounts(). Chỉ cập nhật các trường được cung cấp.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "integer",
                            "description": "ID của page (từ get_connected_accounts)"
                        },
                        "about": {
                            "type": "string",
                            "description": "Giới thiệu ngắn về page (tối đa 255 ký tự)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Mô tả chi tiết về page"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Số điện thoại liên hệ"
                        },
                        "website": {
                            "type": "string",
                            "description": "Website URL"
                        },
                        "emails": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Danh sách email liên hệ"
                        }
                    },
                    "required": ["account_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_page_photo",
                "description": """Cập nhật ảnh đại diện hoặc ảnh bìa của Facebook page.
CẦN KHI: User muốn đổi avatar hoặc cover photo của page.
TRẢ VỀ: success status, photo info.
LƯU Ý: Dùng media_id từ thư viện ảnh hoặc image_url.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "integer",
                            "description": "ID của page (từ get_connected_accounts)"
                        },
                        "photo_type": {
                            "type": "string",
                            "description": "Loại ảnh: 'picture' (avatar) hoặc 'cover' (ảnh bìa)"
                        },
                        "media_id": {
                            "type": "integer",
                            "description": "ID của ảnh từ thư viện media"
                        },
                        "image_url": {
                            "type": "string",
                            "description": "URL ảnh (nếu không dùng media_id)"
                        }
                    },
                    "required": ["account_id", "photo_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "batch_update_pages_info",
                "description": """Cập nhật thông tin cho NHIỀU Facebook pages cùng lúc.
CẦN KHI: User muốn sửa thông tin cho nhiều pages (VD: "sửa description cho tất cả pages").
TRẢ VỀ: success_count, fail_count, results chi tiết.
LƯU Ý: Dùng account_ids từ get_connected_accounts().""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "account_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Danh sách ID các pages cần cập nhật"
                        },
                        "about": {
                            "type": "string",
                            "description": "Giới thiệu ngắn (áp dụng cho tất cả pages)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Mô tả chi tiết (áp dụng cho tất cả pages)"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Số điện thoại (áp dụng cho tất cả pages)"
                        },
                        "website": {
                            "type": "string",
                            "description": "Website URL (áp dụng cho tất cả pages)"
                        },
                        "emails": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Danh sách email (áp dụng cho tất cả pages)"
                        }
                    },
                    "required": ["account_ids"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_image",
                "description": """Chỉnh sửa hình ảnh bằng AI theo yêu cầu user.
CẦN KHI user muốn:
  - THÊM ELEMENT (logo, text, viền, sticker, watermark) → GIỮ NGUYÊN ảnh gốc, chỉ thêm element
  - SỬA KHÁC (đổi style, làm đẹp, xóa chi tiết, đổi màu, đổi nền...) → AI có thể thay đổi ảnh
  - Crop, resize, điều chỉnh màu sắc, độ sáng
  - Bất kỳ chỉnh sửa nào trên ảnh có sẵn
TRẢ VỀ: media_id, file_url của ảnh đã sửa.
QUAN TRỌNG:
  - Nếu user yêu cầu THÊM (logo, text, viền...) → prompt sẽ yêu cầu AI giữ nguyên ảnh gốc
  - Nếu user yêu cầu SỬA/THAY ĐỔI (style, màu, xóa...) → AI sẽ thay đổi theo yêu cầu
  - Nếu user gửi 2 ảnh: 1 là ảnh gốc, 1 là logo/element → dùng source_image_data và overlay_image_data
  - Nếu user yêu cầu "thêm logo từ settings", "dùng logo Fugu" → set use_brand_settings=true
KHÁC VỚI generate_post_image: Tool này EDIT ảnh có sẵn, không tạo ảnh hoàn toàn mới từ prompt.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_image_data": {
                            "type": "string",
                            "description": "Base64 ảnh GỐC cần sửa (từ file user gửi)"
                        },
                        "source_media_id": {
                            "type": "integer",
                            "description": "ID ảnh gốc từ thư viện media"
                        },
                        "agent_post_id": {
                            "type": "integer",
                            "description": "ID bài đăng agent - lấy ảnh từ bài đó để sửa"
                        },
                        "agent_post_image_index": {
                            "type": "integer",
                            "description": "Index ảnh trong bài đăng (0 = ảnh đầu). Mặc định 0"
                        },
                        "overlay_image_data": {
                            "type": "string",
                            "description": "Base64 ảnh phụ (logo, sticker, watermark...) mà user gửi để thêm vào ảnh gốc"
                        },
                        "overlay_media_id": {
                            "type": "integer",
                            "description": "ID ảnh phụ (logo, sticker...) từ thư viện media"
                        },
                        "text_to_add": {
                            "type": "string",
                            "description": "Text cần thêm vào ảnh (VD: 'Everest Light', 'Hotline: 0901234567', 'SALE 50%')"
                        },
                        "edit_instruction": {
                            "type": "string",
                            "description": "Mô tả chi tiết yêu cầu chỉnh sửa. VD: 'thêm logo góc phải dưới, kích thước 15%', 'thêm viền vàng 10px', 'thêm text Everest Light màu trắng ở dưới', 'tăng độ sáng', 'crop vuông'"
                        },
                        "update_post": {
                            "type": "boolean",
                            "description": "Nếu sửa ảnh từ bài đăng, cập nhật lại bài đăng không (mặc định true)"
                        },
                        "use_brand_settings": {
                            "type": "boolean",
                            "description": "Dùng logo từ Settings Fugu (vị trí, kích thước theo cài đặt). Set true khi user nói 'thêm logo từ settings', 'dùng logo Fugu', 'thêm logo đã cài đặt'"
                        },
                        "target_size": {
                            "type": "string",
                            "description": "Kích thước output (WIDTHxHEIGHT). VD: '2048x635', '1920x1080'. Nếu không truyền sẽ GIỮ NGUYÊN kích thước ảnh gốc. QUAN TRỌNG: Khi user chỉ định kích thước cụ thể, PHẢI truyền target_size!"
                        }
                    },
                    "required": ["edit_instruction"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "batch_create_posts",
                "description": """Tạo NHIỀU bài đăng HOÀN CHỈNH (content + ảnh) từ 1 nội dung gốc cho nhiều pages cùng lúc.
CẦN KHI: User muốn tạo cùng 1 nội dung cho nhiều pages.
VD: "dùng nội dung hôm nay tạo bài cho tất cả pages", "tạo bài khuyến mãi cho 10 pages"
TRẢ VỀ: success_count, fail_count, created_posts với post_ids và image URLs.
CÁCH HOẠT ĐỘNG:
- AI viết lại nội dung TỰ NHIÊN cho từng page (không chỉ thay text)
- Mỗi bài được gắn target_account để biết đăng lên page nào

⚠️⚠️⚠️ QUAN TRỌNG VỀ ẢNH:
1. NẾU CÓ ẢNH CÓ SẴN (user đã tạo ảnh trước hoặc dùng ảnh từ thư viện):
   → generate_images=FALSE + shared_image_ids=[media_ids]
   → KHÔNG TẠO ẢNH MỚI, chỉ dùng ảnh có sẵn

2. NẾU CHƯA CÓ ẢNH và cần tạo mới:
   → generate_images=TRUE (hoặc không truyền, mặc định true)
   → Sẽ tạo ảnh riêng cho mỗi page

⚠️ LƯU Ý: Nếu có business_type và marketing_goals từ lịch đăng, PHẢI truyền vào để ảnh được tối ưu cho ngành nghề.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_content": {
                            "type": "string",
                            "description": "Nội dung gốc cần adapt cho các pages"
                        },
                        "account_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Danh sách account_ids từ get_connected_accounts"
                        },
                        "generate_images": {
                            "type": "boolean",
                            "description": "Có tạo ảnh MỚI không. ⚠️ BẮT BUỘC set FALSE nếu dùng shared_image_ids. Mặc định: true"
                        },
                        "image_count": {
                            "type": "integer",
                            "description": "Số ảnh tạo cho mỗi bài nếu generate_images=true (mặc định 3)"
                        },
                        "shared_image_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Danh sách media_id ẢNH CÓ SẴN để dùng chung cho tất cả bài. ⚠️ Khi dùng param này, PHẢI set generate_images=false!"
                        },
                        "shared_image_layout": {
                            "type": "string",
                            "description": "Bố cục hiển thị khi dùng shared images: 'single', 'two_square', 'one_large_two_small', 'four_square', 'grid'. Nếu không chỉ định, tự động theo số ảnh"
                        },
                        "adaptation_style": {
                            "type": "string",
                            "description": "Cách adapt: 'subtle' (nhẹ nhàng), 'natural' (tự nhiên), 'localized' (theo địa phương). Mặc định: 'natural'"
                        },
                        "business_type": {
                            "type": "string",
                            "description": "Ngành nghề/loại sản phẩm (từ lịch đăng). VD: 'Vật liệu xây dựng', 'Thời trang', 'F&B'"
                        },
                        "marketing_goals": {
                            "type": "string",
                            "description": "Mục tiêu marketing tổng thể (từ lịch đăng). VD: 'Tăng nhận diện thương hiệu', 'Ra mắt sản phẩm mới'"
                        }
                    },
                    "required": ["source_content", "account_ids"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "batch_add_text_to_images",
                "description": """Thêm text vào NHIỀU ảnh với cùng style/font/màu nhất quán.
CẦN KHI: User muốn thêm text khác nhau vào nhiều ảnh nhưng cùng font/màu.
VD: "thêm text 'A', 'B', 'C' vào 3 ảnh với font giống nhau"
TRẢ VỀ: success_count, fail_count, results với media_ids và file_urls.
STYLE CÓ SẴN:
- modern: font hiện đại sans-serif, clean, shadow nhẹ
- elegant: font thanh lịch serif, gradient subtle
- bold: font đậm impact, viền trắng/đen nổi bật
- minimal: font đơn giản, không hiệu ứng
- neon: hiệu ứng neon glow sáng
POSITION: top_left, top_right, bottom_left, bottom_right, center""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_text_pairs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "media_id": {"type": "integer"},
                                    "text": {"type": "string"}
                                }
                            },
                            "description": "Danh sách cặp {media_id, text}. VD: [{media_id: 100, text: 'Sản phẩm A'}, {media_id: 101, text: 'Sản phẩm B'}]"
                        },
                        "text_position": {
                            "type": "string",
                            "description": "Vị trí text: top_left, top_right, bottom_left, bottom_right, center. Mặc định: bottom_left"
                        },
                        "text_style": {
                            "type": "string",
                            "description": "Style text: modern, elegant, bold, minimal, neon. Mặc định: modern"
                        },
                        "text_color": {
                            "type": "string",
                            "description": "Màu text (hex). VD: '#FFFFFF', '#FF0000'. Nếu không chỉ định, AI tự chọn màu phù hợp"
                        },
                        "font_size": {
                            "type": "string",
                            "description": "Kích thước font: small, medium, large. Mặc định: medium"
                        },
                        "use_brand_settings": {
                            "type": "boolean",
                            "description": "Dùng thông tin từ Settings Fugu (hotline, slogan) nếu có"
                        }
                    },
                    "required": ["image_text_pairs"]
                }
            }
        }
    ]
