# AI Assistant 上手指南

**项目名称**: Ivan_HappyWoods - Voice-Based AI Agent Interaction System  
**目标读者**: AI Assistant (GitHub Copilot, Cursor, Claude, GPT-4, etc.)  
**版本**: 0.2.0-beta  
**最后更新**: 2025-10-15

---

## 📌 目的

本文档旨在帮助 AI Assistant 快速理解 Ivan_HappyWoods 项目,使其能够:
1. ✅ 准确理解项目当前状态和架构
2. ✅ 提供符合项目规范的代码建议
3. ✅ 快速定位相关文档和代码
4. ✅ 遵循项目的开发约定和最佳实践

---

## 🚀 第一步: 快速上下文刷新 (5分钟)

### 必读文档顺序

```
1. PROJECT.md (5分钟) ⭐⭐⭐⭐⭐
   └─ 重点阅读: "Copilot Context Refresh" 章节
   └─ 内容: 完整架构、技术栈、当前状态

2. progress.md (3分钟) ⭐⭐⭐⭐
   └─ 位置: specs/001-voice-interaction-system/progress.md
   └─ 内容: 详细进度、已完成/进行中任务

3. CHANGELOG.md (2分钟) ⭐⭐⭐
   └─ 内容: 最近变更、版本历史

4. .github/copilot-instructions.md (2分钟) ⭐⭐⭐⭐⭐
   └─ 内容: 代码约定、特殊处理逻辑
```

**总时间**: 约 12 分钟即可掌握 80% 项目上下文

---

## 📊 第二步: 理解项目状态 (当前快照)

### 项目总体状态

```
当前版本: v0.2.0-beta
开发阶段: Phase 2 Complete (80% Overall)
最后更新: 2025-10-15

Phase 1 (Core Foundation)        ████████████████████ 100% ✅
Phase 2A (Voice Integration)     ████████████████████ 100% ✅
Phase 2B (Streaming TTS)         ████████████████████ 100% ✅
Phase 2C (Conversation API)      ████████████████████ 100% ✅
Phase 2D (Code Optimization)     ████████████████████ 100% ✅
Phase 2E (MCP Tools)             ░░░░░░░░░░░░░░░░░░░░   0% ⏳
Phase 3 (Production Ready)       ░░░░░░░░░░░░░░░░░░░░   0% 📋
```

### 当前能力矩阵

| 功能 | 状态 | 可用性 | 备注 |
|------|------|--------|------|
| 文本对话 | ✅ | 生产可用 | 非流式 + SSE + WebSocket |
| 语音识别 (STT) | ✅ | 生产可用 | iFlytek WebSocket |
| 语音合成 (TTS) | ✅ | 生产可用 | <500ms TTFB, 流式 |
| 会话管理 | ✅ | 开发可用 | 内存存储, 重启丢失 |
| 流式响应 | ✅ | 生产可用 | SSE + WebSocket |
| API 认证 | ✅ | 生产可用 | API Key |
| 对话历史 | ✅ | 生产可用 | 查询 + 清除 API |
| MCP 工具 | ⏳ | 未实现 | Phase 2E 规划中 |
| Redis 存储 | 📋 | 未实现 | Phase 3 规划中 |
| 容器化 | 📋 | 未实现 | Phase 3 规划中 |

### 关键决策点 (AI 必知)

1. **语音服务**: 使用 iFlytek (科大讯飞), 非 OpenAI Whisper
   - 原因: 中文优化、低延迟、成本优势
   - 位置: `src/services/voice/`

2. **会话存储**: 内存 (LangGraph MemorySaver), 非数据库
   - 原因: MVP 简化开发
   - 限制: 重启丢失数据
   - 迁移计划: Phase 3 Redis

3. **LLM 兼容性**: OpenAI-compatible, 当前 gpt-5-mini
   - 特殊处理: GPT-5 系列不支持 temperature 参数
   - 位置: `src/utils/llm_compat.py`

4. **代码本地化**: 中文注释、错误消息、日志
   - 原因: 用户体验 + 团队效率
   - 代码: 英文变量/函数名

