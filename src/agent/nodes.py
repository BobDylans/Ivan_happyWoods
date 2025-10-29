"""
Agent Nodes Implementation

This module contains the core LangGraph nodes that handle different stages
of conversation processing, including input processing, LLM calls, tool handling,
and response formatting.
"""

import json
import logging
import random
import time
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
    def prepare_llm_params(model, messages, temperature=0.7, max_tokens=16384, **kwargs):  # 🔧 修复默认值
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
    
    def __init__(self, config: VoiceAgentConfig, trace=None):
        """初始化节点配置
        
        Args:
            config: 语音助手配置对象
            trace: 可选的 TraceEmitter 实例（用于可视化事件）
        """
        self.config = config
        self.logger = logger
        self._http_client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()
        
        # 接收 trace 实例
        self.trace = trace
        
        # 🆕 工具结果缓存（优化：避免重复调用相同工具）
        # 格式: {cache_key: (result, timestamp)}
        self._tool_cache: Dict[str, tuple[ToolResult, float]] = {}
        self._cache_ttl = 300  # 缓存有效期：5分钟
        
        # 🆕 预构建基础系统提示词（优化：避免每次重新生成）
        self._base_system_prompt = self._build_base_system_prompt()
    
    def _build_base_system_prompt(self) -> str:
        """构建基础系统提示词（静态部分）
        
        只在初始化时构建一次，避免每次 LLM 调用都重新生成。
        
        Returns:
            基础系统提示词
        """
        return """你是一个专业、友好的 AI 助手，致力于为用户提供准确、有用的信息和帮助。

## 核心能力

你可以：
1. **回答问题**：基于知识库提供准确的答案
2. **搜索信息**：使用 web_search 工具搜索最新信息
3. **执行计算**：使用 calculator 工具进行数学计算
4. **查询时间**：使用 get_time 工具获取当前时间
5. **查询天气**：使用 get_weather 工具查询天气信息

## 交互原则

1. **准确性第一**：不确定时明确告知，不编造信息
2. **结构化回复**：使用 Markdown 格式组织内容
3. **信息来源**：搜索结果需标注来源和链接
4. **简洁明了**：避免冗长，直击要点
5. **友好专业**：保持礼貌，语气自然

## Markdown 格式规范

### 标题层级
- 使用 `## ` 作为主标题
- 使用 `### ` 作为小标题
- **不要使用** `# ` 一级标题

### 列表格式
- 项目之间**必须有空行**
- 使用 `-` 或数字列表
- 重要信息用 **粗体** 突出

### 代码展示
- 单行代码用 `反引号`
- 多行代码用 ```语言名称 代码块
- 必须指定语言以启用语法高亮

### 链接格式
- 格式：[链接文字](URL)
- 搜索结果链接必须可点击

## 搜索结果格式

当使用搜索工具时，**必须**按以下格式组织：

```
## 🔍 搜索结果

根据最新搜索，我为您找到以下信息：

### 1. [结果标题](URL)
- **来源**：网站名称
- **关键信息**：简要描述

### 2. [结果标题](URL)
- **来源**：网站名称
- **关键信息**：简要描述

## 📝 总结

[对搜索结果的综合分析]
```

## 工具使用指南

### 何时使用工具
- 用户询问**最新信息**（新闻、时事）→ 使用 web_search
- 用户需要**计算**（数学、换算）→ 使用 calculator
- 用户询问**当前时间/日期** → 使用 get_time
- 用户询问**天气** → 使用 get_weather

### 工具调用原则
1. **明确需求**：确认是否真的需要工具
2. **单次调用**：优先一次性获取所需信息
3. **结果整合**：将工具结果自然地融入回复
4. **失败降级**：工具失败时提供替代方案"""
    
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
        session_id = state.get('session_id', 'unknown')
        
        try:
            self.logger.debug(f"处理会话 {session_id} 的输入")
            
            # 🆕 思考阶段：验证输入
            if self.trace:
                # 注意：这里不能 yield，因为 process_input 是同步返回 state 的
                # 我们只记录日志，真正的事件在 Graph 层发射
                self.logger.debug(f"[Trace] process_input: 验证用户输入")
            
            # 更新时间戳
            state["last_activity"] = datetime.now()
            
            # 规范化输入，确保不为空
            user_input = state["user_input"].strip()
            if not user_input:
                state["error_state"] = "empty_input"
                state["should_continue"] = False
                state["agent_response"] = "我没有收到任何输入，请说点什么吧。"
                state["next_action"] = "format_response"
                return state
            
            # ⚡ 快速响应：检测简单问候（优化：跳过 LLM 调用）
            if self._is_simple_greeting(user_input):
                self.logger.info(f"🚀 检测到简单问候，快速响应（跳过 LLM）")
                state["agent_response"] = self._get_greeting_response()
                state["next_action"] = "format_response"
                state["current_intent"] = "greeting"
                
                # 将用户消息添加到历史
                user_message = ConversationMessage(
                    id=f"user_{len(state['messages']) + 1}_{int(datetime.now().timestamp())}",
                    role=MessageRole.USER,
                    content=user_input,
                    metadata={"processed_at": datetime.now().isoformat(), "fast_path": True}
                )
                state["messages"].append(user_message)
                
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
            # 如果 state 中有 external_history，传递给 _prepare_llm_messages
            external_history = state.get("external_history")
            if external_history is not None:
                self.logger.info(f"🔍 Found external_history in state: {len(external_history)} messages")
            else:
                self.logger.warning(f"⚠️ No external_history found in state for session {state['session_id']}")
            messages = self._prepare_llm_messages(state, external_history=external_history)
            
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
        
        🆕 优化版: 支持多轮工具调用
        
        当 LLM 需要使用工具时，此节点负责：
        1. 执行所有待处理的工具调用
        2. 收集工具执行结果
        3. 将结果添加到对话历史
        4. 🆕 增加工具调用计数器
        5. 准备再次调用 LLM（让它基于工具结果重新思考）
        
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
            
            # 🆕 增加工具调用计数
            state["tool_call_count"] = state.get("tool_call_count", 0) + 1
            current_iteration = state["tool_call_count"]
            
            self.logger.info(f"🔧 第 {current_iteration} 轮工具调用，待执行工具数: {len(state['pending_tool_calls'])}")
            
            # ⚡ 并行执行所有工具调用（优化：从串行改为并行）
            tool_tasks = [
                self._execute_tool_call(tool_call) 
                for tool_call in state["pending_tool_calls"]
            ]
            results = await asyncio.gather(*tool_tasks, return_exceptions=True)
            
            # 处理执行结果
            for tool_call, result in zip(state["pending_tool_calls"], results):
                # 如果工具执行抛出异常，转换为失败结果
                if isinstance(result, Exception):
                    self.logger.error(f"  ❌ 工具 '{tool_call.name}' 执行异常: {str(result)}")
                    result = ToolResult(
                        call_id=tool_call.id,
                        success=False,
                        result=None,
                        error=f"工具执行异常: {str(result)}"
                    )
                
                state["tool_results"].append(result)
                state["tool_calls"].append(tool_call)
                
                status_icon = "✅" if result.success else "❌"
                self.logger.info(f"  {status_icon} 工具 '{tool_call.name}' 执行完成: {result.success}")
            
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
            
            # 🆕 核心改动: 工具调用后返回 LLM 进行重新思考
            # LLM 会基于工具结果判断是否需要更多工具或直接生成回复
            state["next_action"] = "call_llm"
            
            self.logger.info(f"🔄 第 {current_iteration} 轮工具调用完成，返回 LLM 重新评估")
            return state
            
        except Exception as e:
            self.logger.error(f"工具处理错误: {e}")
            state["error_state"] = f"tool_handling_error: {str(e)}"
            state["agent_response"] = "抱歉，在使用工具时遇到了问题，让我换个方式帮您。"
            # 即使出错，也返回 LLM 让它生成 fallback 回复
            state["next_action"] = "call_llm"
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
    
    def _prepare_llm_messages(self, state: AgentState, external_history: List[Dict] = None) -> List[Dict[str, str]]:
        """准备 LLM API 调用的消息列表
        
        包含优化的系统提示词和历史对话。优先使用外部传入的历史记录。
        
        Args:
            state: 当前对话状态
            external_history: 外部传入的历史消息列表 (可选)
        
        Returns:
            格式化的消息列表，符合 OpenAI API 格式
        """
        messages = []
        
        # 构建优化的系统提示词
        system_prompt = self._build_optimized_system_prompt(state)
        system_message = {
            "role": "system",
            "content": system_prompt
        }
        messages.append(system_message)
        
        # 优先使用外部历史（从 SessionHistoryManager）
        if external_history is not None:
            # 限制历史消息数量（最近 10 条）
            MAX_HISTORY_MESSAGES = 10
            recent_history = external_history[-MAX_HISTORY_MESSAGES:] if external_history else []
            for msg in recent_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            self.logger.info(f"✅ Loaded {len(recent_history)} messages from external history for LLM")
            
            # 重要：添加当前用户消息（来自 state["messages"] 的最后一条）
            if state["messages"] and state["messages"][-1].role == MessageRole.USER:
                current_user_msg = state["messages"][-1]
                messages.append({
                    "role": "user",
                    "content": current_user_msg.content
                })
                self.logger.info(f"✅ Added current user message to LLM input")
        else:
            # 回退到 state 中的消息（如果有）
            self.logger.info("⚠️ No external history provided, using state messages")
            MAX_HISTORY_MESSAGES = 10
            recent_messages = state["messages"][-MAX_HISTORY_MESSAGES:]
            for msg in recent_messages:
                if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                    messages.append({
                        "role": msg.role.value,
                        "content": msg.content
                    })
            self.logger.info(f"📝 Using {len(recent_messages)} messages from state")
        
        return messages
    
    def _build_optimized_system_prompt(self, state: AgentState) -> str:
        """构建优化的系统提示词（使用预构建基础 + 动态上下文）
        
        优化策略：
        1. 使用预构建的基础提示词（静态部分）
        2. 仅添加动态的上下文信息
        3. 减少字符串拼接开销
        
        Args:
            state: 当前对话状态
        
        Returns:
            完整的系统提示词
        """
        # 使用预构建的基础提示词
        prompt_parts = [self._base_system_prompt]
        
        # 添加动态上下文信息
        context_additions = []
        
        # 如果有工具调用历史，添加提示
        if state.get("tool_calls"):
            tool_count = len(state["tool_calls"])
            context_additions.append(f"\n## 当前上下文\n\n- 已执行 {tool_count} 次工具调用")
        
        # 如果用户有明确意图，添加提示
        current_intent = state.get("current_intent")
        if current_intent and current_intent != "general":
            intent_hints = {
                "search": "用户需要搜索信息，优先使用 web_search 工具",
                "calculation": "用户需要计算，使用 calculator 工具",
                "time_query": "用户询问时间，使用 get_time 工具",
                "weather": "用户询问天气，使用 get_weather 工具"
            }
            if current_intent in intent_hints:
                context_additions.append(f"- {intent_hints[current_intent]}")
        
        # 合并所有部分
        if context_additions:
            prompt_parts.append("\n".join(context_additions))
        
        return "\n\n".join(prompt_parts)
    
    def _get_tools_schema(self) -> List[Dict]:
        """获取工具的 OpenAI Function Calling 格式定义
        
        Returns:
            工具定义列表，OpenAI tools 格式
        """
        try:
            from mcp import get_tool_registry
            registry = get_tool_registry()
            tools = registry.list_tools()
            
            if not tools:
                return []
            
            # 转换为 OpenAI Function Calling 格式
            tools_schema = []
            for tool in tools:
                schema = tool.to_openai_schema()
                tools_schema.append(schema)
            
            self.logger.info(f"✅ Loaded {len(tools_schema)} tools for LLM")
            return tools_schema
        except Exception as e:
            self.logger.error(f"❌ Failed to load tools schema: {e}", exc_info=True)
            return []
    
    def _format_available_tools(self) -> str:
        """格式化可用工具列表为易读的文本
        
        Returns:
            格式化的工具列表字符串
        """
        try:
            from mcp import get_tool_registry
            registry = get_tool_registry()
            tools = registry.list_tools()
            
            if not tools:
                return "当前暂无可用工具。"
            
            tool_descriptions = []
            for tool in tools:
                name = tool.name
                desc = tool.description
                # 简化描述，只保留关键信息
                short_desc = desc.split('.')[0] if desc else "无描述"
                tool_descriptions.append(f"- **{name}**: {short_desc}")
            
            return "\n".join(tool_descriptions)
        
        except Exception as e:
            self.logger.warning(f"获取工具列表失败: {e}")
            return "- **calculator**: 执行数学计算\n- **get_time**: 获取当前时间\n- **get_weather**: 查询天气信息\n- **web_search**: 搜索网络信息"
    
    def _build_context_aware_addition(self, state: AgentState) -> str:
        """根据当前对话上下文构建额外的提示词增强
        
        Args:
            state: 当前对话状态
        
        Returns:
            上下文相关的额外提示词，如果不需要则返回空字符串
        """
        additions = []
        
        # 1. 如果有工具调用历史，提醒基于结果回答
        if state.get("tool_calls") and len(state["tool_calls"]) > 0:
            additions.append(
                """# ⚠️ Current Context: Tool Results Available

You have just executed tool(s) and received results. **CRITICAL REMINDER**:

✅ **You MUST**:
- Base your response ENTIRELY on the actual tool results data
- Parse and present the tool response properly (especially for web_search)
- Follow the mandatory search results protocol if it was a web_search call
- Extract and display: ai_answer, titles, snippets, urls from the results
- Format everything in proper Markdown structure

❌ **You MUST NOT**:
- Fabricate or guess information not in the tool results
- Return tool parameters (e.g., `{"query": "...", "num_results": 8}`) as if they were results
- Say "Found X results" without showing the actual content
- Ignore the structured data in the tool response

**If tool results are incomplete or unclear**: Explicitly inform the user about limitations."""
            )
        
        # 2. 如果对话轮次较多，提醒保持连贯性
        message_count = len(state.get("messages", []))
        if message_count > 6:
            additions.append(
                """# 💬 Conversation Continuity

This is a multi-turn conversation (6+ messages). Please:
- Maintain context consistency across turns
- Recognize pronouns like "it", "this", "that" referring to previous topics
- Reference earlier discussion points when relevant
- Don't repeat information already established in the conversation"""
            )
        
        # 3. 如果检测到特定意图，给出针对性指导
        intent = state.get("current_intent")
        user_input = state.get("user_input", "").lower()
        
        # 检测搜索意图
        search_keywords = ["search", "find", "latest", "news", "搜索", "查找", "最新", "新闻", "查询"]
        if intent == "search" or any(keyword in user_input for keyword in search_keywords):
            additions.append(
                """# 🔍 Search Task Optimization

User is requesting information search. **Enhanced Protocol**:

**Step 1: Tool Execution**
- Use `web_search` with precise query (English for international topics, Chinese for local topics)
- Set `num_results` to 5-8 for optimal balance

**Step 2: Result Processing (MANDATORY)**
Parse the tool response JSON structure:
```json
{
  "ai_answer": "Use this as executive summary if valuable",
  "results": [
    {"title": "...", "snippet": "...", "url": "...", "score": 0.95}
  ]
}
```

**Step 3: Response Formatting (STRICT)**
```markdown
## 🔍 Search Results: [Topic]

### 📊 Executive Summary
[Present ai_answer here, or synthesize from top results]

### 📰 Detailed Findings
1. **[Title 1]**
   - 📝 [Key points from snippet]
   - 🔗 [Title](URL)

2. **[Title 2]** ...

---
💡 **Key Insight**: [Your analysis]
```

**Quality Checklist**:
- [ ] ai_answer used as summary (if present)
- [ ] 3-5 results shown with title + snippet + clickable URL
- [ ] Markdown structure with headers and lists
- [ ] Time-sensitive info includes dates
- [ ] Added synthesis or insight beyond raw data

**Common Error to Avoid**:
❌ Do NOT just output: "Found 8 search results about Trump's Japan visit"
✅ DO output: Structured results with actual titles, snippets, and links"""
            )
        
        # 检测计算意图
        elif intent == "calculation" or any(op in user_input for op in ["+", "-", "*", "/", "calculate", "计算"]):
            additions.append(
                """# 🧮 Calculation Task

User needs mathematical computation:
- Use `calculator` tool for complex expressions or to ensure precision
- Show both the expression and result clearly
- Format: "Calculating `expression` = **result**"
- For very simple math (e.g., 2+2), you can answer directly
- For decimals, powers, trigonometry, always use the tool for accuracy"""
            )
        
        # 检测时间查询
        elif "time" in user_input or "date" in user_input or "时间" in user_input or "日期" in user_input or "几点" in user_input:
            additions.append(
                """# 🕐 Time/Date Query

User is asking about current time or date:
- Use `get_time` tool with appropriate format parameter
- Present time in user-friendly format with timezone context
- For "what time is it": use format="full"
- For "what date": use format="date"
- For "timestamp": use format="timestamp"
- Always clarify the timezone in your response"""
            )
        
        return "\n\n".join(additions) if additions else ""

    
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

            # 获取工具定义（OpenAI 格式）
            self.logger.info(f"🔍 Attempting to load tools schema...")
            tools_schema = self._get_tools_schema()
            self.logger.info(f"🔍 Tools schema loaded: {len(tools_schema) if tools_schema else 0} tools")
            
            # 准备请求参数
            payload = prepare_llm_params(
                model=config.get("model", self.config.llm.models.default),
                messages=messages,
                temperature=config.get("temperature", self.config.llm.temperature),
                max_tokens=config.get("max_tokens", self.config.llm.max_tokens),
                tools=tools_schema if tools_schema else None  # 传递工具定义
            )
            
            # 🔍 诊断日志 - LLM 请求参数
            self.logger.info("=" * 60)
            self.logger.info("📤 LLM API 请求参数:")
            self.logger.info(f"  Model: {payload.get('model')}")
            self.logger.info(f"  Max Tokens: {payload.get('max_tokens') or payload.get('max_completion_tokens')}")
            self.logger.info(f"  Temperature: {payload.get('temperature', 'N/A (模型默认)')}")
            self.logger.info(f"  Messages Count: {len(messages)}")
            self.logger.info(f"  Tools Count: {len(tools_schema) if tools_schema else 0}")
            
            # 估算输入 token 数（粗略估计：中文 ~1.5 字符/token，英文 ~4 字符/token）
            total_chars = sum(len(str(m.get('content', ''))) for m in messages)
            estimated_input_tokens = int(total_chars / 2)  # 保守估计
            self.logger.info(f"  估算输入 Tokens: ~{estimated_input_tokens}")
            self.logger.info("=" * 60)
            
            # 如果有工具，添加 tool_choice
            if tools_schema:
                payload["tool_choice"] = "auto"  # 让模型自动决定是否调用工具
                self.logger.info(f"🔧 Added {len(tools_schema)} tools to LLM request")
            else:
                self.logger.warning(f"⚠️ No tools available for LLM request")

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
            
            # 🔍 诊断日志 - LLM 响应信息
            self.logger.info("=" * 60)
            self.logger.info("📥 LLM API 响应:")
            self.logger.info(f"  Choices Count: {len(data.get('choices', []))}")
            
            # 提取关键信息
            choices = data.get("choices", [])
            if choices:
                first = choices[0]
                finish_reason = first.get("finish_reason", "unknown")
                message_obj = first.get("message", {})
                content = message_obj.get("content") or ""
                tool_calls_raw = message_obj.get("tool_calls") or []
                
                # ⚠️ 关键诊断点：finish_reason
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
                
                # 显示 usage 信息（如果有）
                usage = data.get("usage", {})
                if usage:
                    self.logger.info(f"  Token Usage:")
                    self.logger.info(f"    - Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
                    self.logger.info(f"    - Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
                    self.logger.info(f"    - Total Tokens: {usage.get('total_tokens', 'N/A')}")
                
                # 显示响应内容前 200 字符（用于验证）
                if content:
                    preview = content[:200] + ("..." if len(content) > 200 else "")
                    self.logger.info(f"  Content Preview: {preview}")
                
                self.logger.info("=" * 60)
                
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
        # 🆕 思考阶段：准备调用 LLM
        if self.trace and session_id:
            yield self.trace.thinking_phase("准备 LLM 流式调用", "call_llm", session_id)
        
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

            # 获取工具定义（OpenAI 格式）
            self.logger.info(f"🔍 [Stream] Loading tools schema for streaming mode...")
            tools_schema = self._get_tools_schema()
            self.logger.info(f"🔍 [Stream] Tools schema loaded: {len(tools_schema) if tools_schema else 0} tools")

            payload = prepare_llm_params(
                model=config.get("model", self.config.llm.models.default),
                messages=messages,
                temperature=config.get("temperature", self.config.llm.temperature),
                max_tokens=config.get("max_tokens", self.config.llm.max_tokens),
                stream=True,
                tools=tools_schema if tools_schema else None  # 传递工具定义
            )
            
            # 🔍 诊断日志 - 流式请求参数
            self.logger.info("=" * 60)
            self.logger.info("📤 [STREAM] LLM API 请求参数:")
            self.logger.info(f"  Model: {payload.get('model')}")
            self.logger.info(f"  Max Tokens: {payload.get('max_tokens') or payload.get('max_completion_tokens')}")
            self.logger.info(f"  Temperature: {payload.get('temperature', 'N/A')}")
            self.logger.info(f"  Messages Count: {len(messages)}")
            self.logger.info(f"  Tools Count: {len(tools_schema) if tools_schema else 0}")
            self.logger.info(f"  Stream Mode: True")
            
            # 估算输入 token
            total_chars = sum(len(str(m.get('content', ''))) for m in messages)
            estimated_input_tokens = int(total_chars / 2)
            self.logger.info(f"  估算输入 Tokens: ~{estimated_input_tokens}")
            self.logger.info("=" * 60)
            
            # 如果有工具，添加 tool_choice
            if tools_schema:
                payload["tool_choice"] = "auto"
                self.logger.info(f"🔧 [Stream] Added {len(tools_schema)} tools to streaming LLM request")
            else:
                self.logger.warning(f"⚠️ [Stream] No tools available for streaming LLM request")
            
            # 使用提取的 URL 构建方法
            url = self._build_llm_url()
            
            self.logger.debug(f"LLM 流式调用目标: {url}")
            
            yield create_start_event(session_id=session_id, model=model)
            
            # 收集工具调用信息（流式返回时可能分散在多个 delta 中）
            collected_tool_calls = []
            
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
                            
                            # 处理文本内容
                            if 'content' in delta and delta['content']:
                                piece = delta['content']
                                full_text.append(piece)
                                yield create_delta_event(content=piece, session_id=session_id)
                            
                            # 收集工具调用（OpenAI 流式格式）
                            if 'tool_calls' in delta:
                                for tc_delta in delta['tool_calls']:
                                    idx = tc_delta.get('index', 0)
                                    # 确保 list 足够长
                                    while len(collected_tool_calls) <= idx:
                                        collected_tool_calls.append({
                                            'id': None,
                                            'type': 'function',
                                            'function': {'name': '', 'arguments': ''}
                                        })
                                    
                                    # 累积 id
                                    if 'id' in tc_delta:
                                        collected_tool_calls[idx]['id'] = tc_delta['id']
                                    
                                    # 累积 function name
                                    if 'function' in tc_delta:
                                        fn = tc_delta['function']
                                        if 'name' in fn:
                                            collected_tool_calls[idx]['function']['name'] += fn['name']
                                        if 'arguments' in fn:
                                            collected_tool_calls[idx]['function']['arguments'] += fn['arguments']
            
            # 检查是否有工具调用
            if collected_tool_calls:
                self.logger.info(f"🔧 [Stream] Detected {len(collected_tool_calls)} tool call(s), executing...")
                
                # 🆕 思考阶段：检测到工具调用
                if self.trace and session_id:
                    yield self.trace.llm_streaming("检测到工具调用", session_id, f"共 {len(collected_tool_calls)} 个工具")
                
                # 通知前端工具调用开始
                yield create_tool_calls_event(tool_calls=collected_tool_calls, session_id=session_id)
                
                # 执行所有工具
                tool_results = []
                for tc in collected_tool_calls:
                    try:
                        # 转换为 ToolCall 对象
                        tool_call = ToolCall(
                            id=tc.get('id') or f"tool_{int(datetime.now().timestamp())}",
                            name=tc['function']['name'],
                            arguments=json.loads(tc['function']['arguments']) if tc['function']['arguments'] else {}
                        )
                        
                        # 🆕 工具调用排队事件
                        if self.trace and session_id:
                            yield self.trace.tool_call_pending(tool_call.name, tool_call.arguments, session_id)
                        
                        # 🆕 工具执行中事件
                        if self.trace and session_id:
                            yield self.trace.tool_executing(tool_call.name, session_id)
                        
                        import time
                        tool_start_time = time.time()
                        
                        # 执行工具
                        result = await self._execute_tool_call(tool_call)
                        
                        tool_duration = (time.time() - tool_start_time) * 1000
                        
                        # 格式化工具结果内容（使用 result 属性，不是 data）
                        if result.success:
                            # result.result 可能是 JSON 字符串或其他类型
                            if isinstance(result.result, str):
                                result_content = result.result
                            elif isinstance(result.result, (dict, list)):
                                result_content = json.dumps(result.result, ensure_ascii=False)
                            else:
                                result_content = str(result.result)
                        else:
                            result_content = f"Error: {result.error}"
                        
                        # 🆕 工具结果事件
                        if self.trace and session_id:
                            summary = result_content[:100] + "..." if len(result_content) > 100 else result_content
                            yield self.trace.tool_result(
                                tool_call.name, 
                                result.success, 
                                summary, 
                                session_id,
                                tool_duration
                            )
                        
                        tool_results.append({
                            'tool_call_id': tool_call.id,
                            'role': 'tool',
                            'name': tool_call.name,
                            'content': result_content
                        })
                        
                        self.logger.info(f"✅ [Stream] Tool '{tool_call.name}' executed successfully, result length: {len(result_content)}")
                        
                    except Exception as e:
                        self.logger.error(f"❌ [Stream] Tool execution failed: {e}")
                        
                        # 🆕 工具失败事件
                        if self.trace and session_id:
                            yield self.trace.tool_result(
                                tc['function']['name'],
                                False,
                                f"执行失败: {str(e)}",
                                session_id
                            )
                        
                        tool_results.append({
                            'tool_call_id': tc.get('id', 'unknown'),
                            'role': 'tool',
                            'name': tc['function']['name'],
                            'content': f"Error: {str(e)}"
                        })
                
                # 🆕 思考阶段：基于工具结果再次调用 LLM
                if self.trace and session_id:
                    yield self.trace.llm_streaming("基于工具结果重新思考", session_id)
                
                # 将工具结果添加到消息历史，再次调用 LLM（流式）
                self.logger.info(f"🔄 [Stream] Calling LLM again with tool results...")
                
                # 构建新的消息列表
                new_messages = messages + [
                    {
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': collected_tool_calls
                    }
                ] + tool_results
                
                # 调试：打印消息结构
                self.logger.info(f"📋 [Stream] Final message count: {len(new_messages)}")
                self.logger.info(f"📋 [Stream] Last 3 messages roles: {[m.get('role', 'unknown') for m in new_messages[-3:]]}")
                
                # 递归调用自己，但不传递工具（避免无限循环）
                config_no_tools = config.copy()
                
                # 重新调用（这次是流式返回工具处理后的结果）
                async for event in self._stream_llm_with_tool_results(new_messages, config_no_tools, session_id):
                    yield event
                
                return
            
            # 没有工具调用，正常结束
            final_content = ''.join(full_text)
            
            # 🔍 诊断日志 - 流式响应总结
            self.logger.info("=" * 60)
            self.logger.info("📥 [STREAM] LLM 流式响应总结:")
            self.logger.info(f"  Total Content Length: {len(final_content)} 字符")
            self.logger.info(f"  Delta Events Count: {len(full_text)}")
            self.logger.info(f"  Tool Calls: {len(collected_tool_calls)}")
            
            # 显示内容前 200 字符
            if final_content:
                preview = final_content[:200] + ("..." if len(final_content) > 200 else "")
                self.logger.info(f"  Content Preview: {preview}")
            
            # ⚠️ 注意：流式响应通常不返回 finish_reason
            # 如果内容看起来被截断（突然结束），可能是 max_tokens 限制
            if len(final_content) > 5000:
                self.logger.warning("  ⚠️ 响应内容较长，如果看起来不完整，可能是 max_tokens 限制")
            
            self.logger.info("=" * 60)
            
            yield create_end_event(content=final_content, session_id=session_id)
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
    
    async def _stream_llm_with_tool_results(self, messages: List[Dict], config: Dict, session_id: Optional[str] = None):
        """在工具调用后继续流式返回 LLM 的最终响应（不再传递工具）"""
        self.logger.info(f"🎯 [Stream] Starting _stream_llm_with_tool_results with {len(messages)} messages")
        
        try:
            from api.event_utils import create_delta_event, create_end_event, create_error_event
        except ImportError:
            from datetime import datetime
            import uuid
            def create_delta_event(content, sid=None):
                evt = {"version": "1.0", "id": f"evt_{uuid.uuid4().hex[:16]}", 
                       "timestamp": datetime.utcnow().isoformat() + "Z", "type": "delta", "content": content}
                if sid: evt["session_id"] = sid
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
        
        try:
            await self._ensure_http_client()
            
            # 不再传递工具，避免无限递归
            payload = prepare_llm_params(
                model=config.get("model", self.config.llm.models.default),
                messages=messages,
                temperature=config.get("temperature", self.config.llm.temperature),
                max_tokens=config.get("max_tokens", self.config.llm.max_tokens),
                stream=True
                # tools=None  # 明确不传递工具
            )
            
            url = self._build_llm_url()
            full_response = []
            
            self.logger.info(f"🌐 [Stream] Calling LLM API for tool result processing...")
            
            async with self._http_client.stream('POST', url, json=payload) as resp:
                if resp.status_code >= 400:
                    text = await resp.aread()
                    raise RuntimeError(f"流式 HTTP 请求失败 {resp.status_code}: {text[:200]}")
                
                async for line in resp.aiter_lines():
                    if not line or not line.startswith('data:'):
                        continue
                    
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
                            full_response.append(piece)
                            self.logger.debug(f"📤 [Stream] Yielding delta: {piece[:50]}...")
                            yield create_delta_event(content=piece, session_id=session_id)
            
            final_content = ''.join(full_response)
            self.logger.info(f"✅ [Stream] Tool result processing complete, total length: {len(final_content)}")
            yield create_end_event(content=final_content, session_id=session_id)
            
        except Exception as e:
            self.logger.error(f"工具结果流式调用失败: {e}")
            yield create_error_event(error=str(e), session_id=session_id)
    
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
    
    def _is_simple_greeting(self, text: str) -> bool:
        """检测是否为简单问候语
        
        用于快速响应优化，跳过 LLM 调用以降低延迟。
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否为简单问候
        """
        text_lower = text.lower().strip()
        
        # 简单问候关键词列表
        simple_greetings = [
            # 英文
            "hi", "hello", "hey", "hola", "yo",
            # 中文
            "你好", "您好", "嗨", "哈喽", "嘿",
            "早", "早上好", "中午好", "下午好", "晚上好",
            "晚安", "hi~", "hello~", "嗨~"
        ]
        
        # 精确匹配（去除标点符号）
        clean_text = text_lower.strip("!！?？.。,，~")
        return clean_text in simple_greetings
    
    def _get_greeting_response(self) -> str:
        """获取问候响应
        
        Returns:
            随机问候响应
        """
        import random
        
        responses = [
            "你好！很高兴见到你！有什么我可以帮助的吗？😊",
            "嗨！我是你的 AI 助手，随时为你服务！",
            "您好！请问有什么可以帮到您的吗？",
            "Hi！很高兴能帮到你！✨",
            "你好呀！有什么问题尽管问我～"
        ]
        
        return random.choice(responses)
    
    async def _execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """执行工具调用（带缓存优化）
        
        检查缓存以避免重复执行相同的工具调用，提升性能并降低外部 API 费用。
        
        Args:
            tool_call: 工具调用对象
            
        Returns:
            工具执行结果
        """
        try:
            # 🆕 缓存优化：检查是否可以使用缓存结果
            cache_key = self._generate_tool_cache_key(tool_call)
            
            if cache_key in self._tool_cache:
                cached_result, cached_time = self._tool_cache[cache_key]
                cache_age = time.time() - cached_time
                
                # 检查缓存是否仍然有效
                if cache_age < self._cache_ttl:
                    self.logger.info(f"🎯 使用缓存的工具结果: {tool_call.name} (缓存 {int(cache_age)}秒前)")
                    # 创建新的 ToolResult 对象，使用当前的 call_id
                    return ToolResult(
                        call_id=tool_call.id,
                        success=cached_result.success,
                        result=cached_result.result,
                        error=cached_result.error
                    )
                else:
                    # 缓存过期，删除
                    del self._tool_cache[cache_key]
                    self.logger.debug(f"缓存已过期，重新执行工具: {tool_call.name}")
            
            # 执行工具调用（无缓存或缓存过期）
            result = await self._execute_tool_call_uncached(tool_call)
            
            # 🆕 缓存成功的结果
            if result.success:
                self._tool_cache[cache_key] = (result, time.time())
                self.logger.debug(f"工具结果已缓存: {tool_call.name}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Tool execution error: {e}", exc_info=True)
            return ToolResult(
                call_id=tool_call.id,
                success=False,
                result=None,
                error=str(e)
            )
    
    def _generate_tool_cache_key(self, tool_call: ToolCall) -> str:
        """生成工具调用的缓存键
        
        基于工具名称和参数生成唯一的缓存键。
        
        Args:
            tool_call: 工具调用对象
            
        Returns:
            缓存键字符串
        """
        # 将参数排序后序列化，确保相同参数生成相同的键
        args_str = json.dumps(tool_call.arguments, sort_keys=True, ensure_ascii=False)
        return f"{tool_call.name}:{args_str}"
    
    async def _execute_tool_call_uncached(self, tool_call: ToolCall) -> ToolResult:
        """执行工具调用（无缓存，实际执行）
        
        Args:
            tool_call: 工具调用对象
            
        Returns:
            工具执行结果
        """
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
            self.logger.error(f"Tool execution error in uncached call: {e}", exc_info=True)
            return ToolResult(
                call_id=tool_call.id,
                success=False,
                result=None,
                error=str(e)
            )