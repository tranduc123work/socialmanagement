"""
Agent Factory - Switch giữa Gemini và DeepSeek agent
Dựa vào AI_AGENT_PROVIDER trong .env
"""
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def get_agent_provider() -> str:
    """
    Lấy provider từ settings hoặc env
    Returns: 'gemini' hoặc 'deepseek'
    """
    provider = getattr(settings, 'AI_AGENT_PROVIDER', None)
    logger.info(f"[AGENT-FACTORY] settings.AI_AGENT_PROVIDER = {provider}")
    if not provider:
        provider = os.environ.get('AI_AGENT_PROVIDER', 'gemini')
        logger.info(f"[AGENT-FACTORY] os.environ AI_AGENT_PROVIDER = {provider}")
    return provider.lower()


def get_agent():
    """
    Factory function để lấy agent instance dựa vào provider
    Returns: GeminiAgent hoặc DeepSeekAgent instance
    """
    provider = get_agent_provider()
    logger.info(f"[AGENT-FACTORY] Using provider: {provider}")

    if provider == 'deepseek':
        logger.info("[AGENT-FACTORY] Loading DeepSeekAgent...")
        from .llm_agent_deepseek import get_agent as get_deepseek_agent
        return get_deepseek_agent()
    else:
        # Default: Gemini
        logger.info("[AGENT-FACTORY] Loading GeminiAgent...")
        from .llm_agent import get_agent as get_gemini_agent
        return get_gemini_agent()


def reset_agent():
    """
    Reset agent instance của tất cả providers
    """
    provider = get_agent_provider()

    if provider == 'deepseek':
        from .llm_agent_deepseek import reset_agent as reset_deepseek
        reset_deepseek()
    else:
        from .llm_agent import reset_agent as reset_gemini
        reset_gemini()
