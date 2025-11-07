"""
Input Processor Module

This module handles user input processing and validation,
serving as the entry point for the conversation flow.

Responsibilities:
- Validate user input (non-empty check)
- Create conversation message objects
- Analyze user intent (keyword-based)
- Update state for next processing stage

This is extracted from the original nodes.py process_input() function.
"""

import logging
from typing import Optional
from datetime import datetime

from .base import AgentNodesBase
from ..state import AgentState, ConversationMessage, MessageRole


logger = logging.getLogger(__name__)


class InputProcessor(AgentNodesBase):
    """Input processing node for conversation flow.

    This class handles the first stage of conversation processing:
    1. Input validation (ensure non-empty)
    2. User message creation and history update
    3. Intent analysis (keyword-based)
    4. State preparation for LLM call

    Inherits from AgentNodesBase to access configuration and logging.

    Example:
        >>> from config.models import VoiceAgentConfig
        >>> config = VoiceAgentConfig()
        >>> processor = InputProcessor(config)
        >>>
        >>> state = {
        ...     "session_id": "session_123",
        ...     "user_input": "What is the weather today?",
        ...     "messages": [],
        ... }
        >>> result = await processor.process_input(state)
        >>> result["current_intent"]
        "general_conversation"
        >>> len(result["messages"])
        1
    """

    async def process_input(self, state: AgentState) -> AgentState:
        """Process and validate user input.

        This is the entry node for conversation processing flow, responsible for:
        1. Validating input is not empty
        2. Creating user message object
        3. Analyzing user intent
        4. Updating state to prepare for LLM call

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - user_input: Raw user input string
                - messages: Conversation history list
                - last_activity: Timestamp of last activity (updated here)

        Returns:
            Updated conversation state with:
                - messages: User message appended
                - current_intent: Analyzed intent label
                - next_action: Set to "call_llm"
                - error_state: Set if validation fails
                - should_continue: False if error occurred
                - agent_response: Error message if validation fails

        Side Effects:
            - Appends user message to state["messages"]
            - Updates state["last_activity"] timestamp
            - Logs debug/error messages

        Example:
            >>> state = {
            ...     "session_id": "sess_001",
            ...     "user_input": "search for Python tutorials",
            ...     "messages": [],
            ... }
            >>> result = await processor.process_input(state)
            >>> result["current_intent"]
            "search"
            >>> result["next_action"]
            "call_llm"
        """
        session_id = state.get('session_id', 'unknown')

        try:
            self.logger.debug(f"处理会话 {session_id} 的输入")

            # 🆕 思考阶段：验证输入
            if self.trace:
                # Note: We can't yield here because process_input returns state synchronously
                # Just log, actual events are emitted at Graph layer
                self.logger.debug(f"[Trace] process_input: 验证用户输入")

            # Update activity timestamp
            state["last_activity"] = datetime.now()

            # Normalize input, ensure not empty
            user_input = state["user_input"].strip()
            if not user_input:
                state["error_state"] = "empty_input"
                state["should_continue"] = False
                state["agent_response"] = "我没有收到任何输入，请说点什么吧。"
                return state

            # Add user message to conversation history
            user_message = ConversationMessage(
                id=f"user_{len(state['messages']) + 1}_{int(datetime.now().timestamp())}",
                role=MessageRole.USER,
                content=user_input,
                metadata={"processed_at": datetime.now().isoformat()}
            )
            state["messages"].append(user_message)

            # Analyze user intent based on keywords
            state["current_intent"] = self._analyze_intent(user_input)

            # Set next action: call LLM
            state["next_action"] = "call_llm"

            self.logger.debug(f"输入处理完成，意图: {state['current_intent']}")
            return state

        except Exception as e:
            self.logger.error(f"输入处理错误: {e}")
            state["error_state"] = f"input_processing_error: {str(e)}"
            state["should_continue"] = False
            return state

    def _analyze_intent(self, user_input: str) -> Optional[str]:
        """Analyze user intent (simple keyword-based implementation).

        Note: This is a simplified version of intent recognition, only for basic
        classification. Production environments should use NLU models or LLM for
        intent recognition.

        The intent analysis helps optimize system prompts and tool selection by
        providing context hints about what the user wants to do.

        Args:
            user_input: User input text

        Returns:
            Identified intent label, such as:
            - "search": Information lookup, search queries
            - "calculation": Math, computation requests
            - "time_query": Time/date questions
            - "image_generation": Image creation requests
            - "help_request": Help or how-to questions
            - "general_conversation": Default conversational intent

        Example:
            >>> processor._analyze_intent("search for latest news")
            "search"
            >>> processor._analyze_intent("calculate 2+2")
            "calculation"
            >>> processor._analyze_intent("hello there")
            "general_conversation"
            >>> processor._analyze_intent("搜索Python教程")
            "search"
        """
        input_lower = user_input.lower()

        # Simple keyword-based intent detection
        if any(word in input_lower for word in ["search", "find", "look", "搜索", "查找"]):
            return "search"
        elif any(word in input_lower for word in ["calculate", "math", "compute", "计算"]):
            return "calculation"
        elif any(word in input_lower for word in ["time", "date", "when", "时间", "日期"]):
            return "time_query"
        elif any(word in input_lower for word in ["image", "picture", "generate", "create", "图片", "生成"]):
            return "image_generation"
        elif any(word in input_lower for word in ["help", "what", "how", "帮助", "怎么"]):
            return "help_request"
        else:
            return "general_conversation"


# ============================================================================
# Convenience Functions (for backward compatibility)
# ============================================================================

async def process_input(state: AgentState, config=None, trace=None) -> AgentState:
    """Convenience function for processing input without creating InputProcessor instance.

    Args:
        state: Current conversation state
        config: Voice agent configuration (required)
        trace: Optional trace emitter

    Returns:
        Updated conversation state

    Raises:
        ValueError: If config is not provided

    Example:
        >>> from config.settings import load_config
        >>> config = load_config()
        >>> state = {"user_input": "Hello", "messages": [], "session_id": "test"}
        >>> result = await process_input(state, config=config)
    """
    if config is None:
        raise ValueError("config is required for process_input()")

    processor = InputProcessor(config, trace=trace)
    return await processor.process_input(state)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "InputProcessor",
    "process_input",  # Convenience function
]
