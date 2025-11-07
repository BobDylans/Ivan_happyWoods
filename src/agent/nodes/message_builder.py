"""
Message Builder Module

This module provides utilities for preparing message lists for LLM API calls.
It handles:
- System prompt construction (via prompts module)
- External history integration (from SessionHistoryManager)
- Message formatting and truncation
- Fallback to state-based history

This is a pure utility module with no state or side effects beyond logging.
Design philosophy: Single Responsibility Principle - only format messages, nothing else.
"""

import logging
from typing import Dict, List, Optional, Any

# Import prompts module for system prompt construction
from ..prompts import build_optimized_system_prompt
from ..state import AgentState, MessageRole


logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Maximum number of historical messages to include in LLM context
# This prevents token limit overflow while preserving recent context
MAX_HISTORY_MESSAGES = 10


# ============================================================================
# Core Message Preparation Functions
# ============================================================================

def prepare_llm_messages(
    state: AgentState,
    external_history: Optional[List[Dict[str, str]]] = None,
    max_history: int = MAX_HISTORY_MESSAGES
) -> List[Dict[str, str]]:
    """
    Prepare message list for LLM API call.

    This function constructs the complete message list including:
    1. System prompt (via prompts.build_optimized_system_prompt)
    2. Conversation history (preferring external_history if provided)
    3. Current user message (if not already in history)

    The function prioritizes external_history (from SessionHistoryManager) over
    state["messages"] because external history may include messages from database
    that aren't in the current state.

    Args:
        state: Current conversation state containing:
            - messages: List of ConversationMessage objects
            - current_intent: Optional intent label for prompt optimization
            - tool_calls: Tool call history for context-aware prompts
            - user_input: Current user input

        external_history: Optional list of historical messages from SessionHistoryManager
            Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            If provided, this takes priority over state["messages"]

        max_history: Maximum number of historical messages to include (default: 10)
            This limits context window size to prevent token overflow

    Returns:
        List of message dictionaries in OpenAI API format:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]

    Example:
        >>> state = {
        ...     "messages": [ConversationMessage(role=MessageRole.USER, content="Hello")],
        ...     "current_intent": "general_conversation",
        ...     "tool_calls": [],
        ...     "user_input": "Hello"
        ... }
        >>> messages = prepare_llm_messages(state)
        >>> messages[0]["role"]
        "system"
        >>> messages[1]["role"]
        "user"

    Implementation Notes:
        - System prompt is always first message
        - External history is truncated to most recent max_history messages
        - If external_history is provided but doesn't include current user message,
          it's appended from state["messages"]
        - If external_history is None, falls back to state["messages"]
    """
    messages = []

    # ========================================================================
    # Step 1: Build System Prompt
    # ========================================================================
    # Use prompts module to construct optimized system prompt
    # This includes base identity, tools guide, task framework, and context-aware additions
    system_prompt = build_optimized_system_prompt(state=state)
    system_message = {
        "role": "system",
        "content": system_prompt
    }
    messages.append(system_message)

    # ========================================================================
    # Step 2: Add Conversation History
    # ========================================================================
    if external_history is not None:
        # Priority path: Use external history from SessionHistoryManager
        # This may include messages from database that aren't in current state

        # Truncate to most recent messages to respect token limits
        recent_history = external_history[-max_history:] if external_history else []

        for msg in recent_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        logger.info(f"✅ Loaded {len(recent_history)} messages from external history for LLM")

        # ====================================================================
        # Important: Append current user message if not already in history
        # ====================================================================
        # External history may not include the very latest user input
        # (e.g., if SessionManager hasn't saved it yet)
        # So we check state["messages"] for the current user message
        if state.get("messages") and state["messages"][-1].role == MessageRole.USER:
            current_user_msg = state["messages"][-1]

            # Avoid duplicating if external_history already has this message
            # (Check by comparing content of last message in history)
            is_duplicate = (
                recent_history and
                recent_history[-1].get("role") == "user" and
                recent_history[-1].get("content") == current_user_msg.content
            )

            if not is_duplicate:
                messages.append({
                    "role": "user",
                    "content": current_user_msg.content
                })
                logger.info(f"✅ Added current user message to LLM input (not in external history)")

    else:
        # ====================================================================
        # Fallback path: Use state["messages"] if no external history
        # ====================================================================
        logger.info("⚠️ No external history provided, using state messages")

        # Get recent messages from state
        state_messages = state.get("messages", [])
        recent_messages = state_messages[-max_history:] if state_messages else []

        # Convert ConversationMessage objects to API format
        for msg in recent_messages:
            # Only include user and assistant messages (skip system messages)
            if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                messages.append({
                    "role": msg.role.value,  # Convert enum to string
                    "content": msg.content
                })

        logger.info(f"📝 Using {len(recent_messages)} messages from state")

    return messages


