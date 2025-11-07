"""
LLM Streamer Module

This module handles streaming LLM API calls for the voice agent.
It provides real-time response streaming with Server-Sent Events (SSE):
1. Streams LLM responses incrementally (delta events)
2. Detects and accumulates tool calls across streaming deltas
3. Executes tools and continues streaming with results (multi-turn)
4. Emits structured events for frontend consumption
5. Falls back to non-streaming on errors

This module integrates with the event system (api.event_utils) to emit
versioned SSE events that the frontend can consume for real-time updates.
"""

import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from .base import AgentNodesBase
from .message_builder import prepare_llm_messages
from ..state import AgentState, ToolCall, MessageRole

# Import LLM compatibility layer
try:
    from utils.llm_compat import prepare_llm_params
except ImportError:
    # Fallback implementation if import fails
    def prepare_llm_params(model, messages, temperature=0.7, max_tokens=16384, **kwargs):
        params = {
            "model": model,
            "messages": messages,
        }
        # GPT-5 series doesn't use temperature, use API default
        if not model.startswith("gpt-5"):
            params["temperature"] = temperature
        # GPT-5 series uses max_completion_tokens
        if model.startswith("gpt-5"):
            params["max_completion_tokens"] = max_tokens
        else:
            params["max_tokens"] = max_tokens
        params.update(kwargs)
        return params

# Import event utilities for SSE streaming
try:
    from api.event_utils import (
        create_start_event,
        create_delta_event,
        create_end_event,
        create_error_event,
        create_tool_calls_event
    )
except ImportError:
    # Fallback implementations if event_utils not available
    def create_start_event(session_id: str, **kwargs) -> Dict[str, Any]:
        return {"type": "start", "session_id": session_id, **kwargs}

    def create_delta_event(content: str, session_id: str, **kwargs) -> Dict[str, Any]:
        return {"type": "delta", "content": content, "session_id": session_id, **kwargs}

    def create_end_event(content: str, session_id: str, **kwargs) -> Dict[str, Any]:
        return {"type": "end", "content": content, "session_id": session_id, **kwargs}

    def create_error_event(error: str, session_id: str, **kwargs) -> Dict[str, Any]:
        return {"type": "error", "error": error, "session_id": session_id, **kwargs}

    def create_tool_calls_event(tool_calls: List[Dict], session_id: str, **kwargs) -> Dict[str, Any]:
        return {"type": "tool_calls", "tool_calls": tool_calls, "session_id": session_id, **kwargs}


logger = logging.getLogger(__name__)


# ============================================================================
# LLM Streamer Class
# ============================================================================

