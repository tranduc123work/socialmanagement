"""
LLM Agent Service - Gemini-powered Intelligent Agent
"""
import os
import json
from typing import Dict, Any, List, Optional
from django.conf import settings
import google.generativeai as genai


class GeminiAgent:
    """
    Intelligent Agent sử dụng Gemini LLM
    Agent có thể:
    - Chat với user
    - Phân tích hệ thống
    - Tạo content và image
    - Thực hiện tasks tự động
    """

    def __init__(self):
        # Configure Gemini API
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            api_key = os.environ.get('GEMINI_API_KEY')

        if api_key:
            genai.configure(api_key=api_key)

        # Get model name from settings/env
        model_name = getattr(settings, 'GEMINI_AGENT_MODEL', None)
        if not model_name:
            model_name = os.environ.get('GEMINI_AGENT_MODEL', 'gemini-2.0-flash-exp')

        # System prompt - Direct action style (merged from 841fe98)
        self.system_prompt = """
Bạn là một AI Agent thông minh tên là "Agent Dashboard".

VAI TRÒ CỦA BẠN:
- Bạn là trợ lý kỹ thuật có khả năng gọi các API tools để thực hiện tasks
- Bạn hiểu user intent và quyết định gọi tools nào phù hợp
- Bạn có thể gọi NHIỀU TOOLS CÙNG LÚC để hoàn thành task nhanh chóng
- Bạn KHÔNG cần hỏi permission - hãy tự động thực hiện ngay

CÁC TOOLS BẠN CÓ THỂ GỌI:

1. get_current_datetime()
   - Lấy thông tin thời gian hiện tại
   - Trả về: ngày hôm nay, ngày mai, giờ, thứ trong tuần

2. get_scheduled_posts(status, limit, days_ahead, start_date, end_date)
   - Lấy danh sách lịch đăng đã schedule
   - Trả về: business_type, marketing_goals, full_content, goal, content_type

3. get_connected_accounts(platform, active_only)
   - Lấy danh sách pages/tài khoản đang kết nối
   - Trả về: id, name, platform, category

4. get_agent_posts(limit, status)
   - Lấy danh sách bài đăng do Agent đã tạo

5. get_system_stats()
   - Lấy thống kê tổng quan hệ thống

6. generate_post_content(draft_content, page_context, topic, goal, tone)
   - Tạo/chau chuốt nội dung bài đăng
   - Input: draft_content (nội dung nháp) HOẶC topic (chủ đề mới)
   - Output: content hoàn chỉnh 150+ từ

7. generate_post_image(post_content, page_context, style, size)
   - Tạo hình ảnh từ content bài đăng
   - Input: post_content (BẮT BUỘC - từ generate_post_content)
   - Output: media_ids, images với URLs

8. save_agent_post(content, image_id, page_context)
   - LƯU bài đăng vào database
   - Input: content + image_id (từ generate_post_image)
   - ⚠️ CHỈ LƯU - không generate. PHẢI gọi generate trước!

9. analyze_schedule(schedule_id)
   - Phân tích lịch đăng

CÁCH BẠN HOẠT ĐỘNG:

✅ Khi user hỏi về lịch đăng với thời gian:
   → GỌI: get_current_datetime() + get_scheduled_posts()
   → TRẢ LỜI: Hiển thị danh sách

✅ Khi user hỏi về pages:
   → GỌI: get_connected_accounts()
   → TRẢ LỜI: Hiển thị danh sách pages

✅ Khi user yêu cầu TẠO BÀI từ topic:
   → BƯỚC 1: generate_post_content(topic="...")
   → BƯỚC 2: generate_post_image(post_content=<kết quả bước 1>)
   → BƯỚC 3: save_agent_post(content=..., image_id=...)
   → TRẢ LỜI: "Đã tạo bài đăng #X!"

✅ Khi user yêu cầu TẠO BÀI từ lịch đăng:
   → BƯỚC 1: get_current_datetime() + get_scheduled_posts() (lấy draft)
   → BƯỚC 2: generate_post_content(draft_content=<full_content từ lịch>)
   → BƯỚC 3: generate_post_image(post_content=...)
   → BƯỚC 4: save_agent_post(content=..., image_id=...)

✅ Khi user yêu cầu TẠO BÀI cho NHIỀU PAGES:
   → BƯỚC 1: get_scheduled_posts() + get_connected_accounts()
   → BƯỚC 2: LẶP LẠI CHO MỖI PAGE:
      • generate_post_content(draft_content=..., page_context="Tên Page")
      • generate_post_image(post_content=..., page_context="Tên Page")
      • save_agent_post(content=..., image_id=..., page_context="Tên Page")

✅ Khi user nói "pages 1", "pages đầu tiên":
   → GỌI get_connected_accounts() để xác định pages nào
   → KHÔNG hỏi lại user

NGUYÊN TẮC QUAN TRỌNG:
- GỌI TOOLS NGAY - KHÔNG HỎI "Bạn có muốn tôi...?"
- CÓ THỂ GỌI NHIỀU TOOLS CÙNG LÚC nếu độc lập
- CHỈ BÁO KẾT QUẢ CUỐI - không giải thích từng bước
- ⛔ KHÔNG HALLUCINATE - Chỉ nói "đã tạo bài #X" SAU KHI save_agent_post thành công
- ⚠️ Workflow tạo bài BẮT BUỘC: generate_post_content → generate_post_image → save_agent_post

VÍ DỤ 1 - Tạo bài từ topic:
User: "Tạo bài đăng về khuyến mãi cuối năm"
→ GỌI: generate_post_content(topic="khuyến mãi cuối năm")
→ GỌI: generate_post_image(post_content=<kết quả>)
→ GỌI: save_agent_post(content=..., image_id=123)
→ TRẢ LỜI: "Đã tạo bài đăng #45 về khuyến mãi cuối năm!"

VÍ DỤ 2 - Tạo bài từ lịch:
User: "Tạo bài đăng từ nội dung hôm nay"
→ GỌI: get_current_datetime() + get_scheduled_posts(days_ahead=0)
→ GỌI: generate_post_content(draft_content=<full_content>)
→ GỌI: generate_post_image(post_content=...)
→ GỌI: save_agent_post(...)
→ TRẢ LỜI: "Đã tạo bài đăng #46!"

VÍ DỤ 3 - Tạo cho nhiều pages:
User: "Tạo bài từ nội dung hôm nay cho 7 pages"
→ GỌI: get_current_datetime() + get_scheduled_posts() + get_connected_accounts()
→ LẶP 7 LẦN (mỗi page):
   • generate_post_content(draft_content=..., page_context="Page A")
   • generate_post_image(post_content=..., page_context="Page A")
   • save_agent_post(content=..., image_id=X, page_context="Page A")
→ TRẢ LỜI: "Đã tạo 7 bài đăng:
   1. Page A - Bài #47
   2. Page B - Bài #48
   ..."

VÍ DỤ 4 - Pages 1:
User: "Tạo bài cho pages 1"
→ GỌI: get_connected_accounts() (để biết pages 1 là gì)
→ GỌI: get_scheduled_posts() (lấy nội dung)
→ Tiếp tục workflow tạo bài...

NGÔN NGỮ:
- Chat bằng tiếng Việt tự nhiên, thân thiện
- Không dùng markdown (*, **, #)
"""

        # Initialize model with function calling (model from .env)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=self._define_tools(),
            system_instruction=self.system_prompt
        )

        # Track token usage
        self.last_token_usage = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        }

    def count_tokens(self, text: str) -> int:
        """
        Count tokens trong text sử dụng Gemini API

        Args:
            text: Text cần đếm tokens

        Returns:
            Số lượng tokens
        """
        try:
            result = self.model.count_tokens(text)
            return result.total_tokens
        except Exception:
            # Fallback: estimate ~4 chars per token
            return len(text) // 4

    def _define_tools(self) -> List[Dict]:
        """
        Define tools (functions) mà Agent có thể sử dụng
        Format theo Gemini API requirements (UPPERCASE types)
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
                "name": "get_scheduled_posts",
                "description": """Lấy danh sách lịch đăng bài đã schedule từ database.
