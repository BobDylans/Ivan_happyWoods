"""
LLM Caller Module

This module handles non-streaming LLM API calls for the voice agent.
It orchestrates the complete LLM invocation flow:
1. RAG snippet retrieval (if enabled)
2. Message preparation (via message_builder)
3. HTTP request to LLM API
4. Response parsing (text vs tool calls)
5. State updates for next processing stage

This module inherits from AgentNodesBase to access HTTP client, RAG service,
and configuration. It delegates message formatting to message_builder module.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import AgentNodesBase
from .message_builder import prepare_llm_messages
from ..state import AgentState, ToolCall

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


logger = logging.getLogger(__name__)


# ============================================================================
# LLM Caller Class
# ============================================================================

class LLMCaller(AgentNodesBase):
    """
    LLM caller node for non-streaming API calls.

    This class handles the complete LLM invocation flow:
    1. Retrieves RAG snippets (if RAG enabled)
    2. Prepares message list with system prompts and history
    3. Injects RAG context into messages
    4. Makes HTTP request to LLM API
    5. Parses response (text or tool calls)
    6. Updates state for next processing stage

    Inherits from AgentNodesBase for:
    - HTTP client management (_http_client, _ensure_http_client)
    - RAG service integration (_rag_service, _retrieve_rag_snippets)
    - Configuration access (self.config)
    - Logging (self.logger)

    Example:
        >>> from config.models import VoiceAgentConfig
        >>> config = VoiceAgentConfig()
        >>> caller = LLMCaller(config)
        >>>
        >>> state = {
        ...     "session_id": "sess_123",
        ...     "user_input": "What is the weather?",
        ...     "messages": [...],
        ...     "model_config": {"model": "gpt-4"},
        ...     "external_history": [...]
        ... }
        >>> result = await caller.call_llm(state)
        >>> result["next_action"]  # Either "handle_tools" or "format_response"
    """

    async def call_llm(self, state: AgentState) -> AgentState:
        """
        Call LLM to generate response.

        This is the core processing node, responsible for:
        1. Preparing conversation history messages
        2. Configuring model parameters
        3. Calling LLM API
        4. Handling response (text or tool calls)

        Args:
            state: Current conversation state containing:
                - session_id: Session identifier
                - messages: Conversation history
                - model_config: Model configuration override
                - external_history: Optional external history from SessionManager
                - user_input: Current user input
                - max_tokens: Optional max tokens override
                - temperature: Optional temperature override

        Returns:
            Updated conversation state with:
                - next_action: "handle_tools" if tools called, "format_response" if text
                - agent_response: LLM response text (if no tools)
                - pending_tool_calls: Tool calls to execute (if tools requested)
                - error_state: Error message if call failed

        Side Effects:
            - Retrieves RAG snippets and updates state["rag_snippets"]
            - Logs debug information about LLM call

        Example:
            >>> state = {
            ...     "session_id": "sess_001",
            ...     "user_input": "Calculate 2+2",
            ...     "messages": [...]
            ... }
            >>> result = await caller.call_llm(state)
            >>> result["next_action"]
            "handle_tools"  # LLM requested calculator tool
        """
        try:
            self.logger.debug(f"为会话 {state['session_id']} 调用 LLM")

            # ================================================================
            # Step 1: Retrieve RAG snippets (if enabled)
            # ================================================================
            external_history = state.get("external_history")
            if external_history is not None:
                self.logger.info(f"🔍 Found external_history in state: {len(external_history)} messages")
            else:
                self.logger.warning(f"⚠️ No external_history found in state for session {state['session_id']}")

            rag_results = await self._retrieve_rag_snippets(state)

            # ================================================================
            # Step 2: Prepare message list (system prompt + history)
            # ================================================================
            messages = prepare_llm_messages(state, external_history=external_history)

            # ================================================================
            # Step 3: Inject RAG context (if available)
            # ================================================================
            # Insert RAG system message before the last user message
            # This ensures RAG context is seen before answering the current query
            if rag_results and self._rag_service:
                rag_prompt = self._rag_service.build_prompt(rag_results)
                if rag_prompt:
                    system_message = {"role": "system", "content": rag_prompt}
                    # Insert before last user message if present
                    if messages and messages[-1].get("role") == "user":
                        messages.insert(len(messages) - 1, system_message)
                    else:
                        messages.append(system_message)

            # ================================================================
            # Step 4: Configure model parameters
            # ================================================================
            # Use兼容层 to handle different model parameter requirements
            model = state["model_config"].get("model", self.config.llm.models.default)
            max_tokens = state.get("max_tokens", self.config.llm.max_tokens)
            temperature = state.get("temperature", self.config.llm.temperature)

            llm_config = prepare_llm_params(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # ================================================================
            # Step 5: Call LLM API
            # ================================================================
            llm_start = time.perf_counter()
            response = await self._make_llm_call(messages, llm_config)

            if self.observability:
                elapsed_ms = (time.perf_counter() - llm_start) * 1000
                self.observability.observe(
                    "llm.request_ms",
                    elapsed_ms,
                    model=model,
                    mode="sync",
                    status="success",
                )
                self.observability.increment(
                    "llm.request_count",
                    model=model,
                    mode="sync",
                    status="success",
                )

            # ================================================================
            # Step 6: Determine response type and update state
            # ================================================================
            if self._has_tool_calls(response):
                # LLM requested tool execution
                state["next_action"] = "handle_tools"

                # Extract tool calls and add to pending queue
                tool_calls = self._extract_tool_calls(response)
                state["pending_tool_calls"].extend(tool_calls)

                self.logger.info(f"🔧 LLM requested {len(tool_calls)} tool call(s)")

            else:
                # LLM provided direct text response
                state["next_action"] = "format_response"
                state["agent_response"] = response.get("content", "")

                self.logger.info(f"💬 LLM provided text response ({len(state['agent_response'])} chars)")

            self.logger.debug("LLM 调用完成")
            return state

        except Exception as e:
            if self.observability:
                elapsed_ms = (time.perf_counter() - llm_start) * 1000 if 'llm_start' in locals() else 0.0
                self.observability.observe(
                    "llm.request_ms",
                    elapsed_ms,
                    model=state.get("model_config", {}).get("model", self.config.llm.models.default),
                    mode="sync",
                    status="error",
                )
                self.observability.increment(
                    "llm.request_count",
                    model=state.get("model_config", {}).get("model", self.config.llm.models.default),
                    mode="sync",
                    status="error",
                )
            # ================================================================
            # Error Handling
            # ================================================================
            self.logger.error(f"LLM 调用错误: {e}", exc_info=True)
            state["error_state"] = f"llm_call_error: {str(e)}"
            state["agent_response"] = "抱歉，我在处理您的请求时遇到了问题，请稍后再试。"
            state["next_action"] = "format_response"
            return state

    # ========================================================================
    # HTTP API Call
    # ========================================================================

    async def _make_llm_call(
        self,
        messages: List[Dict[str, str]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call LLM API (OpenAI compatible).

        If real HTTP call fails, falls back to keyword-based heuristic logic.
        This ensures the system can provide basic responses even during API outages.

        Args:
            messages: Conversation message list in OpenAI format
            config: LLM configuration parameters (model, temperature, max_tokens)

        Returns:
            Dictionary containing:
                - content (str): LLM response text
                - tool_calls (list): Tool call requests (empty if none)

        Fallback Behavior:
            If HTTP call fails, uses keyword matching to detect intent:
            - "search" / "搜索" → web_search tool
            - "calculate" / "计算" / math symbols → calculator tool
            - Default → echoes user message

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "You are helpful"},
            ...     {"role": "user", "content": "Calculate 2+2"}
            ... ]
            >>> config = {"model": "gpt-4", "temperature": 0.7}
            >>> response = await caller._make_llm_call(messages, config)
            >>> response["content"]
            "The result is 4"
        """
        user_message = messages[-1]["content"] if messages else ""

        # ====================================================================
        # Main Path: Real HTTP Call
        # ====================================================================
        try:
            # Ensure HTTP client is initialized
            await self._ensure_http_client()

            # Get tool definitions (OpenAI format)
            self.logger.info(f"🔍 Attempting to load tools schema...")
            tools_schema = self._get_tools_schema()
            self.logger.info(f"🔍 Tools schema loaded: {len(tools_schema) if tools_schema else 0} tools")

            # Prepare request payload
            payload = prepare_llm_params(
                model=config.get("model", self.config.llm.models.default),
                messages=messages,
                temperature=config.get("temperature", self.config.llm.temperature),
                max_tokens=config.get("max_tokens", self.config.llm.max_tokens),
                tools=tools_schema if tools_schema else None  # Pass tool definitions
            )

            # 🔍 Diagnostic logging - LLM request parameters
            self.logger.info("=" * 60)
            self.logger.info("📤 LLM API 请求参数:")
            self.logger.info(f"  Model: {payload.get('model')}")
            self.logger.info(f"  Max Tokens: {payload.get('max_tokens') or payload.get('max_completion_tokens')}")
            self.logger.info(f"  Temperature: {payload.get('temperature', 'N/A (模型默认)')}")
            self.logger.info(f"  Messages Count: {len(messages)}")
            self.logger.info(f"  Tools Count: {len(tools_schema) if tools_schema else 0}")

            # Estimate input tokens (rough estimate: Chinese ~1.5 chars/token, English ~4 chars/token)
            total_chars = sum(len(str(m.get('content', ''))) for m in messages)
            estimated_input_tokens = int(total_chars / 2)  # Conservative estimate
            self.logger.info(f"  估算输入 Tokens: ~{estimated_input_tokens}")
            self.logger.info("=" * 60)

            # If tools available, add tool_choice
            if tools_schema:
                payload["tool_choice"] = "auto"  # Let model decide whether to call tools
                self.logger.info(f"🔧 Added {len(tools_schema)} tools to LLM request")
            else:
                self.logger.warning(f"⚠️ No tools available for LLM request")

            # Build complete URL
            url = self._build_llm_url()
            self.logger.debug(f"LLM 调用: {url}")

            # Send request
            resp = await self._http_client.post(url, json=payload)
            if resp.status_code >= 400:
                error_text = resp.text[:500]
                self.logger.error(f"LLM HTTP {resp.status_code}: {error_text}")
                raise RuntimeError(f"LLM HTTP {resp.status_code}: {error_text}")

            data = resp.json()

            # 🔍 Diagnostic logging - LLM response information
            self.logger.info("=" * 60)
            self.logger.info("📥 LLM API 响应:")
            self.logger.info(f"  Choices Count: {len(data.get('choices', []))}")

            # Extract key information
            choices = data.get("choices", [])
            if choices:
                first = choices[0]
                finish_reason = first.get("finish_reason", "unknown")
                message_obj = first.get("message", {})
                content = message_obj.get("content") or ""
                tool_calls_raw = message_obj.get("tool_calls") or []

                # ⚠️ Critical diagnostic point: finish_reason
                self.logger.info(f"  ⭐ Finish Reason: {finish_reason}")
                if finish_reason == "length":
                    self.logger.warning("  ❌ 响应被截断！原因: max_tokens 限制")
                    self.logger.warning("  💡 建议: 增加 max_tokens 或减少输入长度")
                elif finish_reason == "stop":
                    self.logger.info("  ✅ 响应完整（正常结束）")
                elif finish_reason == "tool_calls":
                    self.logger.info("  🔧 响应类型: 工具调用")

                self.logger.info(f"  Content Length: {len(content)} 字符")
                self.logger.info(f"  Tool Calls Count: {len(tool_calls_raw)}")

                # Display usage information (if available)
                usage = data.get("usage", {})
                if usage:
                    self.logger.info(f"  Token Usage:")
                    self.logger.info(f"    - Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
                    self.logger.info(f"    - Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
                    self.logger.info(f"    - Total Tokens: {usage.get('total_tokens', 'N/A')}")

                # Display first 200 characters of response (for verification)
                if content:
                    preview = content[:200] + ("..." if len(content) > 200 else "")
                    self.logger.info(f"  Content Preview: {preview}")

                self.logger.info("=" * 60)

                # Normalize tool call format
                tool_calls = []
                for tc in tool_calls_raw:
                    if tc.get("type") == "function":
                        fn = tc.get("function", {})
                        tool_calls.append({
                            "id": tc.get("id") or f"tool_{int(datetime.now().timestamp())}",
                            "type": "function",
                            "function": {
                                "name": fn.get("name"),
                                "arguments": fn.get("arguments", "{}")
                            }
                        })

                return {"content": content, "tool_calls": tool_calls}

            # Fallback for abnormal response structure
            return {"content": content if 'content' in locals() else "", "tool_calls": []}

        except Exception as e:
            # ================================================================
            # Error logging
            # ================================================================
            self.logger.error(f"LLM 真实调用失败，使用启发式 fallback: {e}", exc_info=True)
            self.logger.error(f"LLM 配置 - Base URL: {self.config.llm.base_url}")
            self.logger.error(f"LLM 配置 - Model: {config.get('model', self.config.llm.models.default)}")
            self.logger.error(f"LLM 配置 - API Key 已设置: {bool(self.config.llm.api_key)}")

        # ====================================================================
        # Fallback Heuristic Logic (Keyword-Based)
        # ====================================================================
        self.logger.warning("⚠️ Using fallback heuristic logic for LLM response")

        # Search intent detection
        if "search" in user_message.lower() or "搜索" in user_message:
            self.logger.info("🔍 Fallback: Detected search intent")
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "search_1",
                        "type": "function",
                        "function": {
                            "name": "search_tool",
                            "arguments": json.dumps({"query": user_message})
                        }
                    }
                ]
            }

        # Calculation intent detection
        if "calculate" in user_message.lower() or "计算" in user_message or any(char in user_message for char in "+-*/"):
            self.logger.info("🧮 Fallback: Detected calculation intent")
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "calc_1",
                        "type": "function",
                        "function": {
                            "name": "calculator",
                            "arguments": json.dumps({"expression": user_message})
                        }
                    }
                ]
            }

        # Default fallback response (echo)
        self.logger.info("💬 Fallback: Using default echo response")
        return {
            "content": f"我理解您说的是：'{user_message}'（注意：LLM API 当前不可用，这是降级响应）",
            "tool_calls": []
        }

    # ========================================================================
    # Tool Call Detection
    # ========================================================================

    def _has_tool_calls(self, response: Dict[str, Any]) -> bool:
        """
        Check if LLM response contains tool calls.

        Args:
            response: LLM response dictionary with "tool_calls" key

        Returns:
            True if tool calls present, False otherwise

        Example:
            >>> response = {"content": "Let me search for that", "tool_calls": [...]}
            >>> caller._has_tool_calls(response)
            True
        """
        return bool(response.get("tool_calls"))

    def _extract_tool_calls(self, response: Dict[str, Any]) -> List[ToolCall]:
        """
        Extract tool calls from LLM response.

        Parses OpenAI-format tool calls and converts them to internal ToolCall objects.
        Handles JSON parsing errors in arguments gracefully.

        Args:
            response: LLM response dictionary containing:
                - tool_calls: List of tool call dictionaries with:
                    - id: Tool call identifier
                    - type: "function"
                    - function: {name: str, arguments: str (JSON)}

        Returns:
            List of ToolCall objects ready for execution

        Example:
            >>> response = {
            ...     "content": "",
            ...     "tool_calls": [
            ...         {
            ...             "id": "call_123",
            ...             "type": "function",
            ...             "function": {
            ...                 "name": "calculator",
            ...                 "arguments": '{"expression": "2+2"}'
            ...             }
            ...         }
            ...     ]
            ... }
            >>> tool_calls = caller._extract_tool_calls(response)
            >>> tool_calls[0].name
            "calculator"
            >>> tool_calls[0].arguments
            {"expression": "2+2"}
        """
        tool_calls = []

        for call_data in response.get("tool_calls", []):
            if call_data.get("type") == "function":
                function_data = call_data.get("function", {})

                # Parse arguments JSON (handle parsing errors)
                try:
                    arguments = json.loads(function_data.get("arguments", "{}"))
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse tool arguments: {e}")
                    arguments = {}

                # Create ToolCall object
                tool_call = ToolCall(
                    id=call_data.get("id", f"tool_{int(datetime.now().timestamp())}"),
                    name=function_data.get("name", "unknown"),
                    arguments=arguments
                )
                tool_calls.append(tool_call)

        return tool_calls

    # ========================================================================
    # Tool Schema
    # ========================================================================

    def _get_tools_schema(self) -> List[Dict]:
        """
        Get tool definitions in OpenAI Function Calling format.

        Queries the MCP tool registry for all available tools and converts
        them to OpenAI-compatible schema format.

        Returns:
            List of tool definition dictionaries in OpenAI format, or empty list if error

        Example:
            >>> tools = caller._get_tools_schema()
            >>> tools[0]
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform mathematical calculations",
                    "parameters": {...}
                }
            }
        """
        try:
            # Try to get registry from global state (workaround)
            # Ideally registry should be passed during init
            try:
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

            # Convert to OpenAI Function Calling format
            tools_schema = []
            for tool in tools:
                schema = tool.to_openai_schema()
                tools_schema.append(schema)

            self.logger.info(f"✅ Loaded {len(tools_schema)} tools for LLM")
            return tools_schema

        except Exception as e:
            self.logger.error(f"❌ Failed to load tools schema: {e}", exc_info=True)
            return []


# ============================================================================
# Convenience Functions
# ============================================================================

async def call_llm(state: AgentState, config=None, trace=None) -> AgentState:
    """
    Convenience function for calling LLM without creating LLMCaller instance.

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
        >>> state = {...}
        >>> result = await call_llm(state, config=config)
    """
    if config is None:
        raise ValueError("config is required for call_llm()")

    caller = LLMCaller(config, trace=trace)
    return await caller.call_llm(state)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "LLMCaller",
    "call_llm",  # Convenience function
]