5. **资源管理**: Async context manager
   - 模式: `async with AgentNodes(...) as nodes:`
   - 原因: 防止 HTTP 客户端泄漏

---

## 🏗️ 第三步: 掌握架构 (核心概念)

### 架构层次

```
┌─────────────────────────────────────┐
│         Client Layer                │
│  (Web/Mobile/Voice Device)          │
└──────────────┬──────────────────────┘
               │ HTTP/WebSocket
               ▼
┌─────────────────────────────────────┐
│      FastAPI Gateway Layer          │
│  • REST API (conversation_routes)   │
│  • WebSocket (streaming)            │
│  • Middleware (CORS/Auth/Logging)   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       Service Layer                 │
│  • ConversationService (会话管理)   │
│  • VoiceService (STT/TTS)           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       Agent Core (LangGraph)        │
│  • VoiceAgent (graph.py)            │
│  • AgentNodes (nodes.py)            │
│  • AgentState (state.py)            │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌──────────────┐ ┌──────────────┐
│   LLM API    │ │ Voice APIs   │
│ (OpenAI-     │ │  (iFlytek)   │
│  compatible) │ │              │
└──────────────┘ └──────────────┘
```

### 对话流程 (AI 必须理解)

```
用户输入 (文本/语音)
    │
    ▼
┌─────────────────────┐
│ 1. process_input    │ ← nodes.py::process_input()
│    - 验证输入        │
│    - 更新历史        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 2. call_llm         │ ← nodes.py::call_llm() / stream_llm_call()
│    - 构建提示词      │
│    - 调用 LLM API   │
│    - 处理响应        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 3. handle_tools     │ ← nodes.py::handle_tools() (未实现)
│    (Phase 2E)       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 4. format_response  │ ← nodes.py::format_response()
│    - 格式化输出      │
│    - 更新状态        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 5. TTS (可选)       │ ← services/voice/tts_service.py
│    - 文本转语音      │
│    - 流式推送        │
└─────────────────────┘
```

---

## 📁 第四步: 代码导航地图

### 核心文件清单 (AI 应当熟悉)

```
🔥 超高频访问 (每次修改对话逻辑时)
├── src/agent/graph.py (375 lines)
│   └─ VoiceAgent 类, LangGraph 工作流定义
│
├── src/agent/nodes.py (768 lines) ⭐ 最重要
│   └─ AgentNodes 类, 所有处理节点实现
│   └─ process_input(), call_llm(), stream_llm_call(), 
│       handle_tools(), format_response()
│
└── src/agent/state.py
    └─ AgentState 状态模型

🔥 高频访问 (API 开发时)
├── src/api/conversation_routes.py
│   └─ 对话端点: /send, /stream, /history, /clear
│
├── src/api/voice_routes.py
│   └─ 语音端点: /stt, /tts, /stream
│
└── src/api/main.py
    └─ FastAPI 应用入口

🔥 中频访问 (配置/工具时)
├── src/config/models.py
│   └─ Pydantic 配置模型
│
├── src/utils/llm_compat.py ⭐ 重要
│   └─ LLM 兼容层 (GPT-5 处理)
│
├── src/services/voice/stt_service.py
│   └─ iFlytek STT 实现
│
└── src/services/voice/tts_service.py
    └─ iFlytek TTS 实现

🔥 低频访问 (但需要知道存在)
├── src/api/middleware.py
│   └─ CORS, 认证, 日志中间件
│
├── src/api/auth.py
│   └─ API Key 认证逻辑
│
└── src/services/conversation_service.py
    └─ 会话管理服务
```

### 文件职责速查表

| 文件 | 职责 | 何时修改 |
|------|------|----------|
| `graph.py` | LangGraph 工作流编排 | 添加新节点、修改路由 |
| `nodes.py` | 节点实现逻辑 | 修改对话处理、LLM 调用 |
| `state.py` | 状态模型定义 | 添加新状态字段 |
| `conversation_routes.py` | 对话 API | 添加新端点、修改请求/响应 |
| `voice_routes.py` | 语音 API | 修改 STT/TTS 逻辑 |
| `llm_compat.py` | LLM 兼容性处理 | 添加新模型兼容逻辑 |
| `models.py` | 配置模型 | 添加新配置项 |

