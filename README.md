# 🎤 Ivan_HappyWoods

> **企业级语音 AI 代理系统** - 开箱即用、可扩展、生产就绪

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.6+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 快速开始

**5 分钟启动**:

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 API Keys

# 3. 启动服务
python start_server.py

# 4. 访问 API 文档
# http://localhost:8000/docs
```

**完整上手指南**: 📖 [QUICK_START.md](QUICK_START.md) ⭐

---

## ✨ 核心特性

| 特性 | 描述 | 状态 |
|------|------|------|
| 🎤 **语音对话** | 科大讯飞 STT/TTS，支持流式响应 | ✅ 完成 |
| 🤖 **智能代理** | LangGraph 工作流，多步骤推理 | ✅ 完成 |
| 🔧 **工具调用** | MCP 协议，7+ 内置工具 | ✅ 完成 |
| 💾 **数据持久化** | PostgreSQL，对话历史 | 🚧 60% |
| 📚 **RAG 知识库** | Qdrant 向量检索 | 📋 计划中 |
| 🔗 **工作流集成** | n8n Webhook 动态工具 | 📋 计划中 |

---

## 📚 文档导航

### 🎯 新手必读

- **[QUICK_START.md](QUICK_START.md)** ⭐ - 15分钟快速上手
- **[PROJECT.md](PROJECT.md)** - 完整架构和技术栈
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - 开发环境配置

### 📖 专题指南

- [database-setup-guide.md](docs/database-setup-guide.md) - PostgreSQL 配置
- [TTS_QUICKSTART.md](docs/achievements/phase2/TTS_QUICKSTART.md) - 语音功能测试
- [CONVERSATION_API_GUIDE.md](docs/achievements/phase2/CONVERSATION_API_GUIDE.md) - 对话 API
- [OPTIMIZATION_QUICK_REFERENCE.md](OPTIMIZATION_QUICK_REFERENCE.md) - 性能优化

### 🔧 开发参考

- [GIT_GUIDE.md](GIT_GUIDE.md) - Git 工作流规范
- [CHANGELOG.md](CHANGELOG.md) - 版本变更历史
- `docs/achievements/` - 各阶段实施报告

---

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────┐
│            FastAPI Gateway                  │
│  /api/conversation  /api/voice  /api/tools │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌──────────┐
│LangGraph│         │  Voice   │
│ Agent   │◄────────┤ Services │
│         │         │ STT/TTS  │
└────┬────┘         └──────────┘
     │
     ▼
┌──────────────────────────┐
│   MCP Tools (7+)         │
│ calculator | time | ... │
│ voice_synthesis | ...    │
└──────────────────────────┘
```

**详细架构**: 查看 [PROJECT.md § 当前架构](PROJECT.md#当前架构)

---

## 🛠️ 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **Web 框架** | FastAPI + Uvicorn | REST API + WebSocket |
| **AI 框架** | LangGraph + LangChain | Agent 工作流 |
| **LLM** | OpenAI API | 对话生成 |
| **语音** | 科大讯飞 | STT/TTS |
| **数据库** | PostgreSQL + SQLAlchemy | 对话持久化 (Phase 3A) |
| **向量库** | Qdrant | RAG 知识检索 (Phase 3B) |
| **工作流** | n8n | 动态工具集成 (Phase 3C) |

---

## 📦 项目结构

```
Ivan_happyWoods/
├── src/                    # 源代码
│   ├── agent/              # LangGraph Agent
│   ├── api/                # FastAPI 路由
│   ├── services/           # 业务逻辑
│   ├── mcp/                # MCP 工具
│   ├── database/           # 数据库层 (Phase 3A)
│   └── config/             # 配置管理
├── config/                 # YAML 配置
├── docs/                   # 文档
├── tests/                  # 测试
├── scripts/                # 工具脚本
├── start_server.py         # 启动入口
└── requirements.txt        # Python 依赖
```

---

## 📊 开发状态

### ✅ 已完成 (Phase 1-2E)

- FastAPI Web 框架
- LangGraph Agent 工作流
- 科大讯飞语音集成
- 对话管理 API
- MCP 工具系统（7个工具）
- 流式响应（SSE + WebSocket）
- 性能优化（50%启动时间↓，30%响应体↓）

### 🚧 进行中 (Phase 3A)

**PostgreSQL 数据库持久化** - 60% 完成

- ✅ Docker Compose 配置
- ✅ SQLAlchemy ORM 模型
- ✅ Repository 数据访问层
- ✅ LangGraph Checkpointer
- ⏳ API 集成
- ⏳ 管理端点
- ⏳ 端到端测试

**详细计划**: `postgresql-rag-n8n-integration.plan.md`

### 📋 计划中 (Phase 3B-C)

- **Phase 3B**: RAG 知识库（Qdrant + Embeddings）
- **Phase 3C**: n8n Webhook 工具动态注册

---

## 🧪 运行测试

```bash
# 运行所有测试
pytest

# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 带覆盖率
pytest --cov=src tests/
```

---

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交变更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

**详细规范**: [GIT_GUIDE.md](GIT_GUIDE.md)

---

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙋 常见问题

<details>
<summary><b>Q: 如何配置 API Keys？</b></summary>

复制 `.env.example` 到 `.env`，然后填写：
```bash
VOICE_AGENT_LLM__API_KEY=your-openai-key
VOICE_AGENT_SPEECH__TTS__APPID=your-iflytek-appid
VOICE_AGENT_SPEECH__TTS__API_KEY=your-iflytek-key
VOICE_AGENT_SPEECH__TTS__API_SECRET=your-iflytek-secret
```
</details>

<details>
<summary><b>Q: 如何启用数据库持久化？</b></summary>

Phase 3A 开发中。完成后：
```bash
# 1. 启动 PostgreSQL
docker-compose up -d postgres

# 2. 初始化数据库
python scripts/init_db.py

# 3. 在 .env 中启用
VOICE_AGENT_DATABASE__ENABLED=true
VOICE_AGENT_SESSION__STORAGE_TYPE=database
```

详见 [database-setup-guide.md](docs/database-setup-guide.md)
</details>

<details>
<summary><b>Q: 支持哪些 LLM 模型？</b></summary>

当前支持 OpenAI API 兼容的所有模型：
- GPT-4, GPT-4 Turbo
- GPT-3.5 Turbo
- GPT-4o, GPT-4o-mini
- 自定义代理（配置 `llm.base_url`）

配置方式见 [PROJECT.md § 技术栈](PROJECT.md#技术栈)
</details>

<details>
<summary><b>Q: 如何添加自定义工具？</b></summary>

参考 `src/mcp/voice_tools.py`:

1. 创建工具类继承 `Tool`
2. 实现 `name`, `description`, `parameters`, `execute()`
3. 在 `src/mcp/init_tools.py` 注册

详见 [QUICK_START.md § 开发工作流](QUICK_START.md#典型开发工作流)
</details>

---

## 📞 联系方式

- 项目地址: [GitHub Repository]
- 问题反馈: [Issues]
- 文档问题: 提交 PR 或创建 Issue

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**

---

*最后更新: 2025-10-16 | Version: 0.3.0-alpha*

