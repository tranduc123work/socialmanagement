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

        # System prompt - Principle-based Tool Manager
        self.system_prompt = """
Bạn là "Agent Dashboard" - AI Agent có khả năng sử dụng các tools để thực hiện tasks.

═══════════════════════════════════════════════════════════════
NGUYÊN TẮC CỐT LÕI
═══════════════════════════════════════════════════════════════

1. HÀNH ĐỘNG NGAY - Không hỏi permission, tự động gọi tools phù hợp
2. NHIỀU TOOLS CÙNG LÚC - Gọi song song nếu các tools độc lập
3. KẾT QUẢ CUỐI - Chỉ báo kết quả, không giải thích từng bước

═══════════════════════════════════════════════════════════════
PHÂN BIỆT INTENT (QUAN TRỌNG)
═══════════════════════════════════════════════════════════════

📖 XEM/ĐỌC (chỉ lấy data, không lưu gì):
   Từ khóa: "xem", "check", "có gì", "list", "show", "cho biết"
   → Gọi tools để query data
   → Hiển thị kết quả
   → KHÔNG gọi tools tạo/lưu

✏️ TẠO/LƯU (phải persist kết quả):
   Từ khóa: "tạo", "viết", "generate", "làm"
   → Gọi tools để generate/create
   → BẮT BUỘC gọi tool lưu kết quả (create_agent_post)
   → Nếu chưa lưu = task CHƯA HOÀN THÀNH

⏰ THỜI GIAN TƯƠNG ĐỐI:
   "ngày mai", "hôm nay", "tuần sau"
   → Gọi get_current_datetime() TRƯỚC để có ngày cụ thể
   → Rồi mới gọi các tools khác

═══════════════════════════════════════════════════════════════
CÁC TOOLS CÓ SẴN (xem tool descriptions để biết chi tiết)
═══════════════════════════════════════════════════════════════

• get_current_datetime - Lấy ngày giờ hiện tại
• get_agent_posts - Xem posts đã tạo
• get_scheduled_posts - Xem lịch đăng (có full_content để dùng tạo bài)
• get_system_stats - Thống kê hệ thống
• get_connected_accounts - Xem tài khoản/pages Facebook đang kết nối (có category để tạo content phù hợp)
• generate_post_content - Tạo nội dung bài đăng bằng AI
• generate_post_image - Tạo ảnh bằng AI
• create_agent_post - LƯU bài đăng vào database (bắt buộc khi TẠO)
• analyze_schedule - Phân tích lịch đăng

═══════════════════════════════════════════════════════════════
VÍ DỤ
═══════════════════════════════════════════════════════════════

📖 "Ngày 4/12 có bài gì?" (XEM)
→ get_scheduled_posts → Hiển thị → XONG

✏️ "Tạo bài về quán café" (TẠO MỚI)
→ generate_post_content → create_agent_post → "✅ Đã tạo!"

✏️ "Tạo bài với nội dung ngày 4/12" (TẠO TỪ LỊCH)
→ get_scheduled_posts (lấy full_content)
→ create_agent_post (lưu) → "✅ Đã tạo!"

═══════════════════════════════════════════════════════════════
NGÔN NGỮ: Tiếng Việt tự nhiên, thân thiện
═══════════════════════════════════════════════════════════════
"""

        # Initialize model with function calling (model from .env)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=self._define_tools(),
            system_instruction=self.system_prompt
        )

    def _define_tools(self) -> List[Dict]:
        """
        Define tools (functions) mà Agent có thể sử dụng
        Format theo Gemini API requirements (UPPERCASE types)
        """
        return [
            {
                "name": "get_current_datetime",
                "description": """Lấy thông tin thời gian hiện tại.
KHI NÀO DÙNG: Khi user nói "ngày mai", "hôm nay", "tuần sau" - gọi tool này TRƯỚC để có ngày cụ thể.
TRẢ VỀ: today, tomorrow, day_of_week, current_time, year, month.""",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "get_agent_posts",
                "description": """Xem danh sách bài đăng đã được Agent tạo trước đó.
KHI NÀO DÙNG: User muốn xem lại posts đã tạo.
INTENT: Chỉ XEM, không tạo mới.""",
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
                "description": """Lấy danh sách lịch đăng đã schedule.
KHI NÀO DÙNG: User muốn xem lịch đăng, hoặc cần lấy content để tạo bài mới.
TRẢ VỀ: business_type, marketing_goals, full_content (có thể dùng để tạo bài), goal, content_type.
LƯU Ý: Nếu user muốn TẠO bài từ lịch → sau khi gọi tool này, PHẢI gọi create_agent_post với full_content.""",
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
                "description": """Tạo nội dung bài đăng bằng AI (150+ từ, tự nhiên như người viết).
KHI NÀO DÙNG: User muốn TẠO bài đăng mới với chủ đề cụ thể.
SAU KHI GỌI: PHẢI gọi create_agent_post để lưu content vào database.""",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "business_type": {
                            "type": "STRING",
                            "description": "Loại hình kinh doanh"
                        },
                        "topic": {
                            "type": "STRING",
                            "description": "Chủ đề bài đăng"
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
                    "required": ["business_type", "topic", "goal"]
                }
            },
            {
                "name": "generate_post_image",
                "description": """Tạo hình ảnh bằng AI từ mô tả text.
KHI NÀO DÙNG: User muốn tạo ảnh riêng, hoặc cần ảnh cho bài đăng.
TRẢ VỀ: image_id, image_url.""",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "description": {
                            "type": "STRING",
                            "description": "Mô tả hình ảnh cần tạo"
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
                    "required": ["description"]
                }
            },
            {
                "name": "create_agent_post",
                "description": """LƯU bài đăng vào database (QUAN TRỌNG).
KHI NÀO DÙNG: Sau khi có content (từ generate_post_content hoặc full_content từ get_scheduled_posts).
BẮT BUỘC: Nếu user nói "tạo", "viết", "generate" bài → PHẢI gọi tool này để lưu.
KHÔNG GỌI = BÀI ĐĂNG CHƯA ĐƯỢC TẠO.
Nếu có image_description: tự động tạo ảnh trước khi lưu.""",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "content": {
                            "type": "STRING",
                            "description": "Nội dung đầy đủ của bài đăng"
                        },
                        "image_description": {
                            "type": "STRING",
                            "description": "Mô tả ảnh để tự động tạo (optional)"
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
                "description": """Lấy danh sách tài khoản/pages mạng xã hội đang kết nối.
KHI NÀO DÙNG:
- User hỏi về tài khoản Facebook, pages đã kết nối
- Cần biết thông tin page (category, tên) để tạo content phù hợp
- Kiểm tra trạng thái kết nối, token còn hạn không
TRẢ VỀ: accounts với name, platform, category (loại hình kinh doanh), username, is_active, token_status.
GỢI Ý: Dùng category của page làm business_type khi tạo bài đăng.""",
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

            # Send user message
            response = chat.send_message(user_message)

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

            return {
                'agent_response': response_text,
                'function_calls': function_calls,
                'needs_tool_execution': len(function_calls) > 0,
                'chat_session': chat,  # Return chat session for multi-turn conversation
                'raw_response': response
            }

        except Exception as e:
            return {
                'agent_response': f"Xin lỗi, tôi gặp lỗi: {str(e)}",
                'function_calls': [],
                'needs_tool_execution': False,
                'error': str(e)
            }

    def continue_with_tool_results(self, chat_session, function_results: List[Dict], user=None) -> str:
        """
        Tiếp tục conversation sau khi execute tools

        Args:
            chat_session: Gemini chat session
            function_results: Kết quả từ các function calls
            user: User object for executing additional tools

        Returns:
            Agent's final response
        """
        try:
            # Create function response parts
            parts = []
            for result in function_results:
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
                    return "Đã hoàn thành xử lý các bước trước đó."

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
                        return "Đã xử lý xong phần đầu, nhưng không thể tiếp tục."

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
                    return self.continue_with_tool_results(
                        chat_session=chat_session,
                        function_results=additional_results,
                        user=user
                    )

                # Extract text response
                text_parts = [p.text for p in parts_list if hasattr(p, 'text') and p.text]
                return '\n'.join(text_parts) if text_parts else "Đã xử lý xong!"

            return "Đã xử lý xong!"

        except Exception as e:
            return f"Lỗi khi xử lý: {str(e)}"

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
