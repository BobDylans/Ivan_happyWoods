"""
Agent Prompts Module

This package contains all system prompts and prompt-building utilities
extracted from the original nodes.py file.

Modules:
- system_prompts.py: Core prompt constants (BASE_IDENTITY, TOOLS_GUIDE, TASK_FRAMEWORK)
                     and prompt builder functions

Usage:
    from agent.prompts import BASE_IDENTITY, TASK_FRAMEWORK
    from agent.prompts import build_optimized_system_prompt

    # Build complete system prompt with context awareness
    system_prompt = build_optimized_system_prompt(
        available_tools="- **calculator**: 执行数学计算\\n- **web_search**: 搜索网络信息",
        state={"messages": [...], "tool_calls": [...]}
    )
"""

from .system_prompts import (
    BASE_IDENTITY,
    TOOLS_GUIDE_TEMPLATE,
    TASK_FRAMEWORK,
    build_optimized_system_prompt,
    build_context_aware_addition,
    format_available_tools,
    build_tools_guide,
)

__all__ = [
    "BASE_IDENTITY",
    "TOOLS_GUIDE_TEMPLATE",
    "TASK_FRAMEWORK",
    "build_optimized_system_prompt",
    "build_context_aware_addition",
    "format_available_tools",
    "build_tools_guide",
]