---

## 🎯 第五步: 代码约定 (AI 必须遵守)

### 1. 命名规范

```python
# Classes: PascalCase
class VoiceAgent:
    pass

# Functions: snake_case
async def process_input(state: AgentState) -> AgentState:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_HISTORY_MESSAGES = 10

# Private: _leading_underscore
def _ensure_http_client(self):
    pass
```

### 2. 文档字符串 (必须中文)

```python
async def process_input(self, state: AgentState) -> AgentState:
    """
    处理用户输入节点
    
    功能:
    1. 验证用户输入
    2. 更新对话历史
    3. 设置下一个节点
    
    Args:
        state: 当前对话状态
        
    Returns:
        更新后的状态,包含 next_action 字段
    """
    # 实现...
```

### 3. 错误消息 (必须中文)

```python
# ✅ 正确
raise ValueError("抱歉,处理消息时发生错误")
logger.error(f"LLM 调用失败: {str(e)}")

# ❌ 错误
raise ValueError("Failed to process message")
logger.error(f"LLM call failed: {str(e)}")
```

### 4. 日志消息 (必须中文)

```python
# ✅ 正确
self.logger.info(f"开始处理会话: {session_id}")
self.logger.debug(f"LLM 响应: {response[:100]}")

# ❌ 错误
self.logger.info(f"Processing session: {session_id}")
```

### 5. 代码注释 (可以英文,推荐中文)

```python
# ✅ 推荐
# 初始化 HTTP 客户端 (懒加载模式)
await self._ensure_http_client()

# ✅ 可接受
# Initialize HTTP client (lazy loading)
await self._ensure_http_client()
```

### 6. 变量和函数名 (必须英文)

```python
# ✅ 正确
user_input = state["user_input"]
session_id = state["session_id"]

# ❌ 错误 (不要用拼音)
yonghu_shuru = state["user_input"]
huihua_id = state["session_id"]
```

---

## 🔧 第六步: 常见模式 (AI 应掌握)

### 模式 1: 添加 LangGraph 节点

```python
# 步骤 1: 在 src/agent/nodes.py 添加节点方法
class AgentNodes:
    async def my_new_node(self, state: AgentState) -> AgentState:
        """
        新节点功能描述
        
        处理逻辑:
        1. 步骤一
        2. 步骤二
        """
        # 节点逻辑
        result = await self._process_something(state)
        
        # 更新状态
        state["my_field"] = result
        state["next_action"] = "next_node"
        
        return state

# 步骤 2: 在 src/agent/graph.py 注册节点
def _build_graph(self):
    workflow = StateGraph(AgentState)
    
    # 注册节点
    workflow.add_node("my_new_node", self.nodes.my_new_node)
    
    # 添加边
    workflow.add_edge("previous_node", "my_new_node")
    workflow.add_edge("my_new_node", "next_node")
    
    # 或条件边
    workflow.add_conditional_edges(
        "my_new_node",
        self._route_after_my_node,
        {
            "path_a": "node_a",
            "path_b": "node_b"
        }
    )
```

### 模式 2: 添加 API 端点

```python
# 步骤 1: 在 src/api/models.py 定义模型
from pydantic import BaseModel

class MyRequest(BaseModel):
    session_id: str
    param: str

class MyResponse(BaseModel):
    result: str
    status: str

# 步骤 2: 在 src/api/conversation_routes.py (或新文件) 实现路由
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/conversation", tags=["Conversation"])

@router.post("/my-endpoint", response_model=MyResponse)
async def my_endpoint(request: MyRequest):
    """
    端点功能描述
    
    Args:
        request: 请求参数
        
    Returns:
        处理结果
    """
    try:
        # 业务逻辑
        result = await process_data(request.param)
        return MyResponse(result=result, status="success")
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

# 步骤 3: 在 src/api/main.py 注册路由 (如果是新文件)
from api.my_routes import router as my_router
app.include_router(my_router)
```

### 模式 3: LLM 调用 (兼容性处理)

