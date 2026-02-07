"""
LLM Prompts module.

Provides standardized prompt templates for LLM interrogation tasks.
"""

from .page_classification import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_messages,
    build_user_message,
)

__all__ = [
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "build_messages",
    "build_user_message",
]
