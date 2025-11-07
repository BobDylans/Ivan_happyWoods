"""
Response Formatter Module

This module handles final response formatting for the voice agent.
It's the last node in the conversation processing flow:
1. Ensures response content exists (provides fallback if missing)
2. Creates assistant message object
3. Adds metadata (model, intent, tool usage, RAG snippets)
4. Marks conversation turn as complete

This is a simple module focused solely on response finalization.
"""

import logging
from datetime import datetime

from .base import AgentNodesBase
from ..state import AgentState, ConversationMessage, MessageRole


logger = logging.getLogger(__name__)


# ============================================================================
# Response Formatter Class
# ============================================================================

class ResponseFormatter(AgentNodesBase):
    """
    Response formatter node for finalizing agent responses.

    This class handles the final stage of conversation processing:
    1. Validates response content (provides fallback if missing)
    2. Creates ConversationMessage object for assistant
    3. Adds comprehensive metadata
    4. Updates conversation history
    5. Marks conversation turn as complete

    Inherits from AgentNodesBase for:
    - Configuration access (self.config)
    - Logging (self.logger)

    Example:
        >>> from config.models import VoiceAgentConfig
        >>> config = VoiceAgentConfig()
        >>> formatter = ResponseFormatter(config)
        >>>
        >>> state = {
        ...     "session_id": "sess_123",
        ...     "agent_response": "The result is 4.",
        ...     "messages": [],
        ...     "model_config": {"model": "gpt-4"},
        ...     "current_intent": "calculation",
        ...     "tool_calls": [...],
        ...     "rag_snippets": []
        ... }
        >>> result = await formatter.format_response(state)
        >>> result["should_continue"]
        False  # Conversation turn complete
        >>> len(result["messages"])
        1  # Assistant message added
    """

    async def format_response(self, state: AgentState) -> AgentState:
        """
        Format final response.

        This is the last node in the processing flow, responsible for:
        1. Ensuring response content exists
        2. Creating assistant message object
        3. Adding metadata
        4. Marking conversation turn as complete

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - agent_response: LLM-generated response text
                - messages: Conversation history to append to
                - model_config: Model configuration for metadata
                - current_intent: User intent for metadata
                - tool_calls: Tool usage history for metadata
                - rag_snippets: RAG snippets used for metadata
                - error_state: Optional error message

        Returns:
            Final conversation state with:
                - messages: Assistant message appended
                - last_activity: Updated timestamp
                - should_continue: Set to False (conversation complete)
                - next_action: Set to None (no further processing)

        Side Effects:
            - Appends assistant message to state["messages"]
            - Updates state["last_activity"] timestamp
            - Logs debug information

        Fallback Behavior:
            If agent_response is missing or empty:
            - If error_state exists: "抱歉，处理您的请求时出现了错误。"
            - Otherwise: "我不太确定如何回答，请换个方式问我吧。"

        Example:
            >>> state = {
            ...     "session_id": "sess_001",
            ...     "agent_response": "Hello! How can I help?",
            ...     "messages": [],
            ...     "model_config": {"model": "gpt-4"},
            ... }
            >>> result = await formatter.format_response(state)
            >>> result["messages"][-1].role
            MessageRole.ASSISTANT
            >>> result["messages"][-1].content
            "Hello! How can I help?"
        """
        try:
            self.logger.debug(f"格式化会话 {state['session_id']} 的响应")

            # ================================================================
            # Step 1: Ensure response content exists
            # ================================================================
            if not state.get("agent_response") or not state["agent_response"].strip():
                # Provide fallback response
                if state.get("error_state"):
                    state["agent_response"] = "抱歉，处理您的请求时出现了错误。"
                    self.logger.warning(
                        f"Using error fallback response due to: {state['error_state']}"
                    )
                else:
                    state["agent_response"] = "我不太确定如何回答，请换个方式问我吧。"
                    self.logger.warning(
                        "Using default fallback response (agent_response was empty)"
                    )

            # ================================================================
            # Step 2: Create assistant message with metadata
            # ================================================================
            assistant_message = ConversationMessage(
                id=self._generate_message_id(state),
                role=MessageRole.ASSISTANT,
                content=state["agent_response"],
                metadata=self._build_response_metadata(state)
            )

            # ================================================================
            # Step 3: Add to conversation history
            # ================================================================
            state["messages"].append(assistant_message)

            # ================================================================
            # Step 4: Update activity timestamp
            # ================================================================
            state["last_activity"] = datetime.now()

            # ================================================================
            # Step 5: Mark conversation turn as complete
            # ================================================================
            state["should_continue"] = False
            state["next_action"] = None

            self.logger.debug(
                f"响应格式化完成: {len(state['agent_response'])} 字符"
            )

            return state

        except Exception as e:
            # ================================================================
            # Error Handling
            # ================================================================
            self.logger.error(f"响应格式化错误: {e}", exc_info=True)

            state["error_state"] = f"response_formatting_error: {str(e)}"
            state["agent_response"] = "抱歉，响应格式化时出现了问题。"
            state["should_continue"] = False
            state["next_action"] = None

            return state

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _generate_message_id(self, state: AgentState) -> str:
        """
        Generate unique message ID for assistant message.

        Format: assistant_{sequence}_{timestamp}

        Args:
            state: Conversation state with messages list

        Returns:
            Unique message identifier string

        Example:
            >>> state = {"messages": [msg1, msg2]}
            >>> formatter._generate_message_id(state)
            "assistant_3_1705305600"
        """
        sequence = len(state.get("messages", [])) + 1
        timestamp = int(datetime.now().timestamp())
        return f"assistant_{sequence}_{timestamp}"

    def _build_response_metadata(self, state: AgentState) -> dict:
        """
        Build comprehensive metadata for assistant message.

        Includes:
        - generated_at: ISO timestamp of response generation
        - model: Model name used for generation
        - intent: Detected user intent
        - tool_calls_count: Number of tool calls made
        - rag_snippets: RAG snippets used (if any)

        Args:
            state: Conversation state with relevant metadata fields

        Returns:
            Metadata dictionary

        Example:
            >>> state = {
            ...     "model_config": {"model": "gpt-4"},
            ...     "current_intent": "search",
            ...     "tool_calls": [call1, call2],
            ...     "rag_snippets": [snippet1]
            ... }
            >>> formatter._build_response_metadata(state)
            {
                "generated_at": "2025-01-15T10:30:00.123456",
                "model": "gpt-4",
                "intent": "search",
                "tool_calls_count": 2,
                "rag_snippets": [...]
            }
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "model": state.get("model_config", {}).get("model", "unknown"),
            "intent": state.get("current_intent"),
            "tool_calls_count": len(state.get("tool_calls", [])),
            "rag_snippets": state.get("rag_snippets", []),
        }


# ============================================================================
# Convenience Functions
# ============================================================================

async def format_response(state: AgentState, config=None, trace=None) -> AgentState:
    """
    Convenience function for formatting response without creating ResponseFormatter instance.

    Args:
        state: Current conversation state
        config: Voice agent configuration (required)
        trace: Optional trace emitter

    Returns:
        Updated conversation state with formatted response

    Raises:
        ValueError: If config is not provided

    Example:
        >>> from config.settings import load_config
        >>> config = load_config()
        >>> state = {"agent_response": "Hello!", "messages": [], ...}
        >>> result = await format_response(state, config=config)
        >>> result["should_continue"]
        False
    """
    if config is None:
        raise ValueError("config is required for format_response()")

    formatter = ResponseFormatter(config, trace=trace)
    return await formatter.format_response(state)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ResponseFormatter",
    "format_response",  # Convenience function
]