```python
from src.utils.llm_compat import prepare_llm_params

async def call_llm(self, state: AgentState) -> AgentState:
    """调用 LLM API"""
    
    # 1. 构建消息
    messages = self._build_messages(state)
    
    # 2. 准备参数 (处理 GPT-5 兼容性)
    model = self.config.llm.models.default
    params = prepare_llm_params(
        model=model,
        messages=messages,
        temperature=0.7,  # GPT-5 会自动移除
        max_tokens=2048
    )
    
    # 3. 确保 HTTP 客户端已初始化
    await self._ensure_http_client()
    
    # 4. 调用 API
    url = self._build_llm_url()
    response = await self._http_client.post(
        url,
        json=params,
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    # 5. 处理响应
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    
    # 6. 更新状态
    state["llm_response"] = content
    state["next_action"] = "format_response"
    
    return state
```

### 模式 4: 资源管理 (必须使用)

```python
# ✅ 推荐: 使用 async context manager
from src.agent.nodes import AgentNodes

async def process_conversation(config):
    async with AgentNodes(config) as nodes:
        result = await nodes.process_input(state)
        # 自动清理资源
    
# ✅ 可接受: 手动清理
nodes = AgentNodes(config)
try:
    result = await nodes.process_input(state)
finally:
    await nodes.cleanup()

# ❌ 错误: 不清理资源
nodes = AgentNodes(config)
result = await nodes.process_input(state)
# 可能导致 HTTP 客户端泄漏
```

### 模式 5: 提取重复代码 (Extract Method)

```python
# ❌ 重复代码
async def method_a(self):
    if self._http_client is None:
        async with self._client_lock:
            if self._http_client is None:
                self._http_client = httpx.AsyncClient(timeout=30.0)
    # 使用 self._http_client

async def method_b(self):
    if self._http_client is None:
        async with self._client_lock:
            if self._http_client is None:
                self._http_client = httpx.AsyncClient(timeout=30.0)
    # 使用 self._http_client

# ✅ 提取方法
async def _ensure_http_client(self):
    """确保 HTTP 客户端已初始化 (懒加载)"""
    if self._http_client is None:
        async with self._client_lock:
            if self._http_client is None:
                self._http_client = httpx.AsyncClient(timeout=30.0)

async def method_a(self):
    await self._ensure_http_client()
    # 使用 self._http_client

async def method_b(self):
    await self._ensure_http_client()
    # 使用 self._http_client
```

---

## ⚠️ 第七步: 特殊注意事项 (AI 必知陷阱)

### 陷阱 1: GPT-5 系列 temperature 参数

```python
# ❌ 错误: 直接传递 temperature 给 GPT-5
params = {
    "model": "gpt-5-mini",
    "temperature": 0.7,  # GPT-5 不支持!
    "messages": messages
}

# ✅ 正确: 使用兼容层
from src.utils.llm_compat import prepare_llm_params

params = prepare_llm_params(
    model="gpt-5-mini",
    messages=messages,
    temperature=0.7  # 自动移除
)
```

**原理**: `llm_compat.py` 检测 GPT-5 系列,自动移除 temperature 参数。

### 陷阱 2: 会话数据在重启后丢失

```python
# ⚠️ 当前限制: 内存存储
# 问题: 服务重启后所有会话丢失

# 临时解决方案: 避免频繁重启
# 长期计划: Phase 3 迁移到 Redis
```

**提示 AI**: 不要建议用户依赖持久化,明确告知数据会丢失。

### 陷阱 3: HTTP 客户端必须清理

```python
# ❌ 错误: 忘记清理
class AgentNodes:
    def __init__(self, config):
        self._http_client = httpx.AsyncClient()
    
    # 没有 cleanup 方法 → 泄漏!

# ✅ 正确: 实现清理
class AgentNodes:
    def __init__(self, config):
        self._http_client = None
        self._client_lock = asyncio.Lock()
    
    async def cleanup(self):
        """清理资源"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
```

### 陷阱 4: 历史消息数量限制