CẦN KHI: User hỏi về lịch đăng, schedule, bài đã lên kế hoạch.
TRẢ VỀ: scheduled_date, business_type, full_content, goal, content_type.
THƯỜNG DÙNG CÙNG: get_current_datetime (khi có từ thời gian), get_connected_accounts (khi tạo bài cho pages).""",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "status": {
                            "type": "STRING",
                            "description": "Filter: draft, approved, scheduled, published"
                        },
                        "limit": {
                            "type": "INTEGER",
                            "description": "Số lượng, mặc định 10"
                        },
                        "days_ahead": {
                            "type": "INTEGER",
                            "description": "Số ngày từ hôm nay (VD: 7 = 7 ngày tới)"
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
TRẢ VỀ: content hoàn chỉnh (150+ từ, tự nhiên).
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
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "generate_post_image",
                "description": """Tạo hình ảnh bằng AI phù hợp với content bài đăng.
CẦN KHI: Đã có content hoàn chỉnh (từ generate_post_content) và cần tạo ảnh.
TRẢ VỀ: image_id, image_url.
SAU KHI GỌI: Gọi save_agent_post với content và image_id để lưu.""",
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
                        }
                    },
                    "required": ["post_content"]
                }
            },
            {
                "name": "save_agent_post",
                "description": """Lưu bài đăng hoàn chỉnh vào database.
