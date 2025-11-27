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

        # System prompt - Agent personality
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
   - Trả về: ngày hôm nay, ngày mai, giờ, thứ trong tuần, năm, tháng
   - Dùng khi cần biết ngày giờ để trả lời user

2. get_agent_posts(limit, status)
   - Lấy danh sách bài đăng do AI Agent đã tạo
   - Input: limit (số lượng), status (all/pending/completed/failed)
   - Output: list các posts với content, hashtags, image, thời gian
   - Dùng để xem lại posts đã tạo trước đó

3. get_scheduled_posts(status, limit, days_ahead)
   - Lấy danh sách lịch đăng đã schedule
   - Input: status, limit, days_ahead (số ngày tính từ hôm nay)
   - Output: list các posts với thời gian, nội dung, status
   - Dùng để check lịch đăng

4. get_system_stats()
   - Lấy thống kê tổng quan hệ thống
   - Trả về: số posts, pages, media, users, etc.

5. generate_post_content(business_type, topic, goal, tone)
   - Tạo nội dung bài đăng HOÀN CHỈNH (300+ từ)
   - Input: loại business, chủ đề, mục tiêu, tone
   - Output: Nội dung đầy đủ với Hook, Body, CTA, Hashtags
   - Tool này dùng AI model để generate content chất lượng cao

6. generate_post_image(description, style, size)
   - Tạo hình ảnh từ text description
   - Input: mô tả hình ảnh, style, size
   - Output: image_id và image_url

7. create_agent_post(content, image_description)
   - LƯU bài đăng vào database
   - Input: content (nội dung đầy đủ), image_description (optional - mô tả để tự động tạo ảnh)
   - Nếu có image_description: tool sẽ TỰ ĐỘNG tạo ảnh trước khi lưu
   - Output: post_id và thông báo thành công

8. analyze_schedule(schedule_id)
   - Phân tích lịch đăng và đưa ra insights
   - Input: schedule_id
   - Output: insights, recommendations, patterns

CÁCH BẠN HOẠT ĐỘNG:

✅ Khi user hỏi về bài đăng agent đã tạo:
   → GỌI get_agent_posts() để xem danh sách posts

✅ Khi user yêu cầu tạo bài đăng:
   → Hiểu rằng cần: 1) Generate content, 2) Lưu vào database
   → GỌI generate_post_content() để có nội dung đầy đủ
   → GỌI create_agent_post() với content + image_description để lưu
   → QUAN TRỌNG: Nếu không gọi create_agent_post, bài đăng sẽ KHÔNG được lưu!

✅ Khi user hỏi về lịch đăng với thời gian (ngày mai, tuần sau, hôm nay):
   → TỰ ĐỘNG GỌI get_current_datetime() TRƯỚC để biết ngày hôm nay, ngày mai
   → SAU ĐÓ GỌI get_scheduled_posts() với start_date/end_date phù hợp
   → Ví dụ: "ngày mai có bài nào?" → get_current_datetime() → dùng field 'tomorrow' để filter

✅ Khi user hỏi về hệ thống/stats:
   → GỌI get_system_stats() để lấy dữ liệu

✅ Khi user yêu cầu phân tích:
   → GỌI analyze_schedule() với schedule_id

NGUYÊN TẮC QUAN TRỌNG:
- GỌI TOOLS NGAY - KHÔNG HỎI "Bạn có muốn tôi...", "Làm tiếp không?"
- CÓ THỂ GỌI NHIỀU TOOLS CÙNG LÚC nếu chúng độc lập
- CHỈ BÁO KẾT QUẢ CUỐI - không giải thích từng bước
- KHÔNG tự viết content ngắn - LUÔN dùng generate_post_content() cho bài đăng
- ĐỂ BÀI ĐĂNG HIỂN THỊ CHO USER: phải gọi create_agent_post() để lưu vào database

VÍ DỤ 1 - Tạo bài đăng:
User: "Tạo bài đăng về quán café"
→ Bạn hiểu: Cần tạo content + lưu bài đăng
→ GỌI: generate_post_content(business_type="quán café", topic="giới thiệu quán", goal="engagement", tone="friendly")
→ SAU ĐÓ GỌI: create_agent_post(content=<kết quả từ tool trên>, image_description="Quán café ấm cúng với không gian xanh mát")
→ TRẢ LỜI: "✅ Đã tạo bài đăng thành công!"

