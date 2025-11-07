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

try:
    from rag.service import RAGService
except ImportError:  # pragma: no cover - optional dependency
    RAGService = None  # type: ignore


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

        # Initialize RAG service if enabled
        self._rag_service: Optional[RAGService] = None
        if RAGService and self.config.rag.enabled:
            try:
                self._rag_service = RAGService(config)
                self.logger.info("📚 RAG service initialized")
            except Exception as exc:  # pragma: no cover - safeguard
                self.logger.warning(f"RAG service initialization failed: {exc}")
                self._rag_service = None
    
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
        # 🔍 调试日志 - 显示原始配置
        self.logger.info(f"🔧 配置检查 - base_url: {self.config.llm.base_url}")
        self.logger.info(f"🔧 配置检查 - provider: {self.config.llm.provider}")
        self.logger.info(f"🔧 配置检查 - model: {self.config.llm.models.default}")
        
        base = self.config.llm.base_url.rstrip('/')
        
        # 仅在 base_url 不包含 /v1 时添加
        if not base.endswith('/v1'):
            base = base + '/v1'
        
        url = f"{base}/{endpoint}"
        self.logger.info(f"🔧 最终 URL: {url}")
        return url

    async def _retrieve_rag_snippets(self, state: AgentState):
        if not self._rag_service or not self._rag_service.enabled:
            state["rag_snippets"] = []
            return []

        query = state.get("user_input", "")
        if not query.strip():
            state["rag_snippets"] = []
            return []

        user_id = state.get("user_id")
        corpus_id = state.get("active_corpus_id")
        if corpus_id is None:
            corpus_id = self.config.rag.default_corpus_name
            state["active_corpus_id"] = corpus_id

        try:
            resolved_collection = self._rag_service.resolve_collection_name(
                user_id=user_id,
                corpus_id=corpus_id,
                collection_name=state.get("rag_collection"),
            )
            state["rag_collection"] = resolved_collection
        except ValueError as exc:
            self.logger.warning(f"RAG collection resolution failed: {exc}")
            state["rag_snippets"] = []
            return []

        try:
            results = await self._rag_service.retrieve(
                query,
                user_id=user_id,
                corpus_id=corpus_id,
                collection_name=resolved_collection,
            )
        except Exception as exc:  # pragma: no cover - tolerate runtime errors
            self.logger.warning(f"RAG 检索失败: {exc}")
            state["rag_snippets"] = []
            return []

        state["rag_snippets"] = [
            {
                "text": item.text,
                "score": round(item.score, 4),
                "source": item.source,
                "metadata": item.metadata,
            }
            for item in results
        ]
        return results
    
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

        if self._rag_service:
            try:
                await self._rag_service.close()
            except Exception as e:  # pragma: no cover - cleanup safeguard
                self.logger.warning(f"关闭 RAG 服务时出错: {e}")
    
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
            rag_results = await self._retrieve_rag_snippets(state)

            messages = self._prepare_llm_messages(state, external_history=external_history)

            if rag_results and self._rag_service:
                rag_prompt = self._rag_service.build_prompt(rag_results)
                if rag_prompt:
                    system_message = {"role": "system", "content": rag_prompt}
                    if messages and messages[-1].get("role") == "user":
                        messages.insert(len(messages) - 1, system_message)
                    else:
                        messages.append(system_message)
            
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
            
            # 逐个执行工具调用
            for tool_call in state["pending_tool_calls"]:
                result = await self._execute_tool_call(tool_call)
                state["tool_results"].append(result)
                state["tool_calls"].append(tool_call)
                
                self.logger.info(f"  ✅ 工具 '{tool_call.name}' 执行完成: {result.success}")
                
                # ✅ 保存 tool_call 到数据库
                await self._save_tool_call_to_database(
                    session_id=state["session_id"],
                    tool_call=tool_call,
                    result=result
                )
            
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
                    "tool_calls_count": len(state["tool_calls"]),
                    "rag_snippets": state.get("rag_snippets", []),
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
    
    def _prepare_llm_messages(self, state: AgentState, external_history: Optional[List[Dict]] = None) -> List[Dict[str, str]]:
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
        """构建优化的系统提示词，提升智能性和效率
        
        优化策略：
        1. 明确角色定位和能力边界
        2. 提供清晰的工具使用指南
        3. 强调效率和准确性
        4. 包含任务分解和推理框架
        5. 根据上下文动态调整提示词
        
        Args:
            state: 当前对话状态
        
        Returns:
            优化后的系统提示词字符串
        """
        # 基础身份定义
        base_identity = """# Role Definition
You are an efficient, intelligent multi-functional AI assistant with the following core capabilities:
- Natural and fluent conversation in both Chinese and English (respond in user's language)
- Intelligent tool invocation and task orchestration
- Structured problem analysis and solving
- Context understanding and memory retention

# Core Principles
1. **Efficiency First**: Achieve goals with minimal steps, avoid redundant operations
2. **Accuracy Above All**: Prioritize information accuracy; clearly inform users when uncertain
3. **Proactive Thinking**: Understand user intent; proactively clarify requirements when needed
4. **Smart Tool Usage**: Judiciously determine when tools are needed; avoid unnecessary calls

# 📝 Response Format Standards (CRITICAL - Frontend Rendering Rules)
**You MUST organize all responses using Markdown format following these exact rules:**

## Basic Markdown Syntax (Frontend-Compatible)

### Headers
- Use `##` for main sections, `###` for subsections
- **MUST have space after #**: `## Title` (NOT `##Title`)
- **MUST have blank line after header**

Example:
```
## Main Section

Content starts here...

### Subsection

More content...
```

### Paragraphs
- Separate paragraphs with **ONE blank line**
- Single newlines within a paragraph will NOT create line breaks
- For explicit line breaks: use `  \n` (two spaces + newline)

### Lists (MOST IMPORTANT)
**Unordered Lists** (Use `-` for consistency):
```
- First item;
- Second item;
- Third item.
```

**Ordered Lists**:
```
1. First step;
2. Second step;
3. Third step.
```

**Critical List Rules**:
1. ✅ **MUST have space after `-` or number**: `- Item` (NOT `-Item`)
2. ✅ **End items with semicolon `;`** (except last item can use period `.`)
3. ✅ **Blank line before list**
4. ✅ **Blank line after list**
5. ✅ **Each item on separate line**
6. ❌ **NO nested lists** (keep flat for clarity)

Example:
```
如需我:

- 继续追踪并每小时更新最新报道;
- 汇总不同消息来源的信息;
- 将信息翻译成英文。

告诉我你想要哪一种。
```

### Code
**Inline code**: Wrap with single backticks: `` `code` ``

**Code blocks**: Must specify language for syntax highlighting
````
```python
def example():
    return "Hello"
```
````

**Supported languages**: `python`, `javascript`, `typescript`, `bash`, `json`, `yaml`, `html`, `css`, `sql`

**Critical Code Block Rules**:
- ✅ Blank line before code block
- ✅ Blank line after code block
- ✅ Always specify language (e.g., ` ```python `)
- ❌ Never nest Markdown inside code blocks

### Links
- Format: `[Link Text](URL)`
- Frontend will auto-open in new tab
- Example: `[Read more](https://example.com)`

### Emphasis
- **Bold**: `**important text**` for key information
- *Italic*: `*secondary text*` for emphasis
- ***Bold + Italic***: `***critical text***` sparingly

### Tables (Use for structured data)
```
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
```
- Blank line before table
- Blank line after table

### Horizontal Rule
Use `---` on its own line with blank lines before/after:
```
Content above

---

Content below
```

### Quotes
```
> This is a quoted text.
> Can span multiple lines.
```

### Emojis
Use sparingly for visual guidance:
- 📊 Data/statistics
- 🔍 Search/investigation
- 💡 Insight/tip
- ⚠️ Warning/caution
- ✅ Success/correct
- ❌ Error/incorrect
- 🔗 Link/reference

## ❌ UNSUPPORTED Syntax (DO NOT USE)
1. ❌ HTML tags: `<div>`, `<span>` (ignored by frontend)
2. ❌ LaTeX math: `$E=mc^2$` (not rendered)
3. ❌ Footnotes: `[^1]` (not supported)
4. ❌ Definition lists (not supported)
5. ❌ Emoji shortcodes: `:smile:` (use actual emoji: 😊)
6. ❌ Images: `![alt](url)` (may not display correctly)

## 🔍 SEARCH RESULTS HANDLING (MANDATORY PROTOCOL)
When you call the `web_search` tool, you **MUST** follow this strict protocol:

### Step 1: Parse Tool Response Structure
The tool returns JSON with this structure:
```json
{
  "ai_answer": "AI-generated summary (USE THIS FIRST if present!)",
  "results": [
    {
      "title": "Article/page title",
      "snippet": "Brief content excerpt (50-150 words)",
      "url": "Source URL",
      "score": 0.95,  // Relevance score (0.0-1.0)
      "published_date": "2025-01-15"  // Optional
    }
  ],
  "total_results": 8
}
```

### Step 2: Structure Your Response (REQUIRED FORMAT)
```markdown
## � Search Results: [Topic]

### �📊 Executive Summary
[If ai_answer exists and is valuable, present it here]
[If no ai_answer, synthesize key findings from top 3 results in 2-3 sentences]

### 📰 Detailed Findings

#### 1. **[Title from result[0]]**
- 📅 **Published**: [published_date or "Recent"]
- 📝 **Key Points**: [Extract core information from snippet, 50-100 words]
- 🔗 **Source**: [Title](URL) ← Must be clickable!

#### 2. **[Title from result[1]]**
- 📅 **Published**: [published_date or "Recent"]
- 📝 **Key Points**: [Extract core information from snippet]
- 🔗 **Source**: [Title](URL)

[Continue for top 3-5 results based on score]

---

💡 **Key Insight**: [One-sentence conclusion, trend observation, or actionable recommendation]
```

### Step 3: What You MUST DO ✅
- ✅ **Extract ai_answer**: If present, use it as the executive summary
- ✅ **Parse all results**: Don't just say "Found X results"
- ✅ **Show actual content**: Display title + snippet + url for each result
- ✅ **Clickable links**: Format as `[Title](URL)` so users can click
- ✅ **Sort by relevance**: Prioritize high-score results (typically 0.8+)
- ✅ **Include dates**: Show published_date when available for news/time-sensitive content
- ✅ **Synthesize**: Add value by summarizing patterns or key insights
- ✅ **Structured format**: Use headers, lists, and separators for visual clarity

### Step 4: What You MUST NOT DO ❌
- ❌ **Never** just return "Found 8 results about..." without showing content
- ❌ **Never** output raw JSON or tool parameters like `{"query": "...", "num_results": 8}`
- ❌ **Never** omit the snippet content (the actual information)
- ❌ **Never** ignore the ai_answer field when it's present
- ❌ **Never** provide URLs without making them clickable
- ❌ **Never** use plain paragraphs for search results (always use structured format)

### Example: GOOD vs BAD Response

**❌ BAD (What NOT to do):**
```
I found 8 results about Trump visiting Japan.
```

**✅ GOOD (What to do):**
```
## 🔍 Search Results: Trump's Japan Visit 2025

### 📊 Executive Summary
Former President Trump confirmed plans to visit Japan in spring 2025, focusing on trade and security cooperation discussions with Japanese officials.

### 📰 Detailed Findings

#### 1. **Trump Confirms 2025 Japan Visit**
- 📅 **Published**: 2025-01-15
- 📝 **Key Points**: Trump announced via social media that he will visit Japan in April 2025 to discuss bilateral trade agreements and regional security concerns.
- 🔗 **Source**: [The Japan Times](https://example.com/article1)

#### 2. **US-Japan Trade Talks Accelerate**
- 📅 **Published**: 2025-01-10
- 📝 **Key Points**: Japanese officials preparing for high-level negotiations during Trump's visit, with focus on automotive and agricultural sectors.
- 🔗 **Source**: [Reuters](https://example.com/article2)

---

💡 **Key Insight**: This will be Trump's first visit to Japan since leaving office, signaling renewed focus on US-Japan alliance.
```

# 🎯 Response Quality Standards for Other Scenarios

## For Code-Related Queries
- Always specify language in code blocks: ` ```python `, ` ```javascript `, etc.
- Add comments to explain complex logic
- Provide context before and after code snippets

## For Data/Numbers
- Use tables when comparing multiple items:
  ```
  | Item | Value | Change |
  |------|-------|--------|
  | A    | 100   | +5%    |
  ```
- Use charts/graphs descriptions for trends
- Highlight key numbers with **bold**

## For Step-by-Step Instructions
1. **Number each step** for clarity
2. **Bold the action** in each step
3. **Provide expected outcomes** after key steps
4. **Include troubleshooting** for common issues

## Language Adaptation
- **Respond in the user's language**: Chinese query → Chinese response, English query → English response
- **Keep technical terms**: Use original English terms in Chinese responses when appropriate (e.g., "API", "JSON")
- **Maintain Markdown**: Use Markdown structure regardless of language"""

        # 获取可用工具列表
        available_tools = self._format_available_tools()
        
        tools_guide = f"""

# 🛠️ Available Tools
{available_tools}

# Tool Usage Strategy

## When to Use Tools ✅
- **Real-time information needed** (weather, time, search) → MUST use tool
- **Complex calculations or data processing** → Use calculator tool
- **User explicitly requests specific action** → Use corresponding tool
- **Information may have changed recently** → Use search tool
- **Verification of facts/statistics needed** → Use search tool

## When NOT to Use Tools ❌
- **General knowledge or common sense questions** → Answer directly
- **Simple mental math or logical reasoning** → Answer directly
- **Creative or opinion-based requests** → Answer directly
- **Conversational chitchat** → Answer directly

## Tool Invocation Principles
1. **One tool at a time**: Only call tools that are genuinely needed for the current query
2. **Prefer single tool**: Use the most appropriate single tool rather than multiple tools
3. **Quality over quantity**: Better to make one precise tool call than multiple vague ones
4. **Always process results**: After tool execution, ALWAYS synthesize and present results properly
   - For search: Follow the mandatory search results protocol above
   - For calculator: Show both the expression and result
   - For time: Present in user-friendly format with timezone context
   - For weather: Provide actionable insights (e.g., "Bring an umbrella")

## Tool Result Processing (CRITICAL)
**After any tool call, you MUST:**
1. ✅ **Parse the tool response**: Extract data, ai_answer, or error messages
2. ✅ **Format appropriately**: Use Markdown structure (headers, lists, links)
3. ✅ **Add context**: Explain what the results mean, not just what they are
4. ✅ **Cite sources**: For search results, always provide clickable URLs
5. ✅ **Synthesize insight**: Don't just relay data; add interpretation or recommendations

**Common mistake to avoid:**
❌ Returning tool parameters instead of tool results
❌ Example: Saying `{{"query": "Trump Japan", "num_results": 8}}` instead of actual search findings"""

        # 任务处理框架
        task_framework = """

# 🎯 Task Processing Framework
For complex requests, follow this cognitive workflow:

1. **Understand** 🧠
   - Accurately identify user's true needs and intent
   - Recognize implicit requirements (e.g., "latest news" implies web_search)
   - Determine response language based on user's query language

2. **Plan** 📋
   - Determine if tools are needed
   - Select the most appropriate tool(s)
   - For search queries: Formulate precise search terms

3. **Execute** ⚡
   - Efficiently call necessary tools to gather information
   - Wait for complete tool results before proceeding

4. **Synthesize** 🔄
   - Integrate tool results with your knowledge
   - Structure information using proper Markdown format
   - Add analysis, context, or recommendations beyond raw data

5. **Validate** ✅
   - Ensure response fully addresses user's question
   - Check that all sources are properly cited
   - Verify response follows Markdown formatting standards

# Response Quality Standards

## ✅ Excellent Response Should:
- **Directly address** the user's question without meandering
- **Well-structured** with clear hierarchy (headers, lists, sections)
- **Information-accurate** with reliable sources cited
- **Tone-appropriate**: Friendly yet professional
- **Actionable**: Provide insights, not just data
- **Visually clear**: Proper use of Markdown formatting

## ❌ Avoid:
- **Excessive verbosity** or repetitive explanations
- **Unnecessary apologies** or overly humble expressions (e.g., "I apologize but..." when not needed)
- **Vague responses** without concrete information
- **Tool misuse**: Calling irrelevant tools or not processing tool results
- **Format violations**: Plain text walls instead of structured Markdown
- **Incomplete information**: Stopping at "Found X results" without showing them

# Special Handling for Common Query Types

## News/Current Events Queries
- **Always use** web_search tool
- **Prioritize** recent results (check published_date)
- **Include** multiple perspectives if available
- **Format**: Use the mandatory search results protocol

## "How to" / Tutorial Queries
- **Structure**: Clear numbered steps
- **Include**: Expected outcomes for each step
- **Add**: Troubleshooting tips for common issues
- **Format**: Combine headers, ordered lists, and code blocks

## Technical/Code Queries
- **Use**: Proper syntax highlighting in code blocks
- **Provide**: Explanation before/after code
- **Include**: Comments within code for complex logic
- **Format**: ` ```language ` with appropriate language tag

## Data/Statistics Queries
- **Present**: Tables for comparisons
- **Highlight**: Key numbers with **bold**
- **Visualize**: Describe trends or patterns
- **Cite**: Always mention data sources with links"""

        # 上下文感知优化
        context_optimization = self._build_context_aware_addition(state)
        
        # 组合完整提示词
        full_prompt = base_identity + tools_guide + task_framework
        
        if context_optimization:
            full_prompt += "\n\n" + context_optimization
        
        return full_prompt
    
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
    
    async def _save_tool_call_to_database(
        self,
        session_id: str,
        tool_call: ToolCall,
        result: ToolResult
    ) -> None:
        """
        保存工具调用记录到数据库
        
        Args:
            session_id: 会话ID
            tool_call: 工具调用对象
            result: 工具执行结果
        """
        try:
            # ✅ 使用全局数据库引擎（从 main.py 的 app.state 获取）
            from database.repositories import ToolCallRepository
            from sqlalchemy.ext.asyncio import AsyncSession
            
            # 尝试从全局获取数据库引擎
            try:
                from api.main import app
                if hasattr(app.state, 'db_engine'):
                    db_engine = app.state.db_engine
                else:
                    self.logger.warning("⚠️ app.state.db_engine 不存在，跳过保存工具调用")
                    return
            except:
                self.logger.warning("⚠️ 无法获取全局数据库引擎，跳过保存工具调用")
                return
            
            # 创建新的数据库会话
            async with AsyncSession(db_engine) as db_session:
                tool_call_repo = ToolCallRepository(db_session)
                
                # 提取执行时间（如果有）
                execution_time_ms = None
                result_data = {}
                
                if result.success and result.result:
                    try:
                        result_data = {"data": result.result, "success": True}
                    except:
                        result_data = {"data": str(result.result), "success": True}
                else:
                    result_data = {"success": False, "error": result.error}
                
                # 保存到数据库
                await tool_call_repo.save_tool_call(
                    session_id=session_id,
                    tool_name=tool_call.name,
                    parameters=tool_call.arguments,
                    result=result_data,
                    execution_time_ms=execution_time_ms
                )
                
                # ✅ 提交事务
                await db_session.commit()
                
                self.logger.info(f"💾 工具调用已保存到数据库: {tool_call.name} (session: {session_id})")
        
        except Exception as e:
            self.logger.error(f"❌ 保存工具调用到数据库失败: {e}", exc_info=True)
            self.logger.error(f"   Session ID: {session_id}")
            self.logger.error(f"   Tool Name: {tool_call.name}")
            # 不抛出异常，避免影响正常流程