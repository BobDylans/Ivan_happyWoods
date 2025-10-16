# Ivan_HappyWoods - Voice-Based AI Agent Interaction System

> **Project Status**: Phase 3A In Progress (数据库持久化 60% 完成 🚧)  
> **Last Updated**: 2025-10-16  
> **Version**: 0.3.0-alpha
>
> 📖 **新手？** 先阅读 [QUICK_START.md](QUICK_START.md) - 15分钟快速上手指南

---

# Copilot Context Refresh

**This file describes the full architecture of Ivan_HappyWoods.**

本文档为 AI Assistant (GitHub Copilot, Cursor, etc.) 提供完整的项目上下文,确保在新环境中能够快速理解项目架构、当前状态和开发规范。

---

## 📋 目录

- [项目概述](#项目概述)
- [当前架构](#当前架构)
- [技术栈](#技术栈)
- [代码组织](#代码组织)
- [环境配置](#环境配置)
- [已完成功能](#已完成功能)
- [进行中功能](#进行中功能)
- [关键技术决策](#关键技术决策)
- [开发工作流](#开发工作流)
- [常见问题](#常见问题)
- [快速导航](#快速导航)

---

## 项目概述

### 🎯 核心目标

Ivan_HappyWoods 是一个**基于语音的 AI 代理交互系统**,旨在提供:
- 🎤 **自然语音交互**: 支持语音输入/输出的对话体验
- 🤖 **智能对话代理**: 基于 LangGraph 的多步骤推理流程
- 🔧 **工具集成能力**: 通过 MCP 协议集成外部工具
- 📡 **实时流式响应**: SSE 和 WebSocket 双模式流式传输
- 🌐 **多模型支持**: 灵活的 LLM 模型选择策略

### 🎨 核心价值主张

1. **Voice-First Design**: 语音作为主要交互方式,文本作为 fallback
2. **Extensible Architecture**: 模块化设计,易于扩展新功能
3. **Production-Ready**: 面向生产环境的架构设计
4. **Developer-Friendly**: 完善的文档和开发工具支持

### 📊 当前状态

```
Phase 1 (Core Foundation)        ████████████████████ 100% ✅
Phase 2A (Voice Integration)     ████████████████████ 100% ✅  
Phase 2B (Streaming TTS)         ████████████████████ 100% ✅
Phase 2C (Conversation API)      ████████████████████ 100% ✅
Phase 2D (Code Optimization)     ████████████████████ 100% ✅
Phase 2E (MCP Voice Tools)       ████████████████████ 100% ✅
Phase 3A (PostgreSQL Database)   ████████████░░░░░░░░  60% 🚧
Phase 3B (RAG Knowledge Base)    ░░░░░░░░░░░░░░░░░░░░   0% 📋
Phase 3C (n8n Integration)       ░░░░░░░░░░░░░░░░░░░░   0% 📋
```

**Phase 3A Progress**:
- ✅ Docker Compose + Database Schema
- ✅ ORM Models + Repositories  
- ✅ LangGraph Checkpointer
- ⏳ API Integration
- ⏳ Admin Endpoints
- ⏳ Testing

详见 [database-setup-guide.md](docs/database-setup-guide.md)

---

## 当前架构

### 🏗️ 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Layer                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Web Client │  │ Voice Device│  │   API Test  │            │
│  │   (Future)  │  │   (Future)  │  │    Tools    │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          │ HTTP/WS         │ WebSocket       │ REST API
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Gateway                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Routes Layer                                            │  │
│  │  • /api/conversation/* - 对话管理                        │  │
│  │  • /api/voice/*        - 语音处理                        │  │
│  │  • /api/stream/*       - WebSocket 流式                  │  │
│  │  • /health, /metrics   - 监控端点                        │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐  │
│  │  Middleware Layer                                        │  │
│  │  • CORS              - 跨域支持                          │  │
│  │  • Authentication    - API Key 验证                      │  │
│  │  • Logging           - 请求/响应日志                     │  │
│  │  • Error Handling    - 统一错误处理                      │  │
│  └────────────────────┬─────────────────────────────────────┘  │
└─────────────────────────┼─────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   LangGraph  │  │ Conversation │  │    Voice     │         │
│  │     Agent    │  │   Service    │  │   Service    │         │
│  │              │  │              │  │              │         │
│  │  • Workflow  │  │  • Sessions  │  │  • STT (科大) │         │
│  │  • Nodes     │  │  • History   │  │  • TTS (科大) │         │
│  │  • State     │  │  • Context   │  │  • Streaming │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          │                                   │
          ▼                                   ▼
┌─────────────────────┐         ┌─────────────────────────┐
│   External Services │         │   MCP Tools (Future)    │
│                     │         │                         │
│  • OpenAI API       │         │  • Search Tool          │
│  • iFlytek STT/TTS  │         │  • Calculator           │
│  • (Custom Proxy)   │         │  • Code Executor        │
│                     │         │  • Image Generator      │
└─────────────────────┘         └─────────────────────────┘
```

### 🔄 对话流程

```
用户输入 (文本/语音)
    │
    ▼
┌───────────────────────┐
│  1. Input Processing  │  语音 → 文本转换 (STT)
└──────────┬────────────┘  文本清洗和验证
           │
           ▼
┌───────────────────────┐
│  2. Intent Analysis   │  意图识别
└──────────┬────────────┘  上下文提取
           │
           ▼
┌───────────────────────┐
│  3. LLM Reasoning     │  调用 LLM API
└──────────┬────────────┘  生成响应/工具调用
           │
           ▼
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│ 4a. Text│ │ 4b. Tool│  (Future) 工具执行
│ Response│ │ Calling │
└────┬────┘ └────┬────┘
     │           │
     │      ┌────▼────┐
     │      │ Re-query│
     │      │   LLM   │
     │      └────┬────┘
     └───────────┘
           │
           ▼
┌───────────────────────┐
│  5. Response Format   │  响应格式化
└──────────┬────────────┘  历史记录更新
           │
           ▼
┌───────────────────────┐
│  6. Output Generation │  文本 → 语音转换 (TTS)
└──────────┬────────────┘  流式响应推送
           │
           ▼
    用户接收响应
```

---

## 技术栈

### 核心框架

| 技术 | 版本 | 用途 | 状态 |
|------|------|------|------|
| **Python** | 3.11+ | 主要开发语言 | ✅ |
| **FastAPI** | 0.100+ | Web 框架和 API 网关 | ✅ |
| **LangGraph** | Latest | 对话流程编排 | ✅ |
| **Pydantic** | v2 | 数据验证和配置管理 | ✅ |
| **httpx** | Latest | 异步 HTTP 客户端 | ✅ |
| **uvicorn** | Latest | ASGI 服务器 | ✅ |

### 外部服务

| 服务 | 提供商 | 用途 | 状态 |
|------|--------|------|------|
| **LLM API** | OpenAI-Compatible | 语言模型推理 | ✅ |
| **STT** | 科大讯飞 (iFlytek) | 语音识别 | ✅ |
| **TTS** | 科大讯飞 (iFlytek) | 语音合成 | ✅ |
| **MCP Tools** | Custom | 工具集成 | ⏳ |

### 开发工具

| 工具 | 用途 | 配置文件 |
|------|------|----------|
| **pytest** | 单元/集成测试 | `pytest.ini` |
| **ruff** | 代码检查 | `.ruff.toml` (planned) |
| **black** | 代码格式化 | `pyproject.toml` (planned) |
| **mypy** | 类型检查 | `mypy.ini` (planned) |

---

## 代码组织

### 📁 项目结构

```
Ivan_HappyWoods/
├── .github/
│   └── copilot-instructions.md    # Copilot 开发指引
│
├── specs/                          # 📐 功能规格文档
│   └── 001-voice-interaction-system/
│       ├── spec.md                 # 功能规格
│       ├── plan.md                 # 实施计划
│       ├── tasks.md                # 任务分解
│       ├── progress.md             # 进度跟踪 (NEW)
│       ├── architecture.md         # 架构文档 (NEW)
│       ├── quickstart.md           # 快速开始
│       ├── data-model.md           # 数据模型
│       └── research.md             # 技术调研
│
├── docs/                           # 📚 项目文档
│   ├── achievements/               # 开发成果
│   │   ├── INDEX.md               # 成果索引
│   │   ├── phase1/                # Phase 1 成果
│   │   ├── phase2/                # Phase 2 成果
│   │   ├── optimizations/         # 优化报告
│   │   └── reports/               # 修复报告
│   ├── api/                       # API 文档 (planned)
│   ├── architecture/              # 架构文档 (planned)
│   └── deployment/                # 部署指南 (planned)
│
├── src/                            # 💻 源代码
│   ├── agent/                      # 🤖 LangGraph 代理核心
│   │   ├── graph.py               # 工作流图定义
│   │   ├── nodes.py               # 节点实现
│   │   └── state.py               # 状态管理
│   │
│   ├── api/                        # 🌐 FastAPI 路由层
│   │   ├── main.py                # 应用入口
│   │   ├── conversation_routes.py # 对话端点
│   │   ├── voice_routes.py        # 语音端点
│   │   ├── models.py              # Pydantic 模型
│   │   ├── middleware.py          # 中间件
│   │   ├── auth.py                # 认证逻辑
│   │   ├── event_utils.py         # 事件工具
│   │   └── stream_manager.py      # 流管理器
│   │
│   ├── services/                   # 🔧 业务服务层
│   │   ├── conversation_service.py # 对话服务
│   │   └── voice/                 # 语音服务
│   │       ├── stt_service.py     # STT 实现
│   │       └── tts_service.py     # TTS 实现
│   │
│   ├── config/                     # ⚙️ 配置管理
│   │   ├── models.py              # 配置模型
│   │   └── settings.py            # 配置加载
│   │
│   ├── mcp/                        # 🔌 MCP 工具集成 (Future)
│   │   └── (planned)
│   │
│   └── utils/                      # 🛠️ 工具函数
│       └── llm_compat.py          # LLM 兼容层
│
├── tests/                          # 🧪 测试代码
│   ├── unit/                      # 单元测试
│   ├── integration/               # 集成测试
│   └── contract/                  # 契约测试 (planned)
│
├── config/                         # 📋 配置文件
│   ├── development.yaml           # 开发配置 (planned)
│   └── production.yaml            # 生产配置 (planned)
│
├── logs/                           # 📝 日志文件
├── test_audio/                     # 🎵 测试音频
│
├── .env                            # 🔐 环境变量 (不提交)
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python 依赖
├── pytest.ini                      # pytest 配置
├── start_server.py                 # 服务启动脚本
├── test_conversation.py            # 对话测试脚本
│
├── PROJECT.md                      # 本文件 - 项目总览
├── DEVELOPMENT.md                  # 开发者指南 (NEW)
├── CHANGELOG.md                    # 变更日志 (NEW)
└── README.md                       # 项目说明 (planned)
```

### 🎯 关键模块说明

#### 1. Agent 模块 (`src/agent/`)

**职责**: LangGraph 工作流核心

- **`graph.py`** (375 行)
  - `VoiceAgent` 类: 主对话代理
  - `_build_graph()`: 构建 LangGraph 工作流
  - `process_message()`: 同步消息处理
  - `process_message_stream()`: 流式消息处理
  - 路由函数: `_route_after_input/llm/tools()`

- **`nodes.py`** (768 行) - 核心节点实现
  - `AgentNodes` 类: 所有处理节点
  - `process_input()`: 输入处理节点
  - `call_llm()`: LLM 调用节点
  - `handle_tools()`: 工具执行节点 (Future)
  - `format_response()`: 响应格式化节点
  - `stream_llm_call()`: 流式 LLM 调用
  - 辅助方法:
    - `_ensure_http_client()`: HTTP 客户端懒加载
    - `_build_llm_url()`: URL 构建
    - `cleanup()`: 资源清理

- **`state.py`**
  - `AgentState`: 对话状态模型
  - `create_initial_state()`: 初始状态创建

#### 2. API 模块 (`src/api/`)

**职责**: FastAPI 路由和中间件

- **`main.py`**: FastAPI 应用入口
- **`conversation_routes.py`**: 对话 API 端点
  - `POST /api/conversation/send` - 发送消息
  - `GET /api/conversation/history` - 获取历史
  - `GET /api/conversation/stream` - SSE 流式
  - `WebSocket /api/conversation/ws` - WebSocket 流式

- **`voice_routes.py`**: 语音 API 端点
  - `POST /api/voice/stt` - 语音识别
  - `POST /api/voice/tts` - 语音合成
  - `WebSocket /api/voice/stream` - 流式语音

- **`middleware.py`**: 
  - CORS 中间件
  - 日志中间件
  - 错误处理中间件

- **`auth.py`**: API Key 认证

#### 3. Services 模块 (`src/services/`)

**职责**: 业务逻辑层

- **`conversation_service.py`**
  - 会话管理
  - 历史记录
  - 上下文维护

- **`voice/stt_service.py`** (科大讯飞 STT)
  - WebSocket 连接管理
  - 音频流处理
  - 实时转写

- **`voice/tts_service.py`** (科大讯飞 TTS)
  - 文本合成
  - 流式音频生成
  - 音频格式转换

#### 4. Config 模块 (`src/config/`)

**职责**: 配置管理

- **`models.py`**: Pydantic 配置模型
  - `VoiceAgentConfig`: 主配置
  - `LLMConfig`: LLM 配置
  - `SpeechConfig`: 语音配置
  - `APIConfig`: API 配置

- **`settings.py`**: 配置加载器
  - 环境变量加载
  - 配置验证
  - 配置合并

#### 5. Utils 模块 (`src/utils/`)

**职责**: 工具函数

- **`llm_compat.py`**: LLM 兼容层
  - `prepare_llm_params()`: 参数准备
  - 模型特性检测
  - GPT-5 系列特殊处理

---

## 环境配置

### 🔧 必需的环境变量

#### 1. LLM 配置 (必需)

```bash
# OpenAI-Compatible API
VOICE_AGENT_LLM__API_KEY=your_api_key_here
VOICE_AGENT_LLM__BASE_URL=https://api.openai-proxy.org/v1
VOICE_AGENT_LLM__PROVIDER=openai

# 模型选择
VOICE_AGENT_LLM__MODELS__DEFAULT=gpt-5-mini                 # 默认模型
VOICE_AGENT_LLM__MODELS__FAST=gpt-5-nano                    # 快速模型
VOICE_AGENT_LLM__MODELS__CREATIVE=gpt-5-chat-latest         # 创意模型

# LLM 参数
VOICE_AGENT_LLM__TIMEOUT=30
VOICE_AGENT_LLM__MAX_TOKENS=2048
VOICE_AGENT_LLM__TEMPERATURE=0.7
```

#### 2. 语音服务配置 (必需)

```bash
# 科大讯飞凭证 - 在 https://www.xfyun.cn/ 注册
IFLYTEK_APPID=your_appid
IFLYTEK_APIKEY=your_apikey
IFLYTEK_APISECRET=your_apisecret

# TTS 配置
IFLYTEK_TTS_APPID=your_appid
IFLYTEK_TTS_APIKEY=your_apikey
IFLYTEK_TTS_APISECRET=your_apisecret

# 语音偏好
VOICE_AGENT_SPEECH__TTS__PROVIDER=iflytek
VOICE_AGENT_SPEECH__TTS__VOICE=x4_lingxiaoxuan_oral
VOICE_AGENT_SPEECH__TTS__SPEED=50
VOICE_AGENT_SPEECH__TTS__FORMAT=mp3
```

#### 3. API 服务配置 (可选)

```bash
# 服务器配置
VOICE_AGENT_API__HOST=0.0.0.0
VOICE_AGENT_API__PORT=8000
VOICE_AGENT_API__RELOAD=true

# 认证
API_KEY_ENABLED=true
API_KEYS=dev-test-key-123

# CORS
VOICE_AGENT_SECURITY__CORS_ORIGINS=http://localhost:3000
```

#### 4. 会话管理 (可选)

```bash
# 内存存储 (开发)
VOICE_AGENT_SESSION__STORAGE_TYPE=memory
VOICE_AGENT_SESSION__TIMEOUT_MINUTES=30
VOICE_AGENT_SESSION__MAX_HISTORY=50

# Redis 存储 (生产 - Future)
# VOICE_AGENT_SESSION__STORAGE_TYPE=redis
# VOICE_AGENT_SESSION__REDIS_URL=redis://localhost:6379/0
```

### 📦 依赖安装

```bash
# 1. 克隆项目
git clone <repository-url>
cd Ivan_happyWoods

# 2. 创建虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件,填入实际凭证

# 5. 验证安装
python -c "import fastapi; import langgraph; print('OK')"
```

### 🚀 启动服务

```bash
# 开发模式 (自动重载)
python start_server.py

# 或使用 uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### ✅ 验证运行

```bash
# 1. 健康检查
curl http://localhost:8000/health

# 2. API 文档
# 浏览器访问: http://localhost:8000/docs

# 3. 测试对话
python test_conversation.py
```

---

## 已完成功能

### ✅ Phase 1: 核心基础 (2025-10-13 ~ 2025-10-14)

- [x] FastAPI 应用框架搭建
- [x] LangGraph 对话流程实现
- [x] OpenAI-Compatible LLM 集成
- [x] 会话管理 (内存存储)
- [x] 文本对话 MVP
- [x] SSE 流式响应 (POST/GET)
- [x] WebSocket 流式响应
- [x] 模型选择策略 (default/fast/creative)
- [x] 基础健康监控端点

**关键文件**: 
- `src/agent/graph.py`
- `src/agent/nodes.py`
- `src/api/main.py`
- `src/api/conversation_routes.py`

### ✅ Phase 2A: 语音集成 (2025-10-14)

- [x] 科大讯飞 STT 集成
- [x] 科大讯飞 TTS 集成
- [x] WebSocket 语音流处理
- [x] 音频格式转换
- [x] 实时语音转写

**关键文件**:
- `src/services/voice/stt_service.py`
- `src/services/voice/tts_service.py`
- `src/api/voice_routes.py`

**文档**:
- [TTS_QUICKSTART.md](./docs/achievements/phase2/TTS_QUICKSTART.md)
- [TTS_STREAM_GUIDE.md](./docs/achievements/phase2/TTS_STREAM_GUIDE.md)

### ✅ Phase 2B: 流式 TTS (2025-10-14)

- [x] TTS 流式音频生成
- [x] WebSocket 实时推送
- [x] 音频分片传输
- [x] 延迟优化 (<500ms 首字节)

**文档**:
- [TTS_FIXED_REPORT.md](./docs/achievements/phase2/TTS_FIXED_REPORT.md)

### ✅ Phase 2C: 对话 API 完善 (2025-10-14)

- [x] 对话历史查询 API
- [x] 会话清除 API
- [x] 流式对话历史持久化
- [x] 错误处理优化
- [x] API 认证 (API Key)

**文档**:
- [CONVERSATION_IMPLEMENTATION_REPORT.md](./docs/achievements/phase2/CONVERSATION_IMPLEMENTATION_REPORT.md)
- [CONVERSATION_API_GUIDE.md](./docs/achievements/phase2/CONVERSATION_API_GUIDE.md)
- [CONVERSATION_BUG_FIX.md](./docs/achievements/phase2/CONVERSATION_BUG_FIX.md)

### ✅ Phase 2D: 代码质量优化 (2025-10-15)

- [x] 代码去重 (Extract Method 模式)
  - HTTP 客户端初始化统一
  - URL 构建逻辑提取
  - 减少 ~35 行重复代码
  
- [x] 资源管理优化
  - Async Context Manager 支持
  - `cleanup()` 方法
  - 防止内存泄漏
  
- [x] 中文本地化
  - 22+ 个方法文档中文化
  - 用户错误消息中文化
  - 日志消息中文化
  
- [x] LLM 兼容性修复
  - GPT-5 系列 temperature 参数处理
  - 模型切换 (gpt-5-pro → gpt-5-mini)
  - 兼容层完善

**关键改进**:
- 代码质量: 4.2/5 → 4.8/5
- 重复代码: -50%
- 中文覆盖率: +217%

**文档**:
- [CODE_OPTIMIZATION_COMPLETE.md](./docs/achievements/optimizations/CODE_OPTIMIZATION_COMPLETE.md) ⭐
- [CODE_REVIEW_REPORT.md](./docs/achievements/optimizations/CODE_REVIEW_REPORT.md) ⭐

---

## 进行中功能

### ⏳ Phase 2E: MCP 工具集成 (规划中)

**计划功能**:
- [ ] MCP 协议实现
- [ ] 工具注册和发现机制
- [ ] 基础工具集:
  - [ ] Web 搜索工具
  - [ ] 计算器
  - [ ] 时间/日期工具
  - [ ] 代码执行器 (沙箱)
- [ ] 工具调用流程集成
- [ ] 错误处理和降级

**设计文档**: 见 `specs/001-voice-interaction-system/tasks.md` (Task 2.x)

---

## 关键技术决策

### 1. 为什么选择 LangGraph?

**决策**: 使用 LangGraph 而非简单的 LLM Chain

**原因**:
- ✅ **状态管理**: 内置会话状态管理
- ✅ **流程控制**: 清晰的节点和边定义
- ✅ **可扩展性**: 易于添加新节点(如工具调用)
- ✅ **调试能力**: 可视化工作流,方便调试
- ✅ **检查点**: 支持会话持久化

**权衡**: 增加了学习曲线,但长期收益明显

### 2. 为什么使用科大讯飞 STT/TTS?

**决策**: 选择科大讯飞而非 OpenAI Whisper/TTS

**原因**:
- ✅ **中文优化**: 对中文语音识别效果更好
- ✅ **流式支持**: 原生 WebSocket 流式接口
- ✅ **延迟低**: <500ms 首字节延迟
- ✅ **成本**: 相对 OpenAI 更经济
- ✅ **本地化**: 国内访问稳定

**权衡**: API 文档相对较少,需要更多集成工作

### 3. 为什么采用内存会话存储?

**决策**: Phase 1-2 使用 LangGraph MemorySaver (内存)

**原因**:
- ✅ **简单**: 无需额外依赖和配置
- ✅ **快速**: 开发迭代速度快
- ✅ **适合 MVP**: 验证核心功能

**限制**:
- ⚠️ 服务重启丢失数据
- ⚠️ 无法横向扩展
- ⚠️ 仅适合开发/测试

**未来计划**: Phase 3 迁移到 Redis

### 4. 为什么代码全中文化?

**决策**: Phase 2D 将注释、错误消息全部中文化

**原因**:
- ✅ **用户体验**: 中文用户更友好
- ✅ **开发效率**: 团队主要使用中文
- ✅ **维护性**: 降低理解成本

**实施**:
- 文档字符串: 中文
- 用户错误消息: 中文
- 日志消息: 中文
- 变量/函数名: 保持英文 (代码规范)

### 5. 为什么提取辅助方法?

**决策**: Extract Method 重构模式

**原因**:
- ✅ **DRY 原则**: 消除重复代码
- ✅ **可测试性**: 独立方法易于测试
- ✅ **可维护性**: 单一职责原则

**示例**:
```python
# Before: 重复 50 行
if self._http_client is None:
    async with self._client_lock:
        # ... 25 行初始化代码

# After: 单一方法
await self._ensure_http_client()  # 复用
```

---

## 开发工作流

### 🔄 标准开发流程

```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 更新依赖 (如需要)
pip install -r requirements.txt

# 3. 修改代码
# ... 编码 ...

# 4. 运行测试
pytest tests/

# 5. 代码检查
ruff check src/

# 6. 本地验证
python start_server.py
python test_conversation.py

# 7. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 8. 合并到主分支
git push origin feature/new-feature
```

### 🧪 测试策略

```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 测试覆盖率
pytest --cov=src tests/

# 特定模块测试
pytest tests/unit/test_agent.py -v

# 跳过慢测试
pytest -m "not slow"
```

### 📝 提交规范

遵循 Conventional Commits:

```
feat: 新功能
fix: Bug 修复
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试相关
chore: 构建/工具
```

示例:
```bash
git commit -m "feat(agent): 添加工具调用支持"
git commit -m "fix(tts): 修复流式音频断流问题"
git commit -m "docs: 更新 API 使用指南"
```

---

## 常见问题

### Q1: 如何添加新的 LangGraph 节点?

**步骤**:
1. 在 `src/agent/nodes.py` 的 `AgentNodes` 类中添加新方法
2. 方法签名: `async def my_node(self, state: AgentState) -> AgentState`
3. 在 `src/agent/graph.py` 的 `_build_graph()` 中注册: `workflow.add_node("my_node", self.nodes.my_node)`
4. 添加路由逻辑
5. 更新 `state.py` (如需新状态字段)

**示例**:
```python
# nodes.py
async def my_tool_node(self, state: AgentState) -> AgentState:
    """执行外部工具调用"""
    tool_name = state.get("tool_to_call")
    result = await self._execute_tool(tool_name)
    state["tool_result"] = result
    state["next_action"] = "format_response"
    return state

# graph.py
workflow.add_node("my_tool", self.nodes.my_tool_node)
workflow.add_edge("call_llm", "my_tool")
```

### Q2: 如何添加新的 API 端点?

**步骤**:
1. 在 `src/api/` 创建或编辑路由文件 (如 `my_routes.py`)
2. 定义 Pydantic 模型 (在 `models.py`)
3. 实现路由函数
4. 在 `src/api/main.py` 注册路由

**示例**:
```python
# models.py
class MyRequest(BaseModel):
    param: str

class MyResponse(BaseModel):
    result: str

# my_routes.py
from fastapi import APIRouter
router = APIRouter(prefix="/api/my")

@router.post("/endpoint", response_model=MyResponse)
async def my_endpoint(request: MyRequest):
    return MyResponse(result=f"Processed: {request.param}")

# main.py
from api.my_routes import router as my_router
app.include_router(my_router)
```

### Q3: 如何调试 LangGraph 工作流?

**方法**:
1. **日志调试**:
   ```python
   self.logger.debug(f"State after node: {state}")
   ```

2. **断点调试**:
   ```python
   import pdb; pdb.set_trace()  # 在节点中设置断点
   ```

3. **状态检查**:
   ```python
   # 在节点末尾打印状态
   print(f"Next action: {state.get('next_action')}")
   print(f"Messages: {len(state['messages'])}")
   ```

4. **使用 LangGraph 内置工具** (Future):
   ```python
   # 可视化工作流
   graph.get_graph().print_ascii()
   ```

### Q4: 如何切换 LLM 模型?

**方法 1: 环境变量**
```bash
# .env
VOICE_AGENT_LLM__MODELS__DEFAULT=gpt-4
```

**方法 2: API 请求**
```python
# 请求中指定模型
response = await client.post("/api/conversation/send", json={
    "session_id": "test",
    "message": "Hello",
    "model_config": {
        "model": "gpt-3.5-turbo"  # 覆盖默认模型
    }
})
```

**方法 3: 代码中修改**
```python
# src/config/models.py
class LLMModels(BaseModel):
    default: str = "gpt-4"  # 修改默认模型
```

### Q5: 如何添加新的语音提供商?

**步骤**:
1. 在 `src/services/voice/` 创建新文件 (如 `aws_tts_service.py`)
2. 实现统一接口:
   ```python
   class AWSTTSService:
       async def synthesize(self, text: str) -> bytes:
           pass
       async def synthesize_stream(self, text: str):
           async for chunk in ...:
               yield chunk
   ```
3. 在配置中添加提供商:
   ```python
   # config/models.py
   class TTSConfig(BaseModel):
       provider: Literal["iflytek", "aws", "azure"] = "iflytek"
   ```
4. 在路由中添加分发逻辑:
   ```python
   # voice_routes.py
   if config.tts.provider == "aws":
       service = AWSTTSService()
   ```

### Q6: 如何优化流式响应延迟?

**技巧**:
1. **减少首字节时间 (TTFB)**:
   - 使用流式 LLM 调用
   - 尽早发送 `start` 事件
   
2. **优化分片大小**:
   ```python
   # 调整 TTS 音频分片
   CHUNK_SIZE = 1024  # 更小 = 更低延迟,但更多开销
   ```

3. **并行处理**:
   ```python
   # 边生成边推送,不等待完整响应
   async for chunk in llm_stream:
       await websocket.send_json(chunk)  # 立即推送
   ```

4. **连接池复用**:
   ```python
   # 使用单例 HTTP 客户端
   self._http_client = httpx.AsyncClient(...)  # 复用连接
   ```

---

## 快速导航

### 📂 想要找到...

| 需求 | 文件位置 |
|------|---------|
| **添加新 API 端点** | `src/api/routes.py` 或创建新路由文件 |
| **修改对话流程** | `src/agent/graph.py` + `src/agent/nodes.py` |
| **配置 LLM 参数** | `src/config/models.py` 或 `.env` |
| **修改语音服务** | `src/services/voice/` |
| **查看 API 文档** | 启动服务后访问 `/docs` |
| **调试日志配置** | `.env` 中 `VOICE_AGENT_LOG_LEVEL` |
| **测试用例** | `tests/unit/` 或 `tests/integration/` |
| **功能规格** | `specs/001-voice-interaction-system/spec.md` |
| **开发任务** | `specs/001-voice-interaction-system/tasks.md` |
| **开发成果** | `docs/achievements/INDEX.md` |

### 🔍 常见操作速查

```bash
# 启动服务
python start_server.py

# 运行测试
pytest

# 查看 API 文档
# http://localhost:8000/docs

# 测试对话
python test_conversation.py

# 查看日志
tail -f logs/voice_agent.log

# 代码格式化
black src/ tests/

# 类型检查
mypy src/
```

### 📚 相关文档链接

- **功能规格**: [specs/001-voice-interaction-system/spec.md](./specs/001-voice-interaction-system/spec.md)
- **实施计划**: [specs/001-voice-interaction-system/plan.md](./specs/001-voice-interaction-system/plan.md)
- **任务列表**: [specs/001-voice-interaction-system/tasks.md](./specs/001-voice-interaction-system/tasks.md)
- **开发进度**: [specs/001-voice-interaction-system/progress.md](./specs/001-voice-interaction-system/progress.md) (NEW)
- **架构文档**: [specs/001-voice-interaction-system/architecture.md](./specs/001-voice-interaction-system/architecture.md) (NEW)
- **快速开始**: [specs/001-voice-interaction-system/quickstart.md](./specs/001-voice-interaction-system/quickstart.md)
- **开发指南**: [DEVELOPMENT.md](./DEVELOPMENT.md) (NEW)
- **成果索引**: [docs/achievements/INDEX.md](./docs/achievements/INDEX.md)
- **变更日志**: [CHANGELOG.md](./CHANGELOG.md) (NEW)

---

## 🎯 下一步计划

### 立即行动 (本周)
- [ ] 完成 MCP 工具框架实现
- [ ] 添加基础工具 (搜索、计算器)
- [ ] 完善单元测试覆盖率

### 短期目标 (本月)
- [ ] 工具调用集成到对话流程
- [ ] 添加更多 AI 工具 (图像生成、文档分析)
- [ ] 性能优化和压力测试

### 长期目标 (下季度)
- [ ] 生产环境部署 (Docker + K8s)
- [ ] Redis 会话存储
- [ ] 指标监控和告警
- [ ] 前端界面开发

---

## 📞 获取帮助

- **项目文档**: 查看 `docs/` 和 `specs/` 目录
- **API 文档**: 启动服务后访问 `/docs`
- **问题报告**: 创建 GitHub Issue
- **开发讨论**: 团队内部沟通渠道

---

*最后更新: 2025-10-15*  
*维护者: Ivan_HappyWoods Development Team*  
*License: [待定]*
