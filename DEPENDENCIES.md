# 📦 Ivan_HappyWoods 项目依赖清单

> **最后更新**: 2025-10-16  
> **Python 版本要求**: 3.11+

---

## 🎯 快速安装

```bash
pip install -r requirements.txt
```

---

## 📚 核心依赖分类

### 1. Web 框架（Core Framework）

| 包名 | 版本 | 用途 | 必需 |
|------|------|------|------|
| `fastapi` | 0.116.1 | Web 框架，提供 REST API | ✅ 必需 |
| `uvicorn[standard]` | 0.35.0 | ASGI 服务器（包含 WebSocket） | ✅ 必需 |
| `pydantic` | 2.11.7 | 数据验证和序列化 | ✅ 必需 |
| `pydantic-settings` | 2.11.0 | 配置管理 | ✅ 必需 |

**说明**: FastAPI 是项目的核心 Web 框架，提供高性能的异步 API 服务。

---

### 2. AI 和 Agent 框架（LangGraph & AI）

| 包名 | 版本 | 用途 | 必需 |
|------|------|------|------|
| `langgraph` | 0.6.7 | 状态图工作流框架 | ✅ 必需 |
| `langgraph-checkpoint` | 2.1.1 | LangGraph 检查点支持 | ✅ 必需 |
| `langchain` | 0.3.27 | LangChain 核心库 | ✅ 必需 |
| `langchain-core` | 0.3.76 | LangChain 核心组件 | ✅ 必需 |
| `langchain-openai` | 0.3.33 | OpenAI LLM 集成 | ✅ 必需 |
| `langchain-community` | 0.3.30 | 社区工具集成 | ✅ 必需 |

**说明**: LangGraph 用于构建智能对话代理的工作流，LangChain 提供 LLM 集成和工具调用能力。

---

### 3. 网络和通信（Networking）

| 包名 | 版本 | 用途 | 必需 |
|------|------|------|------|
| `httpx` | 0.28.1 | 异步 HTTP 客户端 | ✅ 必需 |
| `httpx-sse` | 0.4.1 | Server-Sent Events 支持 | ✅ 必需 |
| `websockets` | 15.0.1 | WebSocket 支持（语音实时通信） | ✅ 必需 |

**说明**: 用于外部 API 调用（如 OpenAI、科大讯飞）和流式响应。

---

### 4. 配置管理（Configuration）

| 包名 | 版本 | 用途 | 必需 |
|------|------|------|------|
| `python-dotenv` | 1.1.0 | .env 文件支持 | ✅ 必需 |
| `PyYAML` | 6.0.2 | YAML 配置文件解析 | ✅ 必需 |
| `typing-extensions` | 4.12.2 | 类型提示扩展 | ✅ 必需 |

**说明**: 支持多环境配置管理（development/testing/production）。

---

### 5. 数据库（Database - Phase 3A）

| 包名 | 版本 | 用途 | 必需 |
|------|------|------|------|
| `sqlalchemy` | ≥2.0.23 | ORM 框架 | ⚠️ Phase 3A |
| `asyncpg` | ≥0.29.0 | PostgreSQL 异步驱动 | ⚠️ Phase 3A |
| `alembic` | ≥1.13.0 | 数据库迁移工具 | ⚠️ Phase 3A |
| `psycopg2-binary` | ≥2.9.9 | PostgreSQL 同步驱动 | ⚠️ Phase 3A |

**说明**: Phase 3A 功能（对话历史持久化）需要。当前版本使用内存存储，可选安装。

---

### 6. 音频处理（Audio Processing）

| 包名 | 版本 | 用途 | 必需 |
|------|------|------|------|
| `pydub` | ≥0.25.1 | 音频格式转换 | ✅ 必需 |

**重要**: `pydub` 依赖 **FFmpeg**，需要单独安装：

- **Windows**: https://www.gyan.dev/ffmpeg/builds/
- **Linux**: `apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`

**说明**: 用于处理科大讯飞语音服务的音频格式转换。

---

### 7. 开发和测试（Development & Testing）

| 包名 | 版本 | 用途 | 必需 |
|------|------|------|------|
| `pytest` | ≥7.4.0, <8.0.0 | 测试框架 | 🔧 开发 |
| `pytest-asyncio` | ≥0.21.0, <0.22.0 | 异步测试支持 | 🔧 开发 |
| `pytest-mock` | ≥3.12.0, <4.0.0 | Mock 支持 | 🔧 开发 |
| `pytest-cov` | ≥4.1.0, <5.0.0 | 代码覆盖率 | 🔧 开发 |

**说明**: 仅开发环境需要，生产环境可不安装。

---

## 🔧 可选依赖（未包含在 requirements.txt）

### 代码质量工具

```bash
# 代码格式化
pip install black>=23.0.0

# 代码检查
pip install ruff>=0.1.0

# 类型检查
pip install mypy>=1.7.0
pip install types-PyYAML>=6.0.0
```

### 未来扩展（Phase 3B/3C）

```bash
# RAG 知识库（Phase 3B）
pip install qdrant-client>=1.7.0
pip install sentence-transformers>=2.3.0
pip install pypdf>=3.17.0
pip install python-docx>=1.1.0

# 高级音频处理（可选）
pip install librosa>=0.10.0
pip install soundfile>=0.12.0
pip install numpy>=1.24.0

# Session 存储（可选）
pip install redis>=5.0.0
pip install aiofiles>=23.0.0
```

