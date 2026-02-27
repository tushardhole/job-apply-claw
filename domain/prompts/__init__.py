"""Prompt templates for the LLM browser agent."""

from .system_prompt import SYSTEM_PROMPT  # noqa: F401
from .task_prompts import build_apply_task_prompt  # noqa: F401

__all__ = [
    "SYSTEM_PROMPT",
    "build_apply_task_prompt",
]
