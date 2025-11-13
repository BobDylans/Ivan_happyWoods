"""
Agent Nodes Package (Refactored)

This package contains the refactored components of the original monolithic nodes.py file.
The original 1927-line file has been split into specialized modules following Single
Responsibility Principle:

Specialized Modules:
- base.py: Base class, HTTP client, RAG service, resource management
- input_processor.py: User input processing and intent analysis
- message_builder.py: LLM message preparation utilities
- llm_caller.py: Non-streaming LLM API calls
- llm_streamer.py: Streaming LLM API calls with tool support
- tool_handler.py: Tool execution and database persistence
- response_formatter.py: Response formatting and message creation

This __init__.py serves as the aggregation layer, providing the main AgentNodes
class that delegates to specialized modules while maintaining backward compatibility.

Usage:
    # Main aggregation class (backward compatible)
    from agent.nodes import AgentNodes
    nodes = AgentNodes(config)
    result = await nodes.process_input(state)

    # Or import specialized classes directly
    from agent.nodes import InputProcessor, LLMCaller, ToolHandler
    processor = InputProcessor(config)
    result = await processor.process_input(state)

    # Or use convenience functions
    from agent.nodes import process_input, call_llm, handle_tools
    result = await process_input(state, config=config)
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

# Import state definitions (from parent package)
from ..state import AgentState

# Import configuration
try:
    from config.models import VoiceAgentConfig
except ImportError:
    # Fallback for when running as script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config.models import VoiceAgentConfig


logger = logging.getLogger(__name__)


# ============================================================================
# Import All Specialized Classes
# ============================================================================

from .base import AgentNodesBase, DateTimeJSONEncoder
from .input_processor import InputProcessor
from .message_builder import prepare_llm_messages
from .llm_caller import LLMCaller
from .llm_streamer import LLMStreamer
from .tool_handler import ToolHandler
from .response_formatter import ResponseFormatter

# ============================================================================
# Import All Convenience Functions
# ============================================================================

from .input_processor import process_input
from .llm_caller import call_llm
from .llm_streamer import stream_llm_call
from .tool_handler import handle_tools
from .response_formatter import format_response


# ============================================================================
# AgentNodes Aggregation Class
# ============================================================================

class AgentNodes:
    """
    LangGraph conversation processing node collection (Refactored).

    This class serves as the main entry point for conversation processing,
    delegating to specialized modules for each stage:
    - Input processing and validation → InputProcessor
    - LLM calls (sync/streaming) → LLMCaller / LLMStreamer
    - Tool call handling → ToolHandler
    - Response formatting → ResponseFormatter

    The interface remains identical to the original monolithic implementation
    for backward compatibility, but internally uses modular components.

    Example:
        >>> from config.models import VoiceAgentConfig
        >>> config = VoiceAgentConfig()
        >>> nodes = AgentNodes(config)
        >>>
        >>> # Use as async context manager (recommended)
        >>> async with nodes:
        ...     state = {"user_input": "Hello", "messages": [], ...}
        ...     result = await nodes.process_input(state)
        ...     result = await nodes.call_llm(result)
        ...     result = await nodes.format_response(result)
        >>>
        >>> # Or manage cleanup manually
        >>> nodes = AgentNodes(config)
        >>> result = await nodes.process_input(state)
        >>> await nodes.cleanup()

    Attributes:
        config (VoiceAgentConfig): Voice agent configuration
        trace: Optional trace emitter for visualization
        _input_processor (InputProcessor): Input processing delegate
        _llm_caller (LLMCaller): LLM calling delegate
        _llm_streamer (LLMStreamer): LLM streaming delegate
        _tool_handler (ToolHandler): Tool handling delegate
        _response_formatter (ResponseFormatter): Response formatting delegate
    """

    def __init__(
        self,
        config: VoiceAgentConfig,
        trace=None,
        *,
        observability=None,
        tool_call_persister=None,
        tool_registry=None,
    ):
        """
        Initialize agent nodes with configuration.

        Args:
            config: Voice agent configuration object
            trace: Optional TraceEmitter instance for visualization events
            observability: Optional Observability tracker for metrics
            tool_call_persister: Optional callable for persisting tool calls
            tool_registry: Optional ToolRegistry instance for tool access

        Side Effects:
            - Creates instances of all specialized node modules
            - Initializes HTTP client (lazy, on first use)
            - Initializes RAG service if enabled in config
        """
        self.config = config
        self.logger = logger
        self.trace = trace

        # ====================================================================
        # Initialize Specialized Node Modules
        # ====================================================================
        # Each module inherits from AgentNodesBase and shares:
        # - Configuration (self.config)
        # - Logging (self.logger)
        # - HTTP client (lazy-initialized, shared)
        # - RAG service (if enabled)
        # - Resource management (cleanup via __aenter__/__aexit__)
        # - Tool registry (for tool list access)

        self._input_processor = InputProcessor(config, trace=trace, observability=observability, tool_registry=tool_registry)
        self._llm_caller = LLMCaller(config, trace=trace, observability=observability, tool_registry=tool_registry)
        self._llm_streamer = LLMStreamer(config, trace=trace, observability=observability, tool_registry=tool_registry)
        self._tool_handler = ToolHandler(
            config,
            trace=trace,
            observability=observability,
            tool_call_persister=tool_call_persister,
            tool_registry=tool_registry,
        )
        self._response_formatter = ResponseFormatter(config, trace=trace, observability=observability, tool_registry=tool_registry)

        self.logger.debug("AgentNodes initialized with modular architecture")

    # ========================================================================
    # Resource Management
    # ========================================================================

    async def cleanup(self):
        """
        Clean up resources.

        Closes HTTP client connections and releases resources.
        Should be called when the program exits or service stops.

        Side Effects:
            - Closes HTTP clients in all specialized modules
            - Closes RAG service connections
            - Logs cleanup progress and errors
        """
        self.logger.debug("Cleaning up AgentNodes resources...")

        # Cleanup all specialized modules
        # Each module has its own cleanup() method from AgentNodesBase
        try:
            await self._input_processor.cleanup()
        except Exception as e:
            self.logger.warning(f"Error cleaning up InputProcessor: {e}")

        try:
            await self._llm_caller.cleanup()
        except Exception as e:
            self.logger.warning(f"Error cleaning up LLMCaller: {e}")

        try:
            await self._llm_streamer.cleanup()
        except Exception as e:
            self.logger.warning(f"Error cleaning up LLMStreamer: {e}")

        try:
            await self._tool_handler.cleanup()
        except Exception as e:
            self.logger.warning(f"Error cleaning up ToolHandler: {e}")

        try:
            await self._response_formatter.cleanup()
        except Exception as e:
            self.logger.warning(f"Error cleaning up ResponseFormatter: {e}")

        self.logger.debug("AgentNodes cleanup completed")

    async def __aenter__(self):
        """Async context manager entry point."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit point, automatically cleans up resources."""
        await self.cleanup()

    # ========================================================================
    # Public Node Methods (LangGraph Entry Points)
    # ========================================================================
    # These methods maintain the same interface as the original monolithic
    # implementation but delegate to specialized modules internally.

    async def process_input(self, state: AgentState) -> AgentState:
        """
        Process and validate user input.

        This is the entry node for conversation processing flow.
        Delegates to InputProcessor module.

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - user_input: Raw user input string
                - messages: Conversation history list

        Returns:
            Updated conversation state with:
                - messages: User message appended
                - current_intent: Analyzed intent label
                - next_action: Set to "call_llm"
                - error_state: Set if validation fails

        Example:
            >>> state = {"user_input": "Hello", "messages": [], "session_id": "test"}
            >>> result = await nodes.process_input(state)
            >>> result["current_intent"]
            "general_conversation"
            >>> result["next_action"]
            "call_llm"
        """
        return await self._input_processor.process_input(state)

    async def call_llm(self, state: AgentState) -> AgentState:
        """
        Call LLM to generate response (non-streaming).

        This is the core processing node for LLM invocation.
        Delegates to LLMCaller module.

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - messages: Conversation history
                - model_config: Model configuration override
                - external_history: Optional external history from SessionManager

        Returns:
            Updated conversation state with:
                - next_action: "handle_tools" if tools called, "format_response" if text
                - agent_response: LLM response text (if no tools)
                - pending_tool_calls: Tool calls to execute (if tools requested)
                - error_state: Error message if call failed

        Example:
            >>> result = await nodes.call_llm(state)
            >>> if result["next_action"] == "handle_tools":
            ...     result = await nodes.handle_tools(result)
            ... else:
            ...     result = await nodes.format_response(result)
        """
        return await self._llm_caller.call_llm(state)

    async def stream_llm_call(
        self,
        state: AgentState,
        external_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream LLM response with tool execution support.

        This generator yields SSE events as the LLM generates its response.
        Delegates to LLMStreamer module.

        Args:
            state: Current conversation state
            external_history: Optional external message history from SessionHistoryManager

        Yields:
            Event dictionaries in SSE format:
            - {"type": "start", "session_id": "...", ...}
            - {"type": "delta", "content": "Hello", "session_id": "...", ...}
            - {"type": "tool_calls", "tool_calls": [...], "session_id": "...", ...}
            - {"type": "end", "content": "Full response", "session_id": "...", ...}
            - {"type": "error", "error": "Error message", "session_id": "...", ...}

        Example:
            >>> async for event in nodes.stream_llm_call(state):
            ...     if event["type"] == "delta":
            ...         print(event["content"], end="", flush=True)
            ...     elif event["type"] == "tool_calls":
            ...         print(f"\\nExecuting {len(event['tool_calls'])} tools...")
        """
        async for event in self._llm_streamer.stream_llm_call(state, external_history):
            yield event

    async def handle_tools(self, state: AgentState) -> AgentState:
        """
        Handle tool call requests.

        Executes all pending tool calls and prepares state for LLM re-evaluation.
        Delegates to ToolHandler module.

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - pending_tool_calls: List of ToolCall objects to execute
                - tool_results: List to append results to
                - messages: Conversation history

        Returns:
            Updated conversation state with:
                - tool_results: Appended with execution results
                - tool_calls: Appended with executed calls
                - messages: Appended with tool result messages
                - pending_tool_calls: Cleared
                - next_action: Set to "call_llm" (return to LLM)

        Example:
            >>> result = await nodes.handle_tools(state)
            >>> result["next_action"]
            "call_llm"  # Returns to LLM for re-evaluation
            >>> len(result["tool_results"])
            3  # Three tools were executed
        """
        return await self._tool_handler.handle_tools(state)

    def configure_tool_persistence(self, persister) -> None:
        """Configure tool call persistence after initialization."""
        self._tool_handler.set_tool_call_persister(persister)

    async def format_response(self, state: AgentState) -> AgentState:
        """
        Format final response.

        This is the last node in the processing flow.
        Delegates to ResponseFormatter module.

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - agent_response: LLM-generated response text
                - messages: Conversation history
                - model_config: Model configuration

        Returns:
            Final conversation state with:
                - messages: Assistant message appended
                - last_activity: Updated timestamp
                - should_continue: Set to False (conversation complete)
                - next_action: Set to None (no further processing)

        Example:
            >>> result = await nodes.format_response(state)
            >>> result["should_continue"]
            False  # Conversation turn complete
            >>> len(result["messages"])
            5  # User + Assistant messages added
        """
        return await self._response_formatter.format_response(state)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Main aggregation class (backward compatibility)
    "AgentNodes",

    # Base classes
    "AgentNodesBase",
    "DateTimeJSONEncoder",

    # Specialized node classes
    "InputProcessor",
    "LLMCaller",
    "LLMStreamer",
    "ToolHandler",
    "ResponseFormatter",

    # Utility functions
    "prepare_llm_messages",

    # Convenience functions (backward compatibility)
    "process_input",
    "call_llm",
    "stream_llm_call",
    "handle_tools",
    "format_response",
]


# ============================================================================
# Module Documentation
# ============================================================================

"""
Refactoring Summary:

Original Structure (1927 lines):
    - Monolithic nodes.py with all implementation
    - Single AgentNodes class with all methods
    - Prompt templates embedded in code
    - Helper methods mixed with public interface

New Structure (Modular):
    agent/
    ├── nodes/  (this package)
    │   ├── __init__.py - Aggregation layer with AgentNodes class
    │   ├── base.py - Base class, HTTP client, RAG service
    │   ├── input_processor.py - Input validation, intent analysis
    │   ├── message_builder.py - Message preparation utilities
    │   ├── llm_caller.py - Non-streaming LLM calls
    │   ├── llm_streamer.py - Streaming LLM calls with tools
    │   ├── tool_handler.py - Tool execution, database persistence
    │   └── response_formatter.py - Response finalization
    └── prompts/
        ├── __init__.py
        └── system_prompts.py - All prompt templates

Benefits:
    ✅ Single Responsibility Principle - each module has one clear purpose
    ✅ Easier Testing - test each module independently
    ✅ Better Maintainability - changes localized to specific modules
    ✅ Improved Readability - smaller, focused files
    ✅ Reusability - modules can be used independently
    ✅ Backward Compatibility - existing code continues to work

Migration Examples:

    # Original code (still works):
    from agent.nodes import AgentNodes
    nodes = AgentNodes(config)
    async with nodes:
        result = await nodes.process_input(state)
        result = await nodes.call_llm(result)

    # New code (using specialized modules directly):
    from agent.nodes import InputProcessor, LLMCaller

    processor = InputProcessor(config)
    caller = LLMCaller(config)

    async with processor, caller:
        result = await processor.process_input(state)
        result = await caller.call_llm(result)

    # Convenience functions (new):
    from agent.nodes import process_input, call_llm

    result = await process_input(state, config=config)
    result = await call_llm(result, config=config)
"""