```python
# ⚠️ 注意: 有最大历史消息限制
MAX_HISTORY_MESSAGES = 10

# 提示 AI: 不要建议无限存储历史
# 当前设计: 只保留最近 10 条消息
```

### 陷阱 5: MCP 工具尚未实现

```python
# ⚠️ 当前状态: handle_tools 节点为占位符
async def handle_tools(self, state: AgentState) -> AgentState:
    """
    工具调用节点 (Phase 2E - 未实现)
    """
    # 当前直接跳过
    state["next_action"] = "format_response"
    return state

# 提示 AI: 不要建议使用工具功能,明确告知未实现
```

---

## 🧪 第八步: 测试指导

### 运行测试

```bash
# 所有测试
pytest

# 特定模块
pytest tests/unit/test_agent.py

# 带覆盖率
pytest --cov=src tests/

# 代码质量检查
ruff check src/
```

### 编写测试 (AI 应遵循的模式)

```python
# tests/unit/test_my_feature.py
import pytest
from src.agent.nodes import AgentNodes
from src.agent.state import create_initial_state

@pytest.fixture
async def agent_nodes():
    """创建 AgentNodes 实例"""
    config = VoiceAgentConfig()
    nodes = AgentNodes(config)
    yield nodes
    await nodes.cleanup()  # 重要: 清理资源

@pytest.mark.asyncio
async def test_my_feature(agent_nodes):
    """
    测试功能描述
    
    测试步骤:
    1. 准备测试数据
    2. 调用功能
    3. 验证结果
    """
    # Arrange
    state = create_initial_state(
        session_id="test",
        user_input="测试输入"
    )
    
    # Act
    result = await agent_nodes.my_method(state)
    
    # Assert
    assert result["expected_field"] == "expected_value"
    assert result["next_action"] == "next_node"
```

---

## 📚 第九步: 文档查找指南

### 需要某个信息时,去哪里找?

| 需求 | 文档位置 | 章节/关键词 |
|------|---------|------------|
| **项目总览** | `PROJECT.md` | "Copilot Context Refresh" |
| **当前进度** | `specs/001-.../progress.md` | 进度概览、Phase 状态 |
| **最近变更** | `CHANGELOG.md` | v0.2.0 章节 |
| **快速上手** | `DEVELOPMENT.md` | "10 分钟快速设置" |
| **API 使用** | `specs/001-.../quickstart.md` | "Basic Usage" |
| **开发报告** | `docs/achievements/INDEX.md` | 按 Phase 分类 |
| **代码约定** | `.github/copilot-instructions.md` | "Code Conventions" |
| **架构设计** | `PROJECT.md` | "当前架构" 章节 |
| **技术决策** | `PROJECT.md` | "关键技术决策" |
| **常见问题** | `PROJECT.md` 或 `DEVELOPMENT.md` | FAQ 章节 |
| **TTS 使用** | `docs/achievements/phase2/TTS_QUICKSTART.md` | 完整指南 |
| **对话 API** | `docs/achievements/phase2/CONVERSATION_API_GUIDE.md` | API 端点 |
| **优化报告** | `docs/achievements/optimizations/CODE_OPTIMIZATION_COMPLETE.md` | 优化内容 |
| **LLM 修复** | `docs/achievements/reports/LLM_CALL_FIX.md` | GPT-5 处理 |

### 快速搜索技巧

```bash
# 在项目中搜索关键词
rg "关键词" --type py  # 只搜索 Python 文件
rg "关键词" docs/      # 只搜索文档

# 查找文件
fd "文件名"

# 查看 Git 历史
git log --oneline --grep="关键词"
```

---

## 🎓 第十步: AI 自检清单

在提供代码建议前,AI 应确认:

### 基础理解
- [ ] 我是否理解当前项目处于 Phase 2 Complete (80%)?
- [ ] 我是否知道 Phase 2E (MCP 工具) 尚未实现?
- [ ] 我是否理解会话存储是内存,重启丢失?

### 代码规范
- [ ] 我的文档字符串是否使用中文?
- [ ] 我的错误消息是否使用中文?
- [ ] 我的日志消息是否使用中文?
- [ ] 我的变量/函数名是否使用英文?

