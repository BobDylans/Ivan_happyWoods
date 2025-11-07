"""
Tool Handler Module

This module handles tool call execution for the voice agent.
It orchestrates the complete tool execution flow:
1. Execute all pending tool calls
2. Collect tool execution results
3. Persist tool calls to database (optional)
4. Add results to conversation history
5. Prepare for next LLM call (multi-turn support)

This module integrates with MCP (Model Context Protocol) tool registry
for dynamic tool discovery and execution.
"""

import json
import logging
from typing import Optional, List
from datetime import datetime

from .base import AgentNodesBase, DateTimeJSONEncoder
from ..state import AgentState, ConversationMessage, MessageRole, ToolCall, ToolResult


logger = logging.getLogger(__name__)


# ============================================================================
# Tool Name Mapping (LLM → MCP)
# ============================================================================

# Map common LLM tool names to MCP tool registry names
# This handles differences in tool naming conventions between LLMs
TOOL_NAME_MAPPING = {
    "search_tool": "web_search",
    "web_search": "web_search",
    "calculator": "calculator",
    "time_tool": "get_time",
    "get_time": "get_time",
    "weather": "get_weather",
    "get_weather": "get_weather",
}


# ============================================================================
# Tool Handler Class
# ============================================================================

class ToolHandler(AgentNodesBase):
    """
    Tool handler node for executing tool calls.

    This class handles the complete tool execution flow:
    1. Executes all pending tool calls from state
    2. Collects execution results
    3. Persists tool calls to database (optional)
    4. Adds results to conversation history
    5. Prepares state for next LLM call (multi-turn tool support)

    Inherits from AgentNodesBase for:
    - Configuration access (self.config)
    - Logging (self.logger)
    - HTTP client (if needed for tool execution)

    Example:
        >>> from config.models import VoiceAgentConfig
        >>> config = VoiceAgentConfig()
        >>> handler = ToolHandler(config)
        >>>
        >>> state = {
        ...     "session_id": "sess_123",
        ...     "pending_tool_calls": [
        ...         ToolCall(id="call_1", name="calculator", arguments={"expression": "2+2"})
        ...     ],
        ...     "tool_results": [],
        ...     "tool_calls": [],
        ...     "messages": []
        ... }
        >>> result = await handler.handle_tools(state)
        >>> result["next_action"]
        "call_llm"  # Returns to LLM for re-evaluation
    """

    async def handle_tools(self, state: AgentState) -> AgentState:
        """
        Handle tool call requests.

        🆕 Optimized version: Supports multi-turn tool calls

        When LLM needs to use tools, this node:
        1. Executes all pending tool calls
        2. Collects tool execution results
        3. Adds results to conversation history
        4. 🆕 Increments tool call counter
        5. Prepares to call LLM again (let it re-think based on tool results)

        Multi-turn support: After tools execute, control returns to LLM.
        The LLM can then decide whether to call more tools or generate final response.

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - pending_tool_calls: List of ToolCall objects to execute
                - tool_results: List to append results to
                - tool_calls: List to append executed calls to
                - messages: Conversation history to append tool messages
                - tool_call_count: Counter for multi-turn tracking

        Returns:
            Updated conversation state with:
                - tool_results: Appended with execution results
                - tool_calls: Appended with executed calls
                - messages: Appended with tool result messages
                - pending_tool_calls: Cleared
                - tool_call_count: Incremented
                - next_action: Set to "call_llm" (return to LLM)

        Side Effects:
            - Executes tool calls via MCP registry
            - Persists tool calls to database (if available)
            - Logs execution progress

        Example:
            >>> state = {
            ...     "session_id": "sess_001",
            ...     "pending_tool_calls": [
            ...         ToolCall(id="call_1", name="web_search", arguments={"query": "Python"})
            ...     ],
            ...     "tool_results": [],
            ...     "tool_calls": [],
            ...     "messages": []
            ... }
            >>> result = await handler.handle_tools(state)
            >>> len(result["tool_results"])
            1
            >>> result["tool_results"][0].success
            True
        """
        try:
            self.logger.debug(f"处理会话 {state['session_id']} 的工具调用")

            # ================================================================
            # Step 1: Validate pending tool calls
            # ================================================================
            if not state.get("pending_tool_calls"):
                self.logger.warning("没有待处理的工具调用")
                state["next_action"] = "call_llm"
                return state

            # ================================================================
            # Step 2: Increment tool call counter (multi-turn support)
            # ================================================================
            state["tool_call_count"] = state.get("tool_call_count", 0) + 1
            current_iteration = state["tool_call_count"]

            self.logger.info(
                f"🔧 第 {current_iteration} 轮工具调用，"
                f"待执行工具数: {len(state['pending_tool_calls'])}"
            )

            # ================================================================
            # Step 3: Execute all pending tool calls
            # ================================================================
            for tool_call in state["pending_tool_calls"]:
                # Execute tool
                result = await self._execute_tool_call(tool_call)

                # Collect results
                state["tool_results"].append(result)
                state["tool_calls"].append(tool_call)

                self.logger.info(
                    f"  ✅ 工具 '{tool_call.name}' 执行完成: "
                    f"{'成功' if result.success else '失败'}"
                )

                # ============================================================
                # Step 4: Persist to database (optional, non-blocking)
                # ============================================================
                await self._save_tool_call_to_database(
                    session_id=state["session_id"],
                    tool_call=tool_call,
                    result=result
                )

            # ================================================================
            # Step 5: Clear pending queue
            # ================================================================
            executed_count = len(state["pending_tool_calls"])
            state["pending_tool_calls"] = []

            # ================================================================
            # Step 6: Add tool results to conversation history
            # ================================================================
            # Add results from the last executed batch
            for result in state["tool_results"][-executed_count:]:
                tool_message = ConversationMessage(
                    id=f"tool_{result.call_id}_{int(datetime.now().timestamp())}",
                    role=MessageRole.TOOL,
                    content=json.dumps(result.dict(), cls=DateTimeJSONEncoder),
                    metadata={
                        "tool_call_id": result.call_id,
                        "success": result.success
                    }
                )
                state["messages"].append(tool_message)

            # ================================================================
            # Step 7: Return to LLM for re-evaluation
            # ================================================================
            # 🆕 Core change: After tool execution, return to LLM
            # LLM will decide based on tool results whether to:
            # - Call more tools
            # - Generate final response
            state["next_action"] = "call_llm"

            self.logger.info(
                f"🔄 第 {current_iteration} 轮工具调用完成，"
                f"返回 LLM 重新评估"
            )

            return state

        except Exception as e:
            # ================================================================
            # Error Handling
            # ================================================================
            self.logger.error(f"工具处理错误: {e}", exc_info=True)
            state["error_state"] = f"tool_handling_error: {str(e)}"
            state["agent_response"] = "抱歉，在使用工具时遇到了问题，让我换个方式帮您。"

            # Even on error, return to LLM for fallback response
            state["next_action"] = "call_llm"
            return state

    # ========================================================================
    # Tool Execution
    # ========================================================================

    async def _execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call using MCP tool registry.

        This method attempts to execute the tool call through MCP registry.
        If MCP is not available or tool execution fails, it falls back to
        placeholder implementations for common tools.

        Args:
            tool_call: ToolCall object containing:
                - id: Unique tool call identifier
                - name: Tool name (may need mapping to MCP name)
                - arguments: Tool arguments dictionary

        Returns:
            ToolResult object containing:
                - call_id: Same as tool_call.id
                - success: True if execution succeeded
                - result: Tool output (JSON string or None)
                - error: Error message if failed

        Execution Flow:
            1. Try MCP tool registry (primary path)
            2. Map LLM tool name to MCP tool name
            3. Execute through registry
            4. Convert MCP result to agent ToolResult
            5. If MCP unavailable, use fallback placeholders

        Example:
            >>> tool_call = ToolCall(
            ...     id="call_123",
            ...     name="calculator",
            ...     arguments={"expression": "2+2"}
            ... )
            >>> result = await handler._execute_tool_call(tool_call)
            >>> result.success
            True
            >>> result.result
            '{"value": 4}'
        """
        try:
            # ================================================================
            # Primary Path: MCP Tool Registry
            # ================================================================
            try:
                from mcp import get_tool_registry

                registry = get_tool_registry()

                # Map LLM tool name to MCP tool name
                mcp_tool_name = TOOL_NAME_MAPPING.get(
                    tool_call.name,
                    tool_call.name  # Use original name if no mapping
                )

                self.logger.debug(
                    f"🔧 Executing tool via MCP: {tool_call.name} → {mcp_tool_name}"
                )

                # Execute through registry
                result_dict = await registry.execute(
                    mcp_tool_name,
                    **tool_call.arguments
                )

                # Convert MCP ToolResult to Agent ToolResult
                if result_dict.get("success"):
                    result_str = json.dumps(
                        result_dict.get("data", {}),
                        ensure_ascii=False
                    )
                else:
                    result_str = None

                return ToolResult(
                    call_id=tool_call.id,
                    success=result_dict.get("success", False),
                    result=result_str,
                    error=result_dict.get("error")
                )

            except ImportError:
                self.logger.warning(
                    "MCP tools not available, using fallback implementation"
                )
                # Fall through to fallback implementation
                pass

            # ================================================================
            # Fallback Path: Placeholder Implementations
            # ================================================================
            self.logger.debug(f"🔧 Executing tool via fallback: {tool_call.name}")

            if tool_call.name in ["search_tool", "web_search"]:
                query = tool_call.arguments.get('query', 'unknown')
                result = f"Search results for: {query} (fallback placeholder)"

            elif tool_call.name == "calculator":
                expression = tool_call.arguments.get('expression', '')
                try:
                    # Simple eval for basic math (UNSAFE for production!)
                    # In production, use a proper math parser
                    result = f"The result is: {expression} (calculation placeholder)"
                except Exception as calc_error:
                    result = f"Could not calculate: {calc_error}"

            elif tool_call.name in ["time_tool", "get_time"]:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                result = f"Current time: {current_time}"

            else:
                # Generic placeholder
                result = (
                    f"Tool '{tool_call.name}' executed with "
                    f"arguments: {tool_call.arguments} (placeholder)"
                )

            return ToolResult(
                call_id=tool_call.id,
                success=True,
                result=result
            )

        except Exception as e:
            # ================================================================
            # Error Handling
            # ================================================================
            self.logger.error(
                f"Tool execution error for '{tool_call.name}': {e}",
                exc_info=True
            )

            return ToolResult(
                call_id=tool_call.id,
                success=False,
                result=None,
                error=str(e)
            )

    # ========================================================================
    # Database Persistence
    # ========================================================================

    async def _save_tool_call_to_database(
        self,
        session_id: str,
        tool_call: ToolCall,
        result: ToolResult
    ) -> None:
        """
        Save tool call record to database.

        This method persists tool call information for:
        - Analytics and debugging
        - Conversation history reconstruction
        - Tool usage tracking

        The method is non-blocking - if database save fails, it logs the error
        but doesn't propagate the exception to avoid interrupting the conversation flow.

        Args:
            session_id: Session identifier
            tool_call: ToolCall object with id, name, arguments
            result: ToolResult object with success, result, error

        Side Effects:
            - Creates database session
            - Saves tool call record via ToolCallRepository
            - Commits transaction
            - Logs success/failure

        Database Access:
            Currently accesses database engine via api.main.app.state.db_engine
            (TODO: Improve to use dependency injection from core.dependencies)

        Example:
            >>> tool_call = ToolCall(id="call_1", name="calculator", arguments={"expression": "2+2"})
            >>> result = ToolResult(call_id="call_1", success=True, result="4")
            >>> await handler._save_tool_call_to_database("sess_123", tool_call, result)
            # Logs: "💾 工具调用已保存到数据库: calculator (session: sess_123)"
        """
        try:
            # ================================================================
            # Import Dependencies
            # ================================================================
            from database.repositories import ToolCallRepository
            from sqlalchemy.ext.asyncio import AsyncSession

            # ================================================================
            # Get Database Engine
            # ================================================================
            # TODO: Improve this to use dependency injection
            # Current approach accesses global app.state, which is not ideal
            # Better: Pass db_engine/session_factory via constructor or method parameter
            try:
                from api.main import app

                if not hasattr(app.state, 'db_engine'):
                    self.logger.debug(
                        "⚠️ app.state.db_engine 不存在，跳过保存工具调用 "
                        "(数据库未初始化或已禁用)"
                    )
                    return

                db_engine = app.state.db_engine

                if db_engine is None:
                    self.logger.debug(
                        "⚠️ db_engine is None，跳过保存工具调用"
                    )
                    return

            except Exception as import_error:
                self.logger.debug(
                    f"⚠️ 无法获取全局数据库引擎，跳过保存工具调用: {import_error}"
                )
                return

            # ================================================================
            # Prepare Tool Call Data
            # ================================================================
            execution_time_ms = None  # TODO: Track execution time if needed

            if result.success and result.result:
                try:
                    result_data = {"data": result.result, "success": True}
                except Exception:
                    result_data = {"data": str(result.result), "success": True}
            else:
                result_data = {"success": False, "error": result.error}

            # ================================================================
            # Save to Database
            # ================================================================
            async with AsyncSession(db_engine) as db_session:
                tool_call_repo = ToolCallRepository(db_session)

                await tool_call_repo.save_tool_call(
                    session_id=session_id,
                    tool_name=tool_call.name,
                    parameters=tool_call.arguments,
                    result=result_data,
                    execution_time_ms=execution_time_ms
                )

                # Commit transaction
                await db_session.commit()

                self.logger.info(
                    f"💾 工具调用已保存到数据库: {tool_call.name} "
                    f"(session: {session_id})"
                )

        except Exception as e:
            # ================================================================
            # Error Handling (Non-Blocking)
            # ================================================================
            # Don't propagate exception - database save failure shouldn't
            # interrupt conversation flow
            self.logger.error(
                f"❌ 保存工具调用到数据库失败: {e}",
                exc_info=True
            )
            self.logger.error(f"   Session ID: {session_id}")
            self.logger.error(f"   Tool Name: {tool_call.name}")


# ============================================================================
# Convenience Functions
# ============================================================================

async def handle_tools(state: AgentState, config=None, trace=None) -> AgentState:
    """
    Convenience function for handling tools without creating ToolHandler instance.

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
        >>> state = {"pending_tool_calls": [...], ...}
        >>> result = await handle_tools(state, config=config)
    """
    if config is None:
        raise ValueError("config is required for handle_tools()")

    handler = ToolHandler(config, trace=trace)
    return await handler.handle_tools(state)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ToolHandler",
    "handle_tools",  # Convenience function
    "TOOL_NAME_MAPPING",  # For testing/documentation
]