def format_message(role: str, content: str, **metadata) -> Dict[str, str]:
    """
    Format a single message for LLM API.

    This is a utility function for creating properly formatted message dictionaries.
    Useful for testing or manual message construction.

    Args:
        role: Message role ("system", "user", "assistant", "tool")
        content: Message content text
        **metadata: Optional metadata fields (name, function_call, etc.)

    Returns:
        Formatted message dictionary

    Example:
        >>> format_message("user", "Hello, how are you?")
        {"role": "user", "content": "Hello, how are you?"}

        >>> format_message("assistant", "I'm doing well!", name="assistant-1")
        {"role": "assistant", "content": "I'm doing well!", "name": "assistant-1"}
    """
    message = {
        "role": role,
        "content": content
    }

    # Add any additional metadata
    message.update(metadata)

    return message


def validate_messages(messages: List[Dict[str, str]]) -> bool:
    """
    Validate message list format for LLM API compatibility.

    Checks:
    - All messages have "role" and "content" fields
    - Roles are valid ("system", "user", "assistant", "tool")
    - Content is non-empty string
    - First message is system message (recommended)

    Args:
        messages: List of message dictionaries to validate

    Returns:
        True if valid, False otherwise (logs warnings for issues)

    Example:
        >>> messages = [
        ...     {"role": "system", "content": "You are a helpful assistant"},
        ...     {"role": "user", "content": "Hello"}
        ... ]
        >>> validate_messages(messages)
        True

        >>> invalid = [{"role": "user"}]  # Missing content
        >>> validate_messages(invalid)
        False
    """
    if not messages:
        logger.warning("Message list is empty")
        return False

    valid_roles = {"system", "user", "assistant", "tool", "function"}

    for i, msg in enumerate(messages):
        # Check required fields
        if "role" not in msg:
            logger.warning(f"Message {i} missing 'role' field")
            return False

        if "content" not in msg:
            logger.warning(f"Message {i} missing 'content' field")
            return False

        # Check role validity
        if msg["role"] not in valid_roles:
            logger.warning(f"Message {i} has invalid role: {msg['role']}")
            return False

        # Check content is non-empty
        if not msg["content"] or not msg["content"].strip():
            logger.warning(f"Message {i} has empty content")
            return False

    # Recommend (but don't require) system message first
    if messages[0]["role"] != "system":
        logger.info("First message is not system message (recommended but not required)")

    return True


def truncate_messages(
    messages: List[Dict[str, str]],
    max_messages: int
) -> List[Dict[str, str]]:
    """
    Truncate message list to maximum number of messages.

    Preserves system message (if present) and truncates from the middle,
    keeping most recent messages.

    Args:
        messages: Full message list
        max_messages: Maximum number of messages to keep

    Returns:
        Truncated message list

    Example:
        >>> messages = [
        ...     {"role": "system", "content": "System prompt"},
        ...     {"role": "user", "content": "Msg 1"},
        ...     {"role": "assistant", "content": "Resp 1"},
        ...     {"role": "user", "content": "Msg 2"},
        ...     {"role": "assistant", "content": "Resp 2"},
        ... ]
        >>> truncate_messages(messages, max_messages=3)
        [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Msg 2"},
            {"role": "assistant", "content": "Resp 2"}
        ]
    """
    if len(messages) <= max_messages:
        return messages

    # Preserve system message if present
    if messages[0]["role"] == "system":
        # Keep system + most recent (max_messages - 1) messages
        return [messages[0]] + messages[-(max_messages - 1):]
    else:
        # Just keep most recent messages
        return messages[-max_messages:]


# ============================================================================
# Convenience Functions
# ============================================================================

def get_last_user_message(state: AgentState) -> Optional[str]:
    """
    Extract the most recent user message from state.

    Args:
        state: Conversation state

    Returns:
        Last user message content, or None if no user messages

    Example:
        >>> state = {"messages": [
        ...     ConversationMessage(role=MessageRole.USER, content="Hello"),
        ...     ConversationMessage(role=MessageRole.ASSISTANT, content="Hi"),
        ... ]}
        >>> get_last_user_message(state)
        "Hello"
    """
    messages = state.get("messages", [])

    # Search backwards for last user message
    for msg in reversed(messages):
        if msg.role == MessageRole.USER:
            return msg.content

    return None


def get_last_assistant_message(state: AgentState) -> Optional[str]:
    """
    Extract the most recent assistant message from state.

    Args:
        state: Conversation state

    Returns:
        Last assistant message content, or None if no assistant messages

    Example:
        >>> state = {"messages": [
        ...     ConversationMessage(role=MessageRole.USER, content="Hello"),
        ...     ConversationMessage(role=MessageRole.ASSISTANT, content="Hi there!"),
        ... ]}
        >>> get_last_assistant_message(state)
        "Hi there!"
    """
    messages = state.get("messages", [])

    # Search backwards for last assistant message
    for msg in reversed(messages):
        if msg.role == MessageRole.ASSISTANT:
            return msg.content

    return None


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "prepare_llm_messages",
    "format_message",
    "validate_messages",
    "truncate_messages",
    "get_last_user_message",
    "get_last_assistant_message",
    "MAX_HISTORY_MESSAGES",
]