class LLMStreamer(AgentNodesBase):
    """
    LLM streamer node for streaming API calls with tool support.

    This class handles streaming LLM invocations with full tool execution support:
    1. Streams LLM responses in real-time (SSE format)
    2. Accumulates tool calls across streaming deltas
    3. Executes tools when LLM requests them
    4. Continues streaming with tool results (multi-turn support)
    5. Emits structured events for frontend consumption

    Inherits from AgentNodesBase for:
    - HTTP client management (_http_client, _ensure_http_client)
    - RAG service integration (_rag_service, _retrieve_rag_snippets)
    - Tool execution (_execute_tool_call)
    - Configuration access (self.config)
    - Logging (self.logger)

    Event Types:
    - start: Stream started
    - delta: Incremental text content
    - tool_calls: LLM requested tool execution
    - end: Stream completed
    - error: Error occurred

    Example:
        >>> from config.models import VoiceAgentConfig
        >>> config = VoiceAgentConfig()
        >>> streamer = LLMStreamer(config)
        >>>
        >>> state = {
        ...     "session_id": "sess_123",
        ...     "user_input": "What is the weather?",
        ...     "messages": [...],
        ...     "model_config": {"model": "gpt-4"},
        ... }
        >>> async for event in streamer.stream_llm_call(state):
        ...     print(event["type"], event.get("content", ""))
    """

    async def stream_llm_call(
        self,
        state: AgentState,
        external_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream LLM response with tool execution support.

        This generator yields SSE events as the LLM generates its response.
        When the LLM requests tools, this method:
        1. Emits tool_calls event
        2. Executes all requested tools
        3. Recursively streams LLM's response based on tool results

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - messages: Conversation history
                - model_config: Model configuration
                - external_history: Optional history from SessionManager
                - user_input: Current user input

            external_history: Optional external message history from SessionHistoryManager
                If provided, this takes priority over state["messages"]

        Yields:
            Event dictionaries in SSE format:
            - {"type": "start", "session_id": "...", ...}
            - {"type": "delta", "content": "Hello", "session_id": "...", ...}
            - {"type": "tool_calls", "tool_calls": [...], "session_id": "...", ...}
            - {"type": "end", "content": "Full response", "session_id": "...", ...}
            - {"type": "error", "error": "Error message", "session_id": "...", ...}

        Side Effects:
            - Retrieves RAG snippets and updates state["rag_snippets"]
            - Executes tool calls via MCP registry
            - Updates state["messages"] with assistant and tool messages
            - Logs streaming progress and errors

        Example:
            >>> async for event in streamer.stream_llm_call(state):
            ...     if event["type"] == "delta":
            ...         print(event["content"], end="", flush=True)
            ...     elif event["type"] == "tool_calls":
            ...         print(f"\\nExecuting {len(event['tool_calls'])} tools...")
        """
        session_id = state.get("session_id", "unknown")

        try:
            self.logger.debug(f"为会话 {session_id} 开始流式调用 LLM")

            # ================================================================
            # Step 1: Retrieve RAG snippets (if enabled)
            # ================================================================
            rag_results = await self._retrieve_rag_snippets(state)

            # ================================================================
            # Step 2: Prepare message list (system prompt + history)
            # ================================================================
            if external_history is None:
                external_history = state.get("external_history")

            messages = prepare_llm_messages(state, external_history=external_history)

            # ================================================================
            # Step 3: Inject RAG context (if available)
            # ================================================================
            if rag_results and self._rag_service:
                rag_prompt = self._rag_service.build_prompt(rag_results)
                if rag_prompt:
                    system_message = {"role": "system", "content": rag_prompt}
                    if messages and messages[-1].get("role") == "user":
                        messages.insert(len(messages) - 1, system_message)
                    else:
                        messages.append(system_message)

            # ================================================================
            # Step 4: Configure model parameters
            # ================================================================
            model = state["model_config"].get("model", self.config.llm.models.default)
            max_tokens = state.get("max_tokens", self.config.llm.max_tokens)
            temperature = state.get("temperature", self.config.llm.temperature)

            # ================================================================
            # Step 5: Stream LLM response
            # ================================================================
            async for event in self._stream_llm_response(
                messages=messages,
                session_id=session_id,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                yield event

        except Exception as e:
            # ================================================================
            # Error Handling
            # ================================================================
            self.logger.error(f"流式调用错误: {e}", exc_info=True)
            yield create_error_event(
                error=f"streaming_error: {str(e)}",
                session_id=session_id
            )

    # ========================================================================
    # Streaming Implementation
    # ========================================================================

    async def _stream_llm_response(
        self,
        messages: List[Dict[str, str]],
        session_id: str,
        model: str,
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream LLM response with tool execution support.

        This is the core streaming implementation that:
        1. Makes HTTP streaming request to LLM API
        2. Parses SSE events from response stream
        3. Accumulates tool calls across deltas
        4. Executes tools and continues streaming with results

        Args:
            messages: Conversation message list in OpenAI format
            session_id: Session identifier for event tracking
            model: Model name to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            SSE event dictionaries

        Streaming Protocol:
            - Server sends lines prefixed with "data: "
            - Each line contains JSON with "choices" array
            - Each choice has "delta" object with incremental content
            - Stream ends with "data: [DONE]" line
            - Tool calls are accumulated across multiple deltas
        """
        full_text = []
        collected_tool_calls = []

        try:
            # ================================================================
            # Ensure HTTP client is ready
            # ================================================================
            await self._ensure_http_client()

            # ================================================================
            # Get tool definitions
            # ================================================================
            tools_schema = self._get_tools_schema()

            # ================================================================
            # Prepare streaming request
            # ================================================================
            payload = prepare_llm_params(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,  # Enable streaming
                tools=tools_schema if tools_schema else None
            )

            if tools_schema:
                payload["tool_choice"] = "auto"

            url = self._build_llm_url()

            # ================================================================
            # Diagnostic logging
            # ================================================================
            self.logger.info("=" * 60)
            self.logger.info("📤 流式 LLM API 请求参数:")
            self.logger.info(f"  Model: {payload.get('model')}")
            self.logger.info(f"  Max Tokens: {payload.get('max_tokens') or payload.get('max_completion_tokens')}")
            self.logger.info(f"  Temperature: {payload.get('temperature', 'N/A')}")
            self.logger.info(f"  Messages Count: {len(messages)}")
            self.logger.info(f"  Tools Count: {len(tools_schema) if tools_schema else 0}")
            self.logger.info(f"  Stream: True")
            self.logger.info("=" * 60)

            # ================================================================
            # Emit start event
            # ================================================================
            yield create_start_event(session_id=session_id)

            # ================================================================
            # Stream response
            # ================================================================
            async with self._http_client.stream('POST', url, json=payload) as resp:
                if resp.status_code >= 400:
                    error_text = await resp.aread()
                    error_msg = error_text.decode('utf-8')[:500]
                    raise RuntimeError(f"LLM HTTP {resp.status_code}: {error_msg}")

                # ============================================================
                # Parse SSE stream
                # ============================================================
                async for line in resp.aiter_lines():
                    if not line:
                        continue

                    # SSE format: "data: {...}"
                    if line.startswith('data:'):
                        data_part = line[5:].strip()

                        # End of stream marker
                        if data_part == '[DONE]':
                            break

                        try:
                            data_json = json.loads(data_part)
                        except json.JSONDecodeError:
                            self.logger.warning(f"Failed to parse SSE data: {data_part[:100]}")
                            continue

                        # ====================================================
                        # Process streaming deltas
                        # ====================================================
                        for choice in data_json.get('choices', []):
                            delta = choice.get('delta', {})

                            # ================================================
                            # Handle text content
                            # ================================================
                            if 'content' in delta and delta['content']:
                                piece = delta['content']
                                full_text.append(piece)

                                # Emit delta event
                                yield create_delta_event(
                                    content=piece,
                                    session_id=session_id
                                )

                            # ================================================
                            # Accumulate tool calls across deltas
                            # ================================================
                            # Tool calls come in fragments across multiple deltas
                            # We need to accumulate them into complete tool call objects
                            if 'tool_calls' in delta:
                                for tc_delta in delta['tool_calls']:
                                    idx = tc_delta.get('index', 0)

                                    # Ensure list is long enough
                                    while len(collected_tool_calls) <= idx:
                                        collected_tool_calls.append({
                                            'id': None,
                                            'type': 'function',
                                            'function': {
                                                'name': '',
                                                'arguments': ''
                                            }
                                        })

                                    # Accumulate id (usually comes first)
                                    if 'id' in tc_delta:
                                        collected_tool_calls[idx]['id'] = tc_delta['id']

                                    # Accumulate type
                                    if 'type' in tc_delta:
                                        collected_tool_calls[idx]['type'] = tc_delta['type']

                                    # Accumulate function name and arguments
                                    if 'function' in tc_delta:
                                        fn = tc_delta['function']
                                        if 'name' in fn:
                                            collected_tool_calls[idx]['function']['name'] += fn['name']
                                        if 'arguments' in fn:
                                            collected_tool_calls[idx]['function']['arguments'] += fn['arguments']

            # ================================================================
            # Step 6: Handle tool calls (if any)
            # ================================================================
            if collected_tool_calls:
                self.logger.info(f"🔧 流式调用检测到 {len(collected_tool_calls)} 个工具调用")

                # Emit tool_calls event
                yield create_tool_calls_event(
                    tool_calls=collected_tool_calls,
                    session_id=session_id
                )

                # ============================================================
                # Execute all tools
                # ============================================================
                tool_results = []

                for tc in collected_tool_calls:
                    # Parse tool call
                    tool_id = tc.get('id') or f"tool_{int(datetime.now().timestamp())}"
                    tool_name = tc['function']['name']

                    try:
                        tool_args = json.loads(tc['function']['arguments'])
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse tool arguments: {e}")
                        tool_args = {}

                    # Create ToolCall object
                    tool_call = ToolCall(
                        id=tool_id,
                        name=tool_name,
                        arguments=tool_args
                    )

                    # Execute tool
                    result = await self._execute_tool_call(tool_call)

                    # Format result for LLM
                    if result.success and result.result:
                        result_content = result.result
                    else:
                        result_content = json.dumps({
                            "success": False,
                            "error": result.error or "Unknown error"
                        }, ensure_ascii=False)

                    # Add to results list
                    tool_results.append({
                        'tool_call_id': tool_id,
                        'role': 'tool',
                        'name': tool_name,
                        'content': result_content
                    })

                    self.logger.info(f"  ✅ 工具 '{tool_name}' 执行完成: {'成功' if result.success else '失败'}")

                # ============================================================
                # Build new message list with tool results
                # ============================================================
                # Add assistant message with tool calls
                new_messages = messages + [
                    {
                        'role': 'assistant',
                        'content': None,  # No text content, only tool calls
                        'tool_calls': collected_tool_calls
                    }
                ]

                # Add tool result messages
                for tr in tool_results:
                    new_messages.append({
                        'role': 'tool',
                        'tool_call_id': tr['tool_call_id'],
                        'name': tr['name'],
                        'content': tr['content']
                    })

                # ============================================================
                # Continue streaming with tool results (multi-turn)
                # ============================================================
                # Remove tools from config to prevent infinite loops
                # (LLM shouldn't call tools again after getting results)
                async for event in self._stream_llm_with_tool_results(
                    messages=new_messages,
                    session_id=session_id,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature
                ):
                    yield event

            else:
                # ============================================================
                # No tool calls: emit end event
                # ============================================================
                final_content = ''.join(full_text)

                self.logger.info(f"📥 流式响应完成: {len(final_content)} 字符")

                yield create_end_event(
                    content=final_content,
                    session_id=session_id
                )

        except Exception as e:
            # ================================================================
            # Error Handling with Fallback
            # ================================================================
            self.logger.error(f"流式调用失败: {e}", exc_info=True)

            # If we got partial results, return them
            if full_text:
                partial_content = ''.join(full_text)
                self.logger.warning(f"返回部分流式结果: {len(partial_content)} 字符")
                yield create_end_event(
                    content=partial_content,
                    session_id=session_id
                )
            else:
                # Fallback to non-streaming call
                self.logger.warning("流式调用失败，回退到非流式调用")

                try:
                    from .llm_caller import LLMCaller
                    caller = LLMCaller(self.config, trace=self.trace)

                    # Prepare config for non-streaming call
                    llm_config = prepare_llm_params(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )

                    result = await caller._make_llm_call(messages, llm_config)
                    content = result.get('content', '')

                    # Emit as single delta + end
                    if content:
                        yield create_delta_event(content=content, session_id=session_id)

                    yield create_end_event(content=content, session_id=session_id)

                except Exception as fallback_error:
                    self.logger.error(f"非流式回退也失败: {fallback_error}", exc_info=True)
                    yield create_error_event(
                        error=f"fallback_failed: {str(fallback_error)}",
                        session_id=session_id
                    )

    async def _stream_llm_with_tool_results(
        self,
        messages: List[Dict[str, str]],
        session_id: str,
        model: str,
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Continue streaming after tool execution.

        This method is called after tools have been executed to get the LLM's
        final response based on tool results. Tools are disabled in this call
        to prevent infinite loops.

        Args:
            messages: Message list including tool results
            session_id: Session identifier
            model: Model name
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Yields:
            SSE event dictionaries
        """
        try:
            await self._ensure_http_client()

            # ================================================================
            # Prepare streaming request WITHOUT tools
            # ================================================================
            # This prevents the LLM from calling tools again in an infinite loop
            payload = prepare_llm_params(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
                # Note: NO tools parameter
            )

            url = self._build_llm_url()

            self.logger.info("🔄 继续流式调用 (带工具结果，禁用工具)")

            # ================================================================
            # Stream response
            # ================================================================
            full_text = []

            async with self._http_client.stream('POST', url, json=payload) as resp:
                if resp.status_code >= 400:
                    error_text = await resp.aread()
                    error_msg = error_text.decode('utf-8')[:500]
                    raise RuntimeError(f"LLM HTTP {resp.status_code}: {error_msg}")

                async for line in resp.aiter_lines():
                    if not line:
                        continue

                    if line.startswith('data:'):
                        data_part = line[5:].strip()

                        if data_part == '[DONE]':
                            break

                        try:
                            data_json = json.loads(data_part)
                        except json.JSONDecodeError:
                            continue

                        for choice in data_json.get('choices', []):
                            delta = choice.get('delta', {})

                            if 'content' in delta and delta['content']:
                                piece = delta['content']
                                full_text.append(piece)

                                yield create_delta_event(
                                    content=piece,
                                    session_id=session_id
                                )

            # ================================================================
            # Emit end event
            # ================================================================
            final_content = ''.join(full_text)

            self.logger.info(f"📥 工具结果流式响应完成: {len(final_content)} 字符")

            yield create_end_event(
                content=final_content,
                session_id=session_id
            )

        except Exception as e:
            self.logger.error(f"工具结果流式调用失败: {e}", exc_info=True)
            yield create_error_event(
                error=f"tool_result_streaming_error: {str(e)}",
                session_id=session_id
            )

    # ========================================================================
    # Tool Schema (imported from llm_caller logic)
    # ========================================================================

    def _get_tools_schema(self) -> List[Dict]:
        """
        Get tool definitions in OpenAI Function Calling format.

        Returns:
            List of tool definition dictionaries, or empty list if error
        """
        try:
            # Use the new dependency injection approach
            from core.dependencies import AppState
            from fastapi import Request
            
            # Try to get registry from AppState (if available)
            try:
                # This is a workaround - ideally registry should be passed during init
                from mcp.registry import _GLOBAL_REGISTRY
                if _GLOBAL_REGISTRY is None:
                    self.logger.warning("Tool registry not initialized, tools disabled for this request")
                    return []
                registry = _GLOBAL_REGISTRY
            except Exception:
                self.logger.warning("Could not access tool registry, tools disabled for this request")
                return []
            
            tools = registry.list_tools()

            if not tools:
                return []

            tools_schema = []
            for tool in tools:
                schema = tool.to_openai_schema()
                tools_schema.append(schema)

            self.logger.info(f"✅ Loaded {len(tools_schema)} tools for streaming LLM")
            return tools_schema

        except Exception as e:
            self.logger.error(f"❌ Failed to load tools schema: {e}", exc_info=True)
            return []


# ============================================================================
# Convenience Functions
# ============================================================================

async def stream_llm_call(
    state: AgentState,
    config=None,
    trace=None,
    external_history: Optional[List[Dict[str, str]]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function for streaming LLM call without creating LLMStreamer instance.

    Args:
        state: Current conversation state
        config: Voice agent configuration (required)
        trace: Optional trace emitter
        external_history: Optional external message history

    Yields:
        SSE event dictionaries

    Raises:
        ValueError: If config is not provided

    Example:
        >>> from config.settings import load_config
        >>> config = load_config()
        >>> state = {...}
        >>> async for event in stream_llm_call(state, config=config):
        ...     print(event["type"])
    """
    if config is None:
        raise ValueError("config is required for stream_llm_call()")

    streamer = LLMStreamer(config, trace=trace)

    async for event in streamer.stream_llm_call(state, external_history=external_history):
        yield event


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "LLMStreamer",
    "stream_llm_call",  # Convenience function
]