### 特殊处理
- [ ] 如果涉及 LLM 调用,我是否使用了 `llm_compat.py`?
- [ ] 如果涉及 HTTP 客户端,我是否使用了 `_ensure_http_client()`?
- [ ] 如果创建资源,我是否实现了 `cleanup()` 方法?
- [ ] 如果涉及 GPT-5,我是否避免传递 temperature 参数?

### 架构一致性
- [ ] 我的代码是否符合分层架构 (API → Service → Agent)?
- [ ] 我的 LangGraph 节点是否返回 `AgentState`?
- [ ] 我的节点是否设置了 `next_action` 字段?
- [ ] 我的 API 端点是否使用了 Pydantic 模型?

### 最佳实践
- [ ] 我是否提取了重复代码 (Extract Method)?
- [ ] 我是否使用了 async/await (异步编程)?
- [ ] 我是否添加了适当的错误处理?
- [ ] 我是否添加了必要的日志记录?

---

## 🚨 常见错误示例 (AI 应避免)

### 错误 1: 建议使用未实现的功能

```python
# ❌ AI 不应建议 (MCP 工具未实现)
"你可以使用 handle_tools 节点来调用搜索工具..."

# ✅ AI 应该说
"注意: MCP 工具功能尚未实现 (Phase 2E 规划中)。
当前 handle_tools 节点为占位符,直接跳过到 format_response。
如需工具功能,请等待 Phase 2E 实施。"
```

### 错误 2: 建议持久化会话

```python
# ❌ AI 不应建议
"你可以在数据库中持久化会话数据..."

# ✅ AI 应该说
"注意: 当前使用内存存储 (LangGraph MemorySaver),
服务重启后会话数据会丢失。这是 MVP 设计决策,
持久化存储 (Redis) 计划在 Phase 3 实施。"
```

### 错误 3: 忽略 GPT-5 兼容性

```python
# ❌ AI 不应建议
params = {
    "model": "gpt-5-mini",
    "temperature": 0.7,
    "messages": messages
}

# ✅ AI 应该建议
from src.utils.llm_compat import prepare_llm_params

params = prepare_llm_params(
    model="gpt-5-mini",
    messages=messages,
    temperature=0.7  # 自动处理 GPT-5 兼容性
)
```

### 错误 4: 英文文档字符串

```python
# ❌ AI 不应生成
async def process_input(self, state: AgentState) -> AgentState:
    """
    Process user input and update conversation history.
    """
    pass

# ✅ AI 应该生成
async def process_input(self, state: AgentState) -> AgentState:
    """
    处理用户输入并更新对话历史
    
    功能:
    1. 验证用户输入
    2. 更新会话上下文
    3. 设置下一个处理节点
    """
    pass
```

---

## 🎯 总结: AI 快速参考卡

### 30 秒速查

```
项目: Voice-Based AI Agent (语音 AI 对话系统)
状态: Phase 2 Complete (80%)
版本: v0.2.0-beta

核心文件:
- src/agent/nodes.py (768行) ← 最重要
- src/agent/graph.py (375行)
- src/api/conversation_routes.py
- src/utils/llm_compat.py

关键约定:
✅ 文档字符串: 中文
✅ 错误/日志: 中文
✅ 变量/函数: 英文
✅ GPT-5: 不传 temperature
✅ 资源: 必须 cleanup()

未实现:
⏳ MCP 工具 (Phase 2E)
⏳ Redis 存储 (Phase 3)
⏳ Docker 容器 (Phase 3)

必读文档:
1. PROJECT.md (Copilot Context Refresh)
2. progress.md (当前进度)
3. copilot-instructions.md (代码约定)
```

---

## 📞 需要更多帮助?

- **项目文档**: 查看 `docs/` 目录
- **API 文档**: 启动服务后访问 http://localhost:8000/docs
- **开发报告**: `docs/achievements/INDEX.md`
- **变更历史**: `CHANGELOG.md`

---

**祝 AI Assistant 使用愉快!** 🎉

*本指南由 Ivan_HappyWoods 团队维护*  
*最后更新: 2025-10-15*
