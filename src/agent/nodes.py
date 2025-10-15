"""
Agent Nodes Implementation

This module contains the core LangGraph nodes that handle different stages
of conversation processing, including input processing, LLM calls, tool handling,
and response formatting.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
import asyncio
import httpx
from datetime import datetime

from .state import AgentState, ConversationMessage, MessageRole, ToolCall, ToolResult

# 导入 LLM 兼容性工具
try:
    from utils.llm_compat import prepare_llm_params
except ImportError:
    # 如果导入失败，提供一个简单的兼容函数
    def prepare_llm_params(model, messages, temperature=0.7, max_tokens=2048, **kwargs):
        params = {
            "model": model,
            "messages": messages,
        }
        # GPT-5 系列不传 temperature，使用 API 默认值
        if not model.startswith("gpt-5"):
            params["temperature"] = temperature
        # GPT-5 系列使用 max_completion_tokens
        if model.startswith("gpt-5"):
            params["max_completion_tokens"] = max_tokens
        else:
            params["max_tokens"] = max_tokens
        params.update(kwargs)
        return params


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

try:
    from config.models import VoiceAgentConfig
except ImportError:
    # Fallback for when running as script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config.models import VoiceAgentConfig


logger = logging.getLogger(__name__)


class AgentNodes:
    """LangGraph 对话处理节点集合
    
    负责对话流程中的各个处理阶段：
    - 输入处理和验证
    - LLM 调用（同步/流式）
    - 工具调用处理
    - 响应格式化
    """
    
    def __init__(self, config: VoiceAgentConfig):
        """初始化节点配置
        
        Args:
            config: 语音助手配置对象
        """
        self.config = config
        self.logger = logger
        self._http_client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()
    
    async def _ensure_http_client(self):
        """确保 HTTP 客户端已初始化（懒加载）
        
        使用双重检查锁定模式确保线程安全的单例初始化。
        """
        if self._http_client is None:
            async with self._client_lock:
                if self._http_client is None:  # 双重检查
                    timeout = httpx.Timeout(self.config.llm.timeout, connect=10)
                    self._http_client = httpx.AsyncClient(
                        timeout=timeout,
                        headers={
                            "Authorization": f"Bearer {self.config.llm.api_key}",
                            "Content-Type": "application/json"
                        }
                    )
                    self.logger.debug("HTTP 客户端初始化成功")
    
    def _build_llm_url(self, endpoint: str = "chat/completions") -> str:
        """构建 LLM API 完整 URL
        
        自动处理 base_url 中是否包含 /v1 的情况。
        
        Args:
            endpoint: API 端点路径，默认为 "chat/completions"
        
        Returns:
            完整的 API URL
        
        Examples:
            >>> # base_url = "https://api.openai-proxy.org/v1"
            >>> self._build_llm_url()
            "https://api.openai-proxy.org/v1/chat/completions"
            
            >>> # base_url = "https://api.openai-proxy.org"
            >>> self._build_llm_url()
            "https://api.openai-proxy.org/v1/chat/completions"
        """
        base = self.config.llm.base_url.rstrip('/')
        
        # 仅在 base_url 不包含 /v1 时添加
        if not base.endswith('/v1'):
            base = base + '/v1'
        
        url = f"{base}/{endpoint}"
        return url
    
    async def cleanup(self):
        """清理资源
        
        关闭 HTTP 客户端连接，释放资源。
        应在程序退出或服务停止时调用。
        """
        if self._http_client:
            try:
                await self._http_client.aclose()
                self.logger.debug("HTTP 客户端已关闭")
            except Exception as e:
                self.logger.warning(f"关闭 HTTP 客户端时出错: {e}")
            finally:
                self._http_client = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口，自动清理资源"""
        await self.cleanup()
    async def process_input(self, state: AgentState) -> AgentState:
        """处理和验证用户输入
        
        这是对话处理流程的入口节点，负责：
        1. 验证输入不为空
        2. 创建用户消息对象
        3. 初步识别用户意图
        4. 更新状态准备调用 LLM
        
        Args:
            state: 当前对话状态
        
        Returns:
            更新后的对话状态
        """
        try:
            self.logger.debug(f"处理会话 {state['session_id']} 的输入")
            
            # 更新时间戳
            state["last_activity"] = datetime.now()
            
            # 规范化输入，确保不为空
            user_input = state["user_input"].strip()
            if not user_input:
                state["error_state"] = "empty_input"
                state["should_continue"] = False
                state["agent_response"] = "我没有收到任何输入，请说点什么吧。"
                return state
            
            # 将用户消息添加到对话历史
            user_message = ConversationMessage(
                id=f"user_{len(state['messages']) + 1}_{int(datetime.now().timestamp())}",
                role=MessageRole.USER,
                content=user_input,
                metadata={"processed_at": datetime.now().isoformat()}
            )
            state["messages"].append(user_message)
            
            # 通过关键词初步识别用户意图
            state["current_intent"] = self._analyze_intent(user_input)
            
            # 设置下一步动作：调用 LLM
            state["next_action"] = "call_llm"
            
            self.logger.debug(f"输入处理完成，意图: {state['current_intent']}")
            return state
            
        except Exception as e:
            self.logger.error(f"输入处理错误: {e}")
            state["error_state"] = f"input_processing_error: {str(e)}"
            state["should_continue"] = False
            return state
    
    async def call_llm(self, state: AgentState) -> AgentState:
        """调用大语言模型生成响应
        
        这是核心处理节点，负责：
        1. 准备对话历史消息
        2. 配置模型参数
        3. 调用 LLM API
        4. 处理响应（文本或工具调用）
        
        Args:
            state: 当前对话状态
        
        Returns:
            更新后的对话状态
        """
        try:
            self.logger.debug(f"为会话 {state['session_id']} 调用 LLM")
            
            # 准备 LLM 消息（包含对话历史）
            messages = self._prepare_llm_messages(state)
            
            # 配置模型参数（使用兼容层处理不同模型的参数差异）
            model = state["model_config"].get("model", self.config.llm.models.default)
            max_tokens = state.get("max_tokens", self.config.llm.max_tokens)
            temperature = state.get("temperature", self.config.llm.temperature)
            
            llm_config = prepare_llm_params(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 调用 LLM API 获取响应
            response = await self._make_llm_call(messages, llm_config)
            
            # 判断响应类型：工具调用 or 直接回复
            if self._has_tool_calls(response):
                state["next_action"] = "handle_tools"
                # 提取工具调用请求并加入待处理队列
                tool_calls = self._extract_tool_calls(response)
                state["pending_tool_calls"].extend(tool_calls)
            else:
                state["next_action"] = "format_response"
                state["agent_response"] = response.get("content", "")
            
            self.logger.debug("LLM 调用完成")
            return state
            
        except Exception as e:
            self.logger.error(f"LLM 调用错误: {e}")
            state["error_state"] = f"llm_call_error: {str(e)}"
            state["agent_response"] = "抱歉，我在处理您的请求时遇到了问题，请稍后再试。"
            state["next_action"] = "format_response"
            return state
    
    async def handle_tools(self, state: AgentState) -> AgentState:
        """处理工具调用请求
        
        当 LLM 需要使用工具时，此节点负责：
        1. 执行所有待处理的工具调用
        2. 收集工具执行结果
        3. 将结果添加到对话历史
        4. 准备再次调用 LLM（让它处理工具结果）
        
        Args:
            state: 当前对话状态
        
        Returns:
            更新后的对话状态
        """
        try:
            self.logger.debug(f"处理会话 {state['session_id']} 的工具调用")
            
            if not state["pending_tool_calls"]:
                self.logger.warning("没有待处理的工具调用")
                state["next_action"] = "call_llm"
                return state
            
            # 逐个执行工具调用
            for tool_call in state["pending_tool_calls"]:
                result = await self._execute_tool_call(tool_call)
                state["tool_results"].append(result)
                state["tool_calls"].append(tool_call)
            
            # 清空待处理队列
            state["pending_tool_calls"] = []
            
            # 将工具执行结果添加到对话历史
            for result in state["tool_results"][-len(state["tool_calls"]):]:
                tool_message = ConversationMessage(
                    id=f"tool_{result.call_id}_{int(datetime.now().timestamp())}",
                    role=MessageRole.TOOL,
                    content=json.dumps(result.dict(), cls=DateTimeJSONEncoder),
                    metadata={"tool_call_id": result.call_id, "success": result.success}
                )
                state["messages"].append(tool_message)
            
            # 继续调用 LLM 处理工具结果
            state["next_action"] = "call_llm"
            
            self.logger.debug(f"已处理 {len(state['tool_calls'])} 个工具调用")
            return state
            
        except Exception as e:
            self.logger.error(f"工具处理错误: {e}")
            state["error_state"] = f"tool_handling_error: {str(e)}"
            state["agent_response"] = "抱歉，在使用工具时遇到了问题，让我换个方式帮您。"
            state["next_action"] = "format_response"
            return state
    
    async def format_response(self, state: AgentState) -> AgentState:
        """格式化最终响应
        
        这是流程的最后一个节点，负责：
        1. 确保有响应内容
        2. 创建助手消息对象
        3. 添加元数据
        4. 标记对话回合结束
        
        Args:
            state: 当前对话状态
        
        Returns:
            最终的对话状态
        """
        try:
            self.logger.debug(f"格式化会话 {state['session_id']} 的响应")
            
            # 确保有响应内容
            if not state["agent_response"]:
                if state["error_state"]:
                    state["agent_response"] = "抱歉，处理您的请求时出现了错误。"
                else:
                    state["agent_response"] = "我不太确定如何回答，请换个方式问我吧。"
            
            # 创建助手消息并添加到历史
            assistant_message = ConversationMessage(
                id=f"assistant_{len(state['messages']) + 1}_{int(datetime.now().timestamp())}",
                role=MessageRole.ASSISTANT,
                content=state["agent_response"],
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "model": state["model_config"].get("model", "unknown"),
                    "intent": state.get("current_intent"),
                    "tool_calls_count": len(state["tool_calls"])
                }
            )
            state["messages"].append(assistant_message)
            
            # 更新活动时间戳
            state["last_activity"] = datetime.now()
            
            # 标记对话回合完成
            state["should_continue"] = False
            state["next_action"] = None
            
            self.logger.debug("响应格式化完成")
            return state
            
        except Exception as e:
            self.logger.error(f"响应格式化错误: {e}")
            state["error_state"] = f"response_formatting_error: {str(e)}"
            state["agent_response"] = "抱歉，响应格式化时出现了问题。"
            state["should_continue"] = False
            return state
    
    def _analyze_intent(self, user_input: str) -> Optional[str]:
        """分析用户意图（基于关键词的简单实现）
        
        注意：这是一个简化版本的意图识别，仅用于基础分类。
        生产环境建议使用 NLU 模型或 LLM 进行意图识别。
        
        Args:
            user_input: 用户输入文本
        
        Returns:
            识别的意图标签，如 "search", "calculation" 等
        """
        input_lower = user_input.lower()
        
        # 基于关键词的简单意图检测
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
    
    def _prepare_llm_messages(self, state: AgentState) -> List[Dict[str, str]]:
        """准备 LLM API 调用的消息列表
        
        包含系统提示词和最近的对话历史（限制为最近 10 条消息以控制上下文长度）。
        
        Args:
            state: 当前对话状态
        
        Returns:
            格式化的消息列表，符合 OpenAI API 格式
        """
        messages = []
        
        # 添加系统提示词
        system_message = {
            "role": "system",
            "content": (
                "你是一个有帮助的语音助手。你可以使用工具来帮助用户完成各种任务。"
                "当需要使用工具时，请返回包含工具调用详情的 JSON 对象。"
            )
        }
        messages.append(system_message)
        
        # 添加最近的对话历史（保留最近 10 条消息）
        MAX_HISTORY_MESSAGES = 10
        recent_messages = state["messages"][-MAX_HISTORY_MESSAGES:]
        for msg in recent_messages:
            if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        return messages
    
    async def _make_llm_call(self, messages: List[Dict[str, str]], config: Dict[str, Any]) -> Dict[str, Any]:
        """调用 LLM API（OpenAI 兼容）
        
        如果真实 HTTP 调用失败，会使用基于关键词的启发式 fallback。
        
        Args:
            messages: 对话消息列表
            config: LLM 配置参数
        
        Returns:
            包含 content (str) 和 tool_calls (list) 的字典
        """
        user_message = messages[-1]["content"] if messages else ""

        # ==== 主要路径：真实 HTTP 调用 ====
        try:
            # 确保 HTTP 客户端已初始化
            await self._ensure_http_client()

            # 准备请求参数
            payload = prepare_llm_params(
                model=config.get("model", self.config.llm.models.default),
                messages=messages,
                temperature=config.get("temperature", self.config.llm.temperature),
                max_tokens=config.get("max_tokens", self.config.llm.max_tokens)
            )

            # 构建完整 URL
            url = self._build_llm_url()
            self.logger.debug(f"LLM 调用: {url}")

            # 发送请求
            resp = await self._http_client.post(url, json=payload)
            if resp.status_code >= 400:
                error_text = resp.text[:500]
                self.logger.error(f"LLM HTTP {resp.status_code}: {error_text}")
                raise RuntimeError(f"LLM HTTP {resp.status_code}: {error_text}")
            
            data = resp.json()
            self.logger.debug(f"LLM 响应: {len(data.get('choices', []))} 个选择")

            # 解析 OpenAI 风格的响应结构
            choices = data.get("choices", [])
            if choices:
                first = choices[0]
                message_obj = first.get("message", {})
                content = message_obj.get("content") or ""
                tool_calls_raw = message_obj.get("tool_calls") or []
                
                # 规范化工具调用格式
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

            # 响应结构异常时的 fallback
            return {"content": content if 'content' in locals() else "", "tool_calls": []}

        except Exception as e:
            self.logger.error(f"LLM 真实调用失败，使用启发式 fallback: {e}", exc_info=True)
            self.logger.error(f"LLM 配置 - Base URL: {self.config.llm.base_url}")
            self.logger.error(f"LLM 配置 - Model: {config.get('model', self.config.llm.models.default)}")
            self.logger.error(f"LLM 配置 - API Key 已设置: {bool(self.config.llm.api_key)}")

        # ==== Fallback 启发式逻辑 ====
        if "search" in user_message.lower() or "搜索" in user_message:
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
        if "calculate" in user_message.lower() or "计算" in user_message or any(char in user_message for char in "+-*/"):
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
        
        # 默认 fallback 响应
        return {
            "content": f"我理解您说的是：'{user_message}'",
            "tool_calls": []
        }

    async def stream_llm_call(self, messages: List[Dict[str, str]], config: Dict[str, Any], session_id: Optional[str] = None):
        """流式调用 LLM 并生成增量响应事件。

        以流式方式调用 LLM API,逐步生成响应内容。返回版本化事件,包含事件 ID、时间戳等元数据。
        如果流式调用失败,自动 fallback 到非流式调用。

        Args:
            messages: 消息历史列表
            config: LLM 配置(model, temperature, max_tokens 等)
            session_id: 会话 ID(可选)

        Yields:
            事件字典,包含 version, id, timestamp, type 等字段:
            - start: {version: '1.0', id: 'evt_xxx', timestamp: '...', type: 'start', model: '...'}
            - delta: {version: '1.0', id: 'evt_xxx', timestamp: '...', type: 'delta', content: str}
            - tool_calls: {version: '1.0', id: 'evt_xxx', timestamp: '...', type: 'tool_calls', tool_calls: [...]}
            - end: {version: '1.0', id: 'evt_xxx', timestamp: '...', type: 'end', content: full_text}
            - error: {version: '1.0', id: 'evt_xxx', timestamp: '...', type: 'error', error: msg}
        """
        # 导入事件工具函数
        try:
            from api.event_utils import (
                create_start_event, create_delta_event, create_end_event,
                create_error_event, create_tool_calls_event
            )
        except ImportError:
            # 如果 event_utils 不可用,使用 fallback 格式
            from datetime import datetime
            import uuid
            def create_start_event(sid=None, model=None):
                evt = {"version": "1.0", "id": f"evt_{uuid.uuid4().hex[:16]}", 
                       "timestamp": datetime.utcnow().isoformat() + "Z", "type": "start"}
                if model: evt["model"] = model
                if sid: evt["session_id"] = sid
                return evt
            def create_delta_event(content, sid=None, metadata=None):
                evt = {"version": "1.0", "id": f"evt_{uuid.uuid4().hex[:16]}", 
                       "timestamp": datetime.utcnow().isoformat() + "Z", "type": "delta", "content": content}
                if sid: evt["session_id"] = sid
                if metadata: evt["metadata"] = metadata
                return evt
            def create_end_event(content, sid=None, metadata=None):
                evt = {"version": "1.0", "id": f"evt_{uuid.uuid4().hex[:16]}", 
                       "timestamp": datetime.utcnow().isoformat() + "Z", "type": "end", "content": content}
                if sid: evt["session_id"] = sid
                if metadata: evt["metadata"] = metadata
                return evt
            def create_error_event(error, sid=None, error_code=None):
                evt = {"version": "1.0", "id": f"evt_{uuid.uuid4().hex[:16]}", 
                       "timestamp": datetime.utcnow().isoformat() + "Z", "type": "error", "error": error}
                if sid: evt["session_id"] = sid
                if error_code: evt["error_code"] = error_code
                return evt
            def create_tool_calls_event(tool_calls, sid=None):
                evt = {"version": "1.0", "id": f"evt_{uuid.uuid4().hex[:16]}", 
                       "timestamp": datetime.utcnow().isoformat() + "Z", "type": "tool_calls", "tool_calls": tool_calls}
                if sid: evt["session_id"] = sid
                return evt
        
        user_message = messages[-1]["content"] if messages else ""
        full_text = []
        yielded_tool_calls = False
        model = config.get("model", self.config.llm.models.default)
        
        # 尝试流式调用
        try:
            # 确保 HTTP 客户端已初始化
            await self._ensure_http_client()

            payload = prepare_llm_params(
                model=config.get("model", self.config.llm.models.default),
                messages=messages,
                temperature=config.get("temperature", self.config.llm.temperature),
                max_tokens=config.get("max_tokens", self.config.llm.max_tokens),
                stream=True
            )
            # 使用提取的 URL 构建方法
            url = self._build_llm_url()
            
            self.logger.debug(f"LLM 流式调用目标: {url}")
            
            yield create_start_event(session_id=session_id, model=model)
            async with self._http_client.stream('POST', url, json=payload) as resp:
                if resp.status_code >= 400:
                    text = await resp.aread()
                    raise RuntimeError(f"流式 HTTP 请求失败 {resp.status_code}: {text[:200]}")
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
                                yield create_delta_event(content=piece, session_id=session_id)
                            # 流式工具调用(OpenAI function calling 风格)
                            if 'tool_calls' in delta and not yielded_tool_calls:
                                # 在流结束后收集最终工具调用;这里可以转发部分名称
                                try:
                                    yield create_tool_calls_event(tool_calls=delta['tool_calls'], session_id=session_id)
                                    yielded_tool_calls = True
                                except Exception:
                                    pass
            yield create_end_event(content=''.join(full_text), session_id=session_id)
            return
        except Exception as e:
            self.logger.warning(f"流式调用失败,回退到非流式: {e}")
            if not full_text:
                # 回退到普通调用
                try:
                    result = await self._make_llm_call(messages, config)
                    content = result.get('content', '')
                    yield create_delta_event(content=content, session_id=session_id)
                    if result.get('tool_calls'):
                        yield create_tool_calls_event(tool_calls=result['tool_calls'], session_id=session_id)
                    yield create_end_event(content=content, session_id=session_id)
                    return
                except Exception as e2:
                    yield create_error_event(error=str(e2), session_id=session_id)
                    return
            else:
                yield create_end_event(content=''.join(full_text), session_id=session_id)
    
    def _has_tool_calls(self, response: Dict[str, Any]) -> bool:
        """Check if LLM response contains tool calls."""
        return bool(response.get("tool_calls"))
    
    def _extract_tool_calls(self, response: Dict[str, Any]) -> List[ToolCall]:
        """Extract tool calls from LLM response."""
        tool_calls = []
        
        for call_data in response.get("tool_calls", []):
            if call_data.get("type") == "function":
                function_data = call_data.get("function", {})
                try:
                    arguments = json.loads(function_data.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}
                
                tool_call = ToolCall(
                    id=call_data.get("id", f"tool_{int(datetime.now().timestamp())}"),
                    name=function_data.get("name", "unknown"),
                    arguments=arguments
                )
                tool_calls.append(tool_call)
        
        return tool_calls
    
    async def _execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call using MCP tool registry."""
        try:
            # Try to use MCP tool registry
            try:
                from mcp import get_tool_registry
                
                registry = get_tool_registry()
                
                # Map common LLM tool names to MCP tool names
                tool_name_mapping = {
                    "search_tool": "web_search",
                    "web_search": "web_search",
                    "calculator": "calculator",
                    "time_tool": "get_time",
                    "get_time": "get_time",
                    "weather": "get_weather",
                    "get_weather": "get_weather",
                }
                
                mcp_tool_name = tool_name_mapping.get(tool_call.name, tool_call.name)
                
                # Execute through registry
                result_dict = await registry.execute(mcp_tool_name, **tool_call.arguments)
                
                # Convert MCP ToolResult to Agent ToolResult
                if result_dict.get("success"):
                    result_str = json.dumps(result_dict.get("data", {}), ensure_ascii=False)
                else:
                    result_str = None
                
                return ToolResult(
                    call_id=tool_call.id,
                    success=result_dict.get("success", False),
                    result=result_str,
                    error=result_dict.get("error")
                )
            
            except ImportError:
                self.logger.warning("MCP tools not available, using fallback implementation")
                # Fall back to placeholder implementation
                pass
            
            # Fallback placeholder implementation
            if tool_call.name in ["search_tool", "web_search"]:
                result = f"Search results for: {tool_call.arguments.get('query', 'unknown')}"
            elif tool_call.name == "calculator":
                expression = tool_call.arguments.get('expression', '')
                try:
                    result = f"The result is: {expression} (calculation placeholder)"
                except:
                    result = "Could not calculate the expression"
            elif tool_call.name in ["time_tool", "get_time"]:
                result = f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                result = f"Tool '{tool_call.name}' executed with arguments: {tool_call.arguments}"
            
            return ToolResult(
                call_id=tool_call.id,
                success=True,
                result=result
            )
            
        except Exception as e:
            self.logger.error(f"Tool execution error: {e}", exc_info=True)
            return ToolResult(
                call_id=tool_call.id,
                success=False,
                result=None,
                error=str(e)
            )