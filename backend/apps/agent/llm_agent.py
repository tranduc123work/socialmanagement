"""
LLM Agent Service - Gemini-powered Intelligent Agent
"""
import os
import json
from typing import Dict, Any, List, Optional
from django.conf import settings
import google.generativeai as genai

from .prompts import SYSTEM_PROMPT
from .tools import get_tool_definitions


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

        # System prompt - imported from prompts.py
        self.system_prompt = SYSTEM_PROMPT

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
        Dùng model riêng KHÔNG có system_instruction để đếm chính xác

        Args:
            text: Text cần đếm tokens

        Returns:
            Số lượng tokens
        """
        try:
            # Dùng model đơn giản để count tokens (không có system prompt/tools)
            # Nếu dùng self.model → sẽ tính cả system_instruction vào!
            if not hasattr(self, '_token_counter'):
                self._token_counter = genai.GenerativeModel('gemini-1.5-flash')
            result = self._token_counter.count_tokens(text)
            return result.total_tokens
        except Exception:
            # Fallback: estimate ~4 chars per token
            return len(text) // 4

    def _define_tools(self) -> List[Dict]:
        """
        Define tools (functions) mà Agent có thể sử dụng
        Format theo Gemini API requirements (UPPERCASE types)
        Imported from tools.py
        """
        return get_tool_definitions()

    def chat(self, user_message: str, user_id: int, conversation_history: List[Dict] = None, files: List[Dict] = None) -> Dict[str, Any]:
        """
        Chat với user và tự động thực hiện tasks nếu cần
        Hỗ trợ multimodal input (files: images, documents)

        Args:
            user_message: Tin nhắn từ user
            user_id: ID của user
            conversation_history: Lịch sử hội thoại trước đó
            files: List các file đính kèm với format:
                   [{'name': 'file.jpg', 'mime_type': 'image/jpeg', 'data': 'base64...'}]

        Returns:
            {
                'agent_response': str,
                'function_calls': List[Dict],
                'needs_tool_execution': bool
            }
        """
        try:
            import base64
            import logging
            logger = logging.getLogger(__name__)

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

            # Count input tokens với chi tiết từng thành phần
            # 1. System Prompt tokens
            system_prompt_tokens = self.count_tokens(self.system_prompt)

            # 2. Tools tokens (estimate từ tool definitions)
            tools_str = json.dumps(self._define_tools())
            tools_tokens = self.count_tokens(tools_str)

            # 3. History tokens
            history_tokens = 0
            for msg in chat_history:
                for part in msg.get('parts', []):
                    history_tokens += self.count_tokens(part)

            # 4. User message tokens
            user_message_tokens = self.count_tokens(user_message)

            # 5. Files tokens (sẽ được cập nhật bên dưới nếu có files)
            files_tokens = 0

            # Tổng input tokens
            input_tokens = system_prompt_tokens + tools_tokens + history_tokens + user_message_tokens

            # Build message content for Gemini multimodal
            message_parts = []
            file_descriptions = []

            # Process files if any (add as inline_data parts)
            if files:
                logger.info(f"[AGENT] Processing {len(files)} files for multimodal")

                for idx, file_data in enumerate(files):
                    try:
                        file_name = file_data.get('name', f'file_{idx}')
                        mime_type = file_data.get('mime_type', 'application/octet-stream')

                        # Add file as inline_data part (Gemini will analyze it)
                        message_parts.append({
                            'inline_data': {
                                'mime_type': mime_type,
                                'data': file_data['data']  # base64 string
                            }
                        })

                        # Build description for text context và track files_tokens
                        if mime_type.startswith('image/'):
                            file_descriptions.append(f"[Hình ảnh: {file_name}]")
                            files_tokens += 258  # Gemini counts ~258 tokens per image
                        elif mime_type == 'application/pdf':
                            file_descriptions.append(f"[Tài liệu PDF: {file_name}]")
                            files_tokens += 500  # Estimate for PDF
                        else:
                            file_descriptions.append(f"[File: {file_name}]")
                            files_tokens += 200  # Estimate

                        logger.info(f"[AGENT] Added file: {file_name} ({mime_type})")

                    except Exception as e:
                        logger.warning(f"[AGENT] Error processing file: {e}")

            # Build final text message with file context
            final_message = user_message
            if file_descriptions:
                # Thêm mô tả files vào đầu message để agent biết có files đính kèm
                files_context = "\n".join(file_descriptions)
                final_message = f"[User đính kèm các files sau - hãy phân tích chúng nếu cần:\n{files_context}]\n\n{user_message}"

            # Add text message as the last part
            message_parts.append(final_message)

            # Cập nhật tổng input_tokens với files_tokens
            input_tokens += files_tokens

            # Send message (multimodal if has files)
            if len(message_parts) > 1:
                logger.info(f"[AGENT] Sending multimodal message with {len(message_parts)} parts")
                response = chat.send_message(message_parts)
            else:
                response = chat.send_message(user_message)

            # Count output tokens from response
            output_tokens = 0

            # Extract function calls if any
            function_calls = []
            response_text = ""

            # Track detailed output token breakdown
            text_tokens = 0
            function_call_tokens = 0
            function_calls_detail = []  # Chi tiết từng tool

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
                                    elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                                        # Handle iterable types (like RepeatedScalarContainer from protobuf)
                                        try:
                                            args_dict[key] = [v for v in value]
                                        except:
                                            args_dict[key] = list(value)
                                    else:
                                        # For complex types, try to convert to string
                                        try:
                                            args_dict[key] = str(value)
                                        except:
                                            args_dict[key] = None

                            # Count tokens for this specific function call
                            fc_str = f"{fc.name}({json.dumps(args_dict)})"
                            fc_tokens = self.count_tokens(fc_str)

                            function_calls.append({
                                'name': fc.name,
                                'args': args_dict,
                                'tokens': fc_tokens  # Thêm tokens cho từng tool
                            })

                            # Track detail for breakdown
                            function_calls_detail.append({
                                'name': fc.name,
                                'tokens': fc_tokens
                            })

                            function_call_tokens += fc_tokens
                            output_tokens += fc_tokens

                        # Check for text
                        elif hasattr(part, 'text') and part.text:
                            response_text += part.text
                            txt_tokens = self.count_tokens(part.text)
                            text_tokens += txt_tokens
                            output_tokens += txt_tokens

            # Store token usage with breakdown (cả input và output)
            self.last_token_usage = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'breakdown': {
                    # Input breakdown chi tiết
                    'input_breakdown': {
                        'system_prompt_tokens': system_prompt_tokens,
                        'tools_tokens': tools_tokens,
                        'history_tokens': history_tokens,
                        'user_message_tokens': user_message_tokens,
                        'files_tokens': files_tokens
                    },
                    # Output breakdown chi tiết
                    'text_tokens': text_tokens,
                    'function_call_tokens': function_call_tokens,
                    'function_calls_detail': function_calls_detail  # Chi tiết từng tool
                }
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

    def continue_with_tool_results(self, chat_session, function_results: List[Dict], user=None, reasoning_content: str = None) -> Dict[str, Any]:
        """
        Tiếp tục conversation sau khi execute tools

        Args:
            chat_session: Gemini chat session
            function_results: Kết quả từ các function calls
            user: User object for executing additional tools
            reasoning_content: Ignored for Gemini (only used by DeepSeek reasoner)

        Returns:
            {
                'response': str,
                'token_usage': {'input_tokens': int, 'output_tokens': int, 'total_tokens': int, 'breakdown': {...}}
            }
        """
        # Note: reasoning_content is ignored for Gemini, only used by DeepSeek reasoner
        try:
            # Track tokens for this turn
            input_tokens = 0
            output_tokens = 0
            tool_result_tokens = 0

            # Track image generation tokens from tool results
            image_gen_prompt_tokens = 0
            image_gen_output_tokens = 0
            image_gen_total_tokens = 0

            # Create function response parts
            parts = []
            for result in function_results:
                # Count tokens from function results
                result_str = str(result.get('result', ''))
                result_tokens = self.count_tokens(result_str)
                input_tokens += result_tokens
                tool_result_tokens += result_tokens

                # Extract image generation tokens if present
                tool_result = result.get('result', {})
                if isinstance(tool_result, dict):
                    img_tokens = tool_result.get('image_generation_tokens', {})
                    if img_tokens:
                        image_gen_prompt_tokens += img_tokens.get('prompt_tokens', 0)
                        image_gen_output_tokens += img_tokens.get('output_tokens', 0)
                        image_gen_total_tokens += img_tokens.get('total_tokens', 0)

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
                                elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                                    # Handle iterable types (like RepeatedScalarContainer from protobuf)
                                    try:
                                        args_dict[key] = [v for v in value]
                                    except:
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
                            'response': "Fugu đã xử lý xong phần đầu, nhưng không thể tiếp tục.",
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

                response_text = '\n'.join(text_parts) if text_parts else "Fugu đã xử lý xong!"

                # Update stored token usage with breakdown
                prev_breakdown = self.last_token_usage.get('breakdown', {})
                prev_img_gen = prev_breakdown.get('image_generation', {})

                # Merge image generation tokens with previous
                merged_img_gen = None
                if image_gen_total_tokens > 0 or prev_img_gen:
                    merged_img_gen = {
                        'prompt_tokens': prev_img_gen.get('prompt_tokens', 0) + image_gen_prompt_tokens,
                        'output_tokens': prev_img_gen.get('output_tokens', 0) + image_gen_output_tokens,
                        'total_tokens': prev_img_gen.get('total_tokens', 0) + image_gen_total_tokens
                    }

                breakdown = {
                    'text_tokens': prev_breakdown.get('text_tokens', 0) + output_tokens,
                    'function_call_tokens': prev_breakdown.get('function_call_tokens', 0),
                    'tool_result_tokens': prev_breakdown.get('tool_result_tokens', 0) + tool_result_tokens
                }

                # Add image generation tokens if present
                if merged_img_gen:
                    breakdown['image_generation'] = merged_img_gen

                # Preserve input_breakdown from previous if exists
                if 'input_breakdown' in prev_breakdown:
                    breakdown['input_breakdown'] = prev_breakdown['input_breakdown']
                    # Add tool_results_tokens to input_breakdown
                    breakdown['input_breakdown']['tool_results_tokens'] = prev_breakdown.get('input_breakdown', {}).get('tool_results_tokens', 0) + tool_result_tokens

                # Preserve function_calls_detail from previous if exists
                if 'function_calls_detail' in prev_breakdown:
                    breakdown['function_calls_detail'] = prev_breakdown['function_calls_detail']

                self.last_token_usage = {
                    'input_tokens': self.last_token_usage.get('input_tokens', 0) + input_tokens,
                    'output_tokens': self.last_token_usage.get('output_tokens', 0) + output_tokens,
                    'total_tokens': self.last_token_usage.get('input_tokens', 0) + input_tokens + self.last_token_usage.get('output_tokens', 0) + output_tokens,
                    'breakdown': breakdown
                }

                return {
                    'response': response_text,
                    'token_usage': self.last_token_usage
                }

            return {
                'response': "Fugu đã xử lý xong!",
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
