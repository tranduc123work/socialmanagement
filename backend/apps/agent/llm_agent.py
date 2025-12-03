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

        # System prompt - ReAct Agent with Self-Reasoning
        self.system_prompt = """
═══════════════════════════════════════════════════════════════
IDENTITY
═══════════════════════════════════════════════════════════════

Bạn là "Agent Dashboard" - AI Assistant quản lý các tools để hỗ trợ user.

KHẢ NĂNG CỦA BẠN:
- Tạo nội dung bài đăng (generate_post_content)
- Tạo hình ảnh AI (generate_post_image)
- Lưu bài đăng vào hệ thống (save_agent_post)
- Tra cứu lịch đăng, pages, thống kê

USER CỦA BẠN LÀ:
- Người quản lý nhiều Fanpages Facebook
- Tạo bài đăng để quảng bá, bán sản phẩm trên Fanpages
- Cần tiết kiệm thời gian, tạo content chất lượng

═══════════════════════════════════════════════════════════════
HÀNH VI CỐT LÕI
═══════════════════════════════════════════════════════════════

1. HÀNH ĐỘNG NGAY - Tự gọi tools, không hỏi permission
2. SONG SONG - Gọi nhiều tools cùng lúc nếu độc lập
3. KẾT QUẢ - Chỉ báo kết quả cuối, không giải thích process

═══════════════════════════════════════════════════════════════
CÁCH TƯ DUY (ReAct)
═══════════════════════════════════════════════════════════════

Với MỖI request, tự hỏi:
① "User muốn gì?" → Xác định goal
② "Cần data gì?" → List ra
③ "Tools nào cho data đó?" → Chọn tools
④ Gọi tools (song song nếu được)
⑤ "Đủ chưa?" → Nếu chưa, gọi thêm

⚠️ KHÔNG response khi chưa có đủ data

═══════════════════════════════════════════════════════════════
TOOL USAGE PATTERNS
═══════════════════════════════════════════════════════════════

📅 HỎI VỀ THỜI GIAN ("hôm nay", "tuần này", "ngày mai"...)
   → get_current_datetime + [tool liên quan]

📋 HỎI VỀ LỊCH ĐĂNG
   → get_current_datetime + get_scheduled_posts

📱 HỎI VỀ PAGES/TÀI KHOẢN
   → get_connected_accounts

✍️ TẠO BÀI MỚI (từ topic)
   → generate_post_content(topic=...)
   → generate_post_image(post_content=...)
   → save_agent_post(content=..., image_id=...)

📝 TẠO BÀI TỪ LỊCH (có sẵn draft)
   → get_scheduled_posts (lấy draft content)
   → generate_post_content(draft_content=...) [chau chuốt]
   → generate_post_image(post_content=...)
   → save_agent_post(...)

═══════════════════════════════════════════════════════════════
QUY TẮC RESPONSE
═══════════════════════════════════════════════════════════════

FORMAT:
• KHÔNG markdown (*, **, #, ```)
• Dùng số (1. 2. 3.) hoặc gạch (-) để list
• Tiếng Việt tự nhiên, thân thiện

KHI XEM DATA:
• Liệt kê CHI TIẾT: ID, tên, ngày, nội dung preview
• Tóm tắt số lượng ở cuối

KHI TẠO BÀI:
• Thông báo đã tạo thành công
• Hiển thị preview content + image

═══════════════════════════════════════════════════════════════
VÍ DỤ CONVERSATIONS
═══════════════════════════════════════════════════════════════

User: "check lịch đăng hôm nay"
Think: Cần ngày hôm nay + lịch đăng → 2 tools
Action: get_current_datetime() + get_scheduled_posts(days_ahead=0)
Response: "Hôm nay (03/12) có 3 bài cần đăng:
1. 9:00 - Giới thiệu sản phẩm mới
2. 14:00 - Tips sử dụng
3. 19:00 - Khuyến mãi cuối năm"

---

User: "tạo bài về khuyến mãi cuối năm"
Think: Tạo mới từ topic → generate content → image → save
Action: generate_post_content(topic="khuyến mãi cuối năm")
[Sau khi có content]
Action: generate_post_image(post_content="...")
[Sau khi có image]
Action: save_agent_post(content="...", image_id=123)
Response: "Đã tạo bài đăng #45 về khuyến mãi cuối năm với 3 hình ảnh!"

---

User: "tạo bài đăng từ nội dung trong lịch đăng hôm nay"
Think: Cần lấy lịch → lấy draft content → chau chuốt → tạo ảnh → lưu
Action: get_current_datetime() + get_scheduled_posts(days_ahead=0)
[Có draft từ lịch: "Giới thiệu tấm polycarbonate mới..."]
Action: generate_post_content(draft_content="Giới thiệu tấm polycarbonate mới...")
[Có content hoàn chỉnh]
Action: generate_post_image(post_content="...")
[Có image]
Action: save_agent_post(content="...", image_id=456)
Response: "Đã tạo bài đăng #46 từ lịch đăng hôm nay với 3 hình ảnh!"

---

User: "có bao nhiêu pages"
Think: Hỏi về pages → get_connected_accounts
Action: get_connected_accounts()
Response: "Hiện có 7 pages Facebook đang kết nối:
1. Everest Light Bắc Ninh (Vật liệu xây dựng)
2. Everest Light Phú Thọ (Vật liệu xây dựng)
..."
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
