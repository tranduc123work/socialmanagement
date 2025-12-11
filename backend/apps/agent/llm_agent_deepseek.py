"""
LLM Agent Service - DeepSeek-powered Intelligent Agent
Sử dụng OpenAI-compatible API
"""
import os
import json
from typing import Dict, Any, List, Optional
from django.conf import settings
from openai import OpenAI

from .prompts import SYSTEM_PROMPT
from .tools_deepseek import get_tool_definitions


import logging
logger = logging.getLogger(__name__)


class DeepSeekAgent:
    """
    Intelligent Agent sử dụng DeepSeek LLM
    Agent có thể:
    - Chat với user
    - Phân tích hệ thống
    - Tạo content và image
    - Thực hiện tasks tự động
    """

    def __init__(self):
        logger.info("=" * 50)
        logger.info("[AGENT] Initializing DeepSeekAgent")
        logger.info("=" * 50)
        # Configure DeepSeek API (OpenAI-compatible)
        api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        if not api_key:
            api_key = os.environ.get('DEEPSEEK_API_KEY')

        # Initialize OpenAI client with DeepSeek base_url
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        # Get model name from settings/env
        self.model_name = getattr(settings, 'DEEPSEEK_AGENT_MODEL', None)
        if not self.model_name:
            self.model_name = os.environ.get('DEEPSEEK_AGENT_MODEL', 'deepseek-chat')

        # System prompt - imported from prompts.py
        self.system_prompt = SYSTEM_PROMPT

        # Tool definitions in OpenAI format
        self.tools = get_tool_definitions()

        # Track token usage
        self.last_token_usage = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        }

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count cho text
        DeepSeek không có API count tokens, dùng estimate

        Args:
            text: Text cần đếm tokens

        Returns:
            Số lượng tokens (estimate)
        """
        # Estimate: ~4 chars per token cho tiếng Việt/English mixed
        return len(text) // 4

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

            # Build messages for OpenAI format
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]

            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = msg['role']
                    content = msg['message']
                    if role == 'user':
                        messages.append({"role": "user", "content": content})
                    elif role == 'agent':
                        messages.append({"role": "assistant", "content": content})

            # Count input tokens
            system_prompt_tokens = self.count_tokens(self.system_prompt)
            tools_str = json.dumps(self.tools)
            tools_tokens = self.count_tokens(tools_str)
            history_tokens = sum(self.count_tokens(m.get('content', '')) for m in messages[1:])
            user_message_tokens = self.count_tokens(user_message)
            files_tokens = 0

            # Process files if any
            file_descriptions = []

            if files:
                logger.info(f"[AGENT-DEEPSEEK] Processing {len(files)} files")

                for idx, file_data in enumerate(files):
                    try:
                        file_name = file_data.get('name', f'file_{idx}')
                        mime_type = file_data.get('mime_type', 'application/octet-stream')

                        # DeepSeek-chat does NOT support images - return error
                        if mime_type.startswith('image/'):
                            logger.error(f"[AGENT-DEEPSEEK] Image upload not supported: {file_name}")
                            return {
                                'agent_response': f"⚠️ DeepSeek không hỗ trợ xử lý hình ảnh. Vui lòng chuyển sang dùng Gemini trong cài đặt để gửi ảnh.",
                                'function_calls': [],
                                'needs_tool_execution': False,
                                'error': 'DeepSeek does not support image input',
                                'token_usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
                            }
                        else:
                            file_descriptions.append(f"[File: {file_name}]")
                            files_tokens += 200

                        logger.info(f"[AGENT-DEEPSEEK] Added file: {file_name} ({mime_type})")

                    except Exception as e:
                        logger.warning(f"[AGENT-DEEPSEEK] Error processing file: {e}")

            # Build final message content
            final_message = user_message
            if file_descriptions:
                files_context = "\n".join(file_descriptions)
                final_message = f"[User đính kèm các files sau - hãy phân tích chúng nếu cần:\n{files_context}]\n\n{user_message}"

            # Add user message (text only - DeepSeek doesn't support images)
            messages.append({"role": "user", "content": final_message})

            input_tokens = system_prompt_tokens + tools_tokens + history_tokens + user_message_tokens + files_tokens

            # Call DeepSeek API
            logger.info(f"[AGENT-DEEPSEEK] Calling DeepSeek API with model: {self.model_name}")
            logger.info(f"[AGENT-DEEPSEEK] User message: {user_message[:100]}...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

            # Extract response
            choice = response.choices[0]
            message = choice.message
            response_text = message.content or ""
            function_calls = []

            # Extract reasoning_content for deepseek-reasoner model
            reasoning_content = getattr(message, 'reasoning_content', None)
            if reasoning_content:
                logger.info(f"[AGENT-DEEPSEEK] Got reasoning_content ({len(reasoning_content)} chars)")

            # Count output tokens
            output_tokens = 0
            text_tokens = self.count_tokens(response_text)
            function_call_tokens = 0
            function_calls_detail = []

            output_tokens += text_tokens

            # Check for tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    fc_name = tool_call.function.name
                    fc_args_str = tool_call.function.arguments

                    # Parse arguments
                    try:
                        fc_args = json.loads(fc_args_str)
                    except json.JSONDecodeError:
                        fc_args = {}

                    # Count tokens for function call
                    fc_str = f"{fc_name}({fc_args_str})"
                    fc_tokens = self.count_tokens(fc_str)

                    function_calls.append({
                        'name': fc_name,
                        'args': fc_args,
                        'tokens': fc_tokens,
                        'tool_call_id': tool_call.id  # Needed for response
                    })

                    function_calls_detail.append({
                        'name': fc_name,
                        'tokens': fc_tokens
                    })

                    function_call_tokens += fc_tokens
                    output_tokens += fc_tokens

            # Get actual token usage from response if available
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            # Store token usage
            self.last_token_usage = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'breakdown': {
                    'input_breakdown': {
                        'system_prompt_tokens': system_prompt_tokens,
                        'tools_tokens': tools_tokens,
                        'history_tokens': history_tokens,
                        'user_message_tokens': user_message_tokens,
                        'files_tokens': files_tokens
                    },
                    'text_tokens': text_tokens,
                    'function_call_tokens': function_call_tokens,
                    'function_calls_detail': function_calls_detail
                }
            }

            return {
                'agent_response': response_text,
                'function_calls': function_calls,
                'needs_tool_execution': len(function_calls) > 0,
                'chat_session': messages,  # Return messages for multi-turn conversation
                'raw_response': response,
                'token_usage': self.last_token_usage,
                'reasoning_content': reasoning_content  # For deepseek-reasoner
            }

        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[AGENT-DEEPSEEK] Error in chat: {str(e)}")
            logger.error(f"[AGENT-DEEPSEEK] Traceback: {traceback.format_exc()}")
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
            chat_session: List messages (OpenAI format)
            function_results: Kết quả từ các function calls
            user: User object for executing additional tools
            reasoning_content: reasoning_content từ response trước (required cho deepseek-reasoner)

        Returns:
            {
                'response': str,
                'token_usage': {'input_tokens': int, 'output_tokens': int, 'total_tokens': int, 'breakdown': {...}}
            }
        """
        try:
            import logging
            logger = logging.getLogger(__name__)

            # Track tokens for this turn
            input_tokens = 0
            output_tokens = 0
            tool_result_tokens = 0

            # Track image generation tokens from tool results
            image_gen_prompt_tokens = 0
            image_gen_output_tokens = 0
            image_gen_total_tokens = 0

            messages = chat_session.copy() if isinstance(chat_session, list) else []

            # Add assistant message with tool calls (reconstructed)
            # Include reasoning_content for deepseek-reasoner model
            assistant_message = {
                "role": "assistant",
                "content": None,
                "tool_calls": []
            }
            # Add reasoning_content if provided (required for deepseek-reasoner)
            if reasoning_content:
                assistant_message["reasoning_content"] = reasoning_content
                logger.info(f"[AGENT-DEEPSEEK] Including reasoning_content in assistant message")

            for result in function_results:
                tool_call_id = result.get('tool_call_id', f"call_{result['function_name']}")
                assistant_message["tool_calls"].append({
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": result['function_name'],
                        "arguments": json.dumps(result.get('args', {}))
                    }
                })

            if assistant_message["tool_calls"]:
                messages.append(assistant_message)

            # Add tool results as tool messages
            for result in function_results:
                result_str = json.dumps(result.get('result', ''), ensure_ascii=False)
                result_tokens = self.count_tokens(result_str)
                input_tokens += result_tokens
                tool_result_tokens += result_tokens
                logger.info(f"[AGENT-DEEPSEEK] Tool {result['function_name']} result ({len(result_str)} chars): {result_str[:300]}...")

                # Extract image generation tokens if present
                tool_result = result.get('result', {})
                if isinstance(tool_result, dict):
                    img_tokens = tool_result.get('image_generation_tokens', {})
                    if img_tokens:
                        image_gen_prompt_tokens += img_tokens.get('prompt_tokens', 0)
                        image_gen_output_tokens += img_tokens.get('output_tokens', 0)
                        image_gen_total_tokens += img_tokens.get('total_tokens', 0)

                tool_call_id = result.get('tool_call_id', f"call_{result['function_name']}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result_str
                })

            # Call API again
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

            choice = response.choices[0]
            message = choice.message

            # Check for more function calls
            more_function_calls = []
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    fc_name = tool_call.function.name
                    try:
                        fc_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        fc_args = {}

                    more_function_calls.append({
                        'name': fc_name,
                        'args': fc_args,
                        'tool_call_id': tool_call.id
                    })

            # If there are more function calls, execute them too
            if more_function_calls:
                logger.info(f"[AGENT-DEEPSEEK] Model wants to call {len(more_function_calls)} more functions: {[fc['name'] for fc in more_function_calls]}")

                if not user:
                    logger.error("[AGENT-DEEPSEEK] Cannot execute additional tools - user context missing")
                    return {
                        'response': "Fugu đã xử lý xong phần đầu, nhưng không thể tiếp tục.",
                        'token_usage': {'input_tokens': input_tokens, 'output_tokens': 0, 'total_tokens': input_tokens}
                    }

                # Execute additional tools
                from .services import AgentToolExecutor

                additional_results = []
                for fc in more_function_calls:
                    logger.info(f"[AGENT-DEEPSEEK] Executing additional tool: {fc['name']}")
                    result = AgentToolExecutor.execute_tool(
                        function_name=fc['name'],
                        arguments=fc['args'],
                        user=user
                    )
                    additional_results.append({
                        'function_name': fc['name'],
                        'args': fc['args'],
                        'result': result,
                        'tool_call_id': fc['tool_call_id']
                    })

                # Recursively continue with additional tool results
                # Note: Don't append assistant message here - the recursive call will handle it
                # via lines 311-333 using the tool_call_ids from additional_results

                recursive_result = self.continue_with_tool_results(
                    chat_session=messages,
                    function_results=additional_results,
                    user=user
                )
                recursive_result['token_usage']['input_tokens'] += input_tokens
                recursive_result['token_usage']['total_tokens'] += input_tokens
                return recursive_result

            # Extract text response
            response_text = message.content or "Fugu đã xử lý xong!"
            logger.info(f"[AGENT-DEEPSEEK] Final response text ({len(response_text)} chars): {response_text[:200]}...")

            # Check for reasoning_content in final response (deepseek-reasoner)
            final_reasoning = getattr(message, 'reasoning_content', None)
            if final_reasoning:
                logger.info(f"[AGENT-DEEPSEEK] Final reasoning_content ({len(final_reasoning)} chars): {final_reasoning[:200]}...")

            # Get actual token usage from response
            # Note: API's prompt_tokens includes ALL history (system + previous messages + tool results)
            # So we should NOT accumulate input_tokens - just use the latest value
            # Output tokens ARE incremental per turn, so we accumulate those
            current_input_tokens = input_tokens  # fallback to estimate
            current_output_tokens = output_tokens
            if response.usage:
                current_input_tokens = response.usage.prompt_tokens
                current_output_tokens = response.usage.completion_tokens

            # Accumulate output tokens across turns
            accumulated_output_tokens = self.last_token_usage.get('output_tokens', 0) + current_output_tokens

            # Update stored token usage with breakdown
            prev_breakdown = self.last_token_usage.get('breakdown', {})
            prev_img_gen = prev_breakdown.get('image_generation', {})

            # Merge image generation tokens
            merged_img_gen = None
            if image_gen_total_tokens > 0 or prev_img_gen:
                merged_img_gen = {
                    'prompt_tokens': prev_img_gen.get('prompt_tokens', 0) + image_gen_prompt_tokens,
                    'output_tokens': prev_img_gen.get('output_tokens', 0) + image_gen_output_tokens,
                    'total_tokens': prev_img_gen.get('total_tokens', 0) + image_gen_total_tokens
                }

            breakdown = {
                'text_tokens': prev_breakdown.get('text_tokens', 0) + self.count_tokens(response_text),
                'function_call_tokens': prev_breakdown.get('function_call_tokens', 0),
                'tool_result_tokens': prev_breakdown.get('tool_result_tokens', 0) + tool_result_tokens
            }

            if merged_img_gen:
                breakdown['image_generation'] = merged_img_gen

            if 'input_breakdown' in prev_breakdown:
                breakdown['input_breakdown'] = prev_breakdown['input_breakdown']
                breakdown['input_breakdown']['tool_results_tokens'] = prev_breakdown.get('input_breakdown', {}).get('tool_results_tokens', 0) + tool_result_tokens

            if 'function_calls_detail' in prev_breakdown:
                breakdown['function_calls_detail'] = prev_breakdown['function_calls_detail']

            self.last_token_usage = {
                'input_tokens': current_input_tokens,  # Latest turn's input (already includes history)
                'output_tokens': accumulated_output_tokens,  # Accumulated across all turns
                'total_tokens': current_input_tokens + accumulated_output_tokens,
                'breakdown': breakdown
            }

            return {
                'response': response_text,
                'token_usage': self.last_token_usage
            }

        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"[AGENT-DEEPSEEK] Error in continue_with_tool_results: {str(e)}")
            logger.error(f"[AGENT-DEEPSEEK] Traceback: {traceback.format_exc()}")
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

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        return {
            'chat_session': messages,
            'initial_response': response
        }


# Singleton instance
_agent_instance = None


def get_agent() -> DeepSeekAgent:
    """Get or create agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DeepSeekAgent()
    return _agent_instance


def reset_agent():
    """Reset agent instance to reload system prompt"""
    global _agent_instance
    _agent_instance = None