VÍ DỤ 2 - Check lịch đăng với thời gian:
User: "Ngày mai có bài đăng nào không?"
→ Bạn hiểu: Cần biết "ngày mai" là ngày nào
→ GỌI: get_current_datetime() → nhận được tomorrow="2025-11-28"
→ SAU ĐÓ GỌI: get_scheduled_posts(start_date="2025-11-28", end_date="2025-11-28")
→ TRẢ LỜI: "Ngày mai (28/11/2025) có X bài đăng: ..."

NGÔN NGỮ:
- Chat bằng tiếng Việt tự nhiên, thân thiện
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
                "description": "Lấy thông tin thời gian hiện tại: ngày hôm nay, ngày mai, giờ, thứ trong tuần, v.v.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "get_agent_posts",
                "description": "Lấy danh sách các bài đăng do AI Agent đã tạo trước đó. Dùng để xem lại posts đã tạo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "limit": {
                            "type": "INTEGER",
                            "description": "Số lượng posts cần lấy, mặc định 20"
                        },
                        "status": {
                            "type": "STRING",
                            "description": "Filter theo status: all, pending, completed, failed"
                        }
                    }
                }
            },
            {
                "name": "get_scheduled_posts",
                "description": "Lấy danh sách các bài đăng đã được lên lịch của user. Hỗ trợ filter theo ngày tháng. Trả về thông tin chi tiết về các posts.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "status": {
                            "type": "STRING",
                            "description": "Filter theo status: draft, approved, scheduled, published",
                        },
                        "limit": {
                            "type": "INTEGER",
                            "description": "Số lượng posts cần lấy, mặc định 10"
                        },
                        "days_ahead": {
                            "type": "INTEGER",
                            "description": "Số ngày tính từ hôm nay. Ví dụ: 7 = lấy posts trong 7 ngày tới từ hôm nay"
                        },
                        "start_date": {
                            "type": "STRING",
                            "description": "Ngày bắt đầu filter (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "STRING",
                            "description": "Ngày kết thúc filter (YYYY-MM-DD)"
                        }
                    }
                }
            },
            {
                "name": "get_system_stats",
                "description": "Lấy thống kê tổng quan về hệ thống: số lượng posts, schedules, media, v.v.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "generate_post_content",
                "description": "Tạo nội dung bài đăng sử dụng AI. Trả về content đầy đủ với hook, body, CTA, hashtags.",
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
                            "description": "Mục tiêu: awareness, engagement, conversion",
                        },
                        "tone": {
                            "type": "STRING",
                            "description": "Giọng điệu: professional, casual, friendly, funny",
                        }
                    },
                    "required": ["business_type", "topic", "goal"]
                }
            },
            {
                "name": "generate_post_image",
                "description": "Tạo hình ảnh minh họa cho bài đăng sử dụng AI",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "description": {
                            "type": "STRING",
                            "description": "Mô tả hình ảnh cần tạo"
                        },
                        "style": {
                            "type": "STRING",
                            "description": "Phong cách: professional, modern, minimalist, colorful",
                        },
                        "size": {
                            "type": "STRING",
                            "description": "Kích thước: 1080x1080, 1200x628, 1080x1920",
                        }
                    },
                    "required": ["description"]
                }
            },
            {
                "name": "create_agent_post",
                "description": "Lưu bài đăng vào database. Nếu có image_description, tool sẽ tự động tạo ảnh trước khi lưu.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "content": {
                            "type": "STRING",
                            "description": "Nội dung đầy đủ của bài đăng"
                        },
                        "image_description": {
                            "type": "STRING",
                            "description": "Mô tả hình ảnh để tạo (VD: 'Quán café ấm cúng với không gian xanh'). Optional."
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "analyze_schedule",
                "description": "Phân tích lịch đăng và đưa ra insights, recommendations",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "schedule_id": {
                            "type": "INTEGER",
                            "description": "ID của schedule cần phân tích"
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