---

## 🐳 Docker 服务依赖（Phase 3）

通过 `docker-compose.yml` 管理：

| 服务 | 镜像 | 端口 | 用途 | 状态 |
|------|------|------|------|------|
| PostgreSQL | `postgres:16-alpine` | 5432 | 对话历史存储 | Phase 3A |
| Qdrant | `qdrant/qdrant:latest` | 6333, 6334 | 向量数据库（RAG） | Phase 3B |
| n8n | `n8n:latest` | 5678 | 工作流自动化 | Phase 3C |

**启动命令**:
```bash
docker-compose up -d
```

---

## 📋 完整依赖列表（按字母排序）

```
alembic>=1.13.0
asyncpg>=0.29.0
fastapi==0.116.1
httpx==0.28.1
httpx-sse==0.4.1
langchain==0.3.27
langchain-community==0.3.30
langchain-core==0.3.76
langchain-openai==0.3.33
langgraph==0.6.7
langgraph-checkpoint==2.1.1
psycopg2-binary>=2.9.9
pydantic==2.11.7
pydantic-settings==2.11.0
pydub>=0.25.1
pytest>=7.4.0,<8.0.0
pytest-asyncio>=0.21.0,<0.22.0
pytest-cov>=4.1.0,<5.0.0
pytest-mock>=3.12.0,<4.0.0
python-dotenv==1.1.0
PyYAML==6.0.2
sqlalchemy>=2.0.23
typing-extensions==4.12.2
uvicorn[standard]==0.35.0
websockets==15.0.1
```

---

## 🔍 依赖关系图

```
Ivan_HappyWoods
│
├─ FastAPI (Web 框架)
│  ├─ uvicorn (ASGI 服务器)
│  ├─ pydantic (数据验证)
│  └─ websockets (实时通信)
│
├─ LangGraph (Agent 框架)
│  ├─ langchain (LLM 集成)
│  ├─ langchain-openai (OpenAI)
│  └─ langgraph-checkpoint (状态持久化)
│
├─ 配置管理
│  ├─ pydantic-settings
│  ├─ python-dotenv
│  └─ PyYAML
│
├─ 网络通信
│  ├─ httpx (HTTP 客户端)
│  └─ httpx-sse (流式响应)
│
├─ 音频处理
│  └─ pydub + FFmpeg
│
├─ 数据库（Phase 3A）
│  ├─ sqlalchemy (ORM)
│  ├─ asyncpg (PostgreSQL)
│  └─ alembic (迁移)
│
└─ 测试
   ├─ pytest
   ├─ pytest-asyncio
   ├─ pytest-mock
   └─ pytest-cov
```

---

## 💡 安装建议

### 最小安装（仅运行）

```bash
# 核心依赖（不包含数据库和测试）
pip install fastapi uvicorn[standard] pydantic pydantic-settings \
    langgraph langgraph-checkpoint langchain langchain-core \
    langchain-openai langchain-community httpx httpx-sse \
    websockets python-dotenv PyYAML typing-extensions pydub
```

### 完整安装（包含开发）

```bash
pip install -r requirements.txt
```

### 生产环境

```bash
# 不安装测试依赖
pip install -r requirements.txt --no-deps
pip install <列出除 pytest* 之外的所有包>
```

---

## 🔄 依赖更新

### 检查过期依赖

```bash
pip list --outdated
```

### 更新依赖

```bash
# 更新单个包
pip install --upgrade <package-name>

# 更新所有包（谨慎）
pip install --upgrade -r requirements.txt
```

### 锁定依赖版本

```bash
# 生成精确版本锁定文件
pip freeze > requirements.lock
```

---

## ⚠️ 已知问题和注意事项

### 1. FFmpeg 依赖

**问题**: `pydub` 需要 FFmpeg，但不会自动安装。

**解决**:
- Windows: 下载并添加到 PATH
- Linux: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

### 2. asyncpg 编译

**问题**: `asyncpg` 需要编译，Windows 可能遇到问题。

**解决**:
- 安装 Visual Studio Build Tools
- 或使用预编译的 wheel

### 3. LangGraph 版本兼容性

**注意**: LangGraph 0.6.7 与 LangChain 0.3.x 系列兼容，升级时需同步更新。

### 4. Python 版本

**要求**: Python 3.11+

**原因**: 使用了 `typing` 的新特性和 `asyncio` 的改进。

---

## 📚 相关文档

- [QUICK_START.md](QUICK_START.md) - 快速上手指南
- [DEVELOPMENT.md](DEVELOPMENT.md) - 开发环境配置
- [requirements.txt](requirements.txt) - 依赖文件
- [docker-compose.yml](docker-compose.yml) - Docker 服务配置

---

## 🆘 故障排除

### 安装失败

```bash
# 清理缓存重试
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

### 依赖冲突

```bash
# 创建新的虚拟环境
python -m venv venv_new
source venv_new/bin/activate  # Windows: venv_new\Scripts\activate
pip install -r requirements.txt
```

### 版本不兼容

```bash
# 检查 Python 版本
python --version  # 应该 >= 3.11

# 检查 pip 版本
pip --version
pip install --upgrade pip
```

---

**维护者**: 项目团队  
**更新频率**: 每个 Phase 完成后更新  
**反馈**: 通过 Issues 或 PR