CẦN KHI: Đã có content (từ generate_post_content) VÀ image (từ generate_post_image).
TRẢ VỀ: post_id, status, image_urls.
QUAN TRỌNG: Tool này CHỈ LƯU, không generate. Phải gọi generate_post_content và generate_post_image trước.""",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "content": {
                            "type": "STRING",
                            "description": "Nội dung đã generate từ generate_post_content"
                        },
                        "image_id": {
                            "type": "INTEGER",
                            "description": "ID của image đã tạo từ generate_post_image"
                        },
                        "page_context": {
                            "type": "STRING",
                            "description": "Tên page để reference. VD: 'Everest Light Bắc Ninh'"
                        }
                    },
                    "required": ["content"]
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
            }
        ]

    def chat(self, user_message: str, user_id: int, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Chat với user và tự động thực hiện tasks nếu cần

        Args:
            user_message: Tin nhắn từ user
            user_id: ID của user
            conversation_history: Lịch sử hội thoại trước đó

        Returns:
            {
                'agent_response': str,
                'function_calls': List[Dict],
                'needs_tool_execution': bool
            }
        """
        try:
            # Build conversation context
            chat_history = []
            if conversation_history:
                for msg in conversation_history:
                    role = msg['role']
                    content = msg['message']
                    if role == 'user':
                        chat_history.append({'role': 'user', 'parts': [content]})
                    elif role == 'agent':
                        chat_history.append({'role': 'model', 'parts': [content]})

            # Start chat session
            chat = self.model.start_chat(history=chat_history)

            # Count input tokens (user message)
            input_tokens = self.count_tokens(user_message)

            # Add tokens from history
            for msg in chat_history:
                if msg.get('parts'):
                    for part in msg['parts']:
                        input_tokens += self.count_tokens(str(part))

            # Send user message
            response = chat.send_message(user_message)

            # Count output tokens from response
            output_tokens = 0

            # Extract function calls if any
            function_calls = []
            response_text = ""

            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # Check for function call
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            # Convert args to JSON-serializable dict
                            args_dict = {}
                            if fc.args:
                                # Manually convert each arg to primitive types
                                for key in fc.args:
                                    value = fc.args[key]
                                    # Convert to primitive Python types
                                    if isinstance(value, (str, int, float, bool, type(None))):
                                        args_dict[key] = value
                                    elif isinstance(value, (list, tuple)):
                                        args_dict[key] = list(value)
                                    else:
                                        # For complex types, try to convert to string
                                        try:
                                            args_dict[key] = str(value)
                                        except:
                                            args_dict[key] = None

                            function_calls.append({
                                'name': fc.name,
                                'args': args_dict
                            })
                        # Check for text
                        elif hasattr(part, 'text') and part.text:
                            response_text += part.text
                            output_tokens += self.count_tokens(part.text)

            # Store token usage
            self.last_token_usage = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens
            }

            return {
                'agent_response': response_text,
                'function_calls': function_calls,
                'needs_tool_execution': len(function_calls) > 0,
                'chat_session': chat,  # Return chat session for multi-turn conversation
                'raw_response': response,
                'token_usage': self.last_token_usage
            }

        except Exception as e:
            return {
                'agent_response': f"Xin lỗi, tôi gặp lỗi: {str(e)}",
                'function_calls': [],
                'needs_tool_execution': False,
                'error': str(e),
                'token_usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
            }

    def continue_with_tool_results(self, chat_session, function_results: List[Dict], user=None) -> Dict[str, Any]:
        """
        Tiếp tục conversation sau khi execute tools

        Args:
            chat_session: Gemini chat session
            function_results: Kết quả từ các function calls
            user: User object for executing additional tools

        Returns:
            {
                'response': str,
                'token_usage': {'input_tokens': int, 'output_tokens': int, 'total_tokens': int}
            }
        """
        try:
            # Track tokens for this turn
            input_tokens = 0
            output_tokens = 0

            # Create function response parts
            parts = []
            for result in function_results:
                # Count tokens from function results
                result_str = str(result.get('result', ''))
                input_tokens += self.count_tokens(result_str)

                parts.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=result['function_name'],
                            response={'result': result['result']}
                        )
                    )
                )

            # Send function results back to model
            response = chat_session.send_message(
                genai.protos.Content(parts=parts)
            )

            # Check for errors (malformed function call, etc)
            import logging
            logger = logging.getLogger(__name__)

            if response.candidates and response.candidates[0].finish_reason:
                finish_reason = str(response.candidates[0].finish_reason)
                if 'MALFORMED' in finish_reason or 'ERROR' in finish_reason:
                    logger.error(f"[AGENT] Model returned error: {finish_reason}")
                    logger.error(f"[AGENT] Response content: {response.candidates[0].content if response.candidates[0].content else 'None'}")
                    return {
                        'response': "Đã hoàn thành xử lý các bước trước đó.",
                        'token_usage': {'input_tokens': input_tokens, 'output_tokens': 0, 'total_tokens': input_tokens}
                    }

            # Check if model wants to call MORE functions
            if response.candidates and response.candidates[0].content:
                parts_list = response.candidates[0].content.parts

                # Check for more function calls
                more_function_calls = []
                for part in parts_list:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        args_dict = {}
                        if fc.args:
                            for key in fc.args:
                                value = fc.args[key]
                                # Convert to primitive Python types (same logic as chat method)
                                if isinstance(value, (str, int, float, bool, type(None))):
                                    args_dict[key] = value
                                elif isinstance(value, (list, tuple)):
                                    args_dict[key] = list(value)
                                else:
                                    try:
                                        args_dict[key] = str(value)
                                    except:
                                        args_dict[key] = None

                        more_function_calls.append({
                            'name': fc.name,
                            'args': args_dict
                        })

                # If there are more function calls, execute them too!
                if more_function_calls:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"[AGENT] Model wants to call {len(more_function_calls)} more functions: {[fc['name'] for fc in more_function_calls]}")

                    # Check if we have user context
                    if not user:
                        logger.error("[AGENT] Cannot execute additional tools - user context missing")
                        return {
                            'response': "Đã xử lý xong phần đầu, nhưng không thể tiếp tục.",
                            'token_usage': {'input_tokens': input_tokens, 'output_tokens': 0, 'total_tokens': input_tokens}
                        }

                    # Execute additional tools
                    from .services import AgentToolExecutor

                    additional_results = []
                    for fc in more_function_calls:
                        logger.info(f"[AGENT] Executing additional tool: {fc['name']}")
                        result = AgentToolExecutor.execute_tool(
                            function_name=fc['name'],
                            arguments=fc['args'],
                            user=user
                        )
                        additional_results.append({
                            'function_name': fc['name'],
                            'result': result
                        })

                    # RECURSIVELY continue with additional tool results
                    recursive_result = self.continue_with_tool_results(
                        chat_session=chat_session,
                        function_results=additional_results,
                        user=user
                    )
                    # Add current input tokens to recursive result
                    recursive_result['token_usage']['input_tokens'] += input_tokens
                    recursive_result['token_usage']['total_tokens'] += input_tokens
                    return recursive_result

                # Extract text response and count output tokens
                text_parts = []
                for p in parts_list:
                    if hasattr(p, 'text') and p.text:
                        text_parts.append(p.text)
                        output_tokens += self.count_tokens(p.text)

                response_text = '\n'.join(text_parts) if text_parts else "Đã xử lý xong!"

                # Update stored token usage
                self.last_token_usage = {
                    'input_tokens': self.last_token_usage.get('input_tokens', 0) + input_tokens,
                    'output_tokens': self.last_token_usage.get('output_tokens', 0) + output_tokens,
                    'total_tokens': self.last_token_usage.get('input_tokens', 0) + input_tokens + self.last_token_usage.get('output_tokens', 0) + output_tokens
                }

                return {
                    'response': response_text,
                    'token_usage': self.last_token_usage
                }

            return {
                'response': "Đã xử lý xong!",
                'token_usage': self.last_token_usage
            }

        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"[AGENT] Error in continue_with_tool_results: {str(e)}")
            logger.error(f"[AGENT] Traceback: {traceback.format_exc()}")
            return {
                'response': f"Lỗi khi xử lý: {str(e)}",
                'token_usage': self.last_token_usage
            }

    def generate_post_automatically(
        self,
        business_type: str,
        topic: str,
        goal: str = 'engagement',
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        Tự động generate một post hoàn chỉnh (content + image)

        Args:
            business_type: Loại hình kinh doanh
            topic: Chủ đề
            goal: Mục tiêu
            user_id: ID của user

        Returns:
            {
                'content': str,
                'hashtags': List[str],
                'image_url': str,
                'reasoning': str
            }
        """
        prompt = f"""
Hãy tạo một bài đăng Facebook hoàn chỉnh với thông tin sau:

Business: {business_type}
Topic: {topic}
Goal: {goal}

Yêu cầu:
1. Tạo content hấp dẫn, có hook mạnh
2. Tạo hình ảnh phù hợp
3. Include hashtags relevant

Hãy sử dụng tools để tạo post hoàn chỉnh!
"""

        # Start chat
        chat = self.model.start_chat()
        response = chat.send_message(prompt)

        # Agent sẽ tự động gọi tools
        # Return response để service layer xử lý
        return {
            'chat_session': chat,
            'initial_response': response
        }


# Singleton instance
_agent_instance = None


def get_agent() -> GeminiAgent:
    """Get or create agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = GeminiAgent()
    return _agent_instance


def reset_agent():
    """Reset agent instance to reload system prompt"""
    global _agent_instance
    _agent_instance = None
