# 变更日志 (Changelog)

本文档记录 Ivan_HappyWoods 项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),  
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [未发布]

### 计划中
- RAG 知识库集成
- n8n 工作流集成
- Docker 容器化
- 监控和指标系统

---

## [0.3.0] - 2025-10-31

### ✨ 新增
- 💾 **PostgreSQL 数据库集成** (Phase 3A)
  - SQLAlchemy 2.0+ 异步 ORM 模型
  - PostgreSQLCheckpointer 实现 LangGraph 状态持久化
  - HybridSessionManager 混合存储架构 (内存 + 数据库)
  - 4 个数据库 Repository (Conversation, Session, Message, ToolCall)
  - Alembic 数据库迁移支持
  - 异步数据库连接池管理

- 🔧 **MCP 工具系统** (Phase 2E/2F)
  - 7 个 MCP 工具：calculator, time, weather, search, voice (3)
  - ToolRegistry 工具注册表
  - MCP API 端点 (`/api/tools/`)
  - OpenAI Function Calling 格式支持
  - 流式+工具调用集成

- 🧠 **AI 功能增强**
  - 上下文记忆系统 (20 条消息, 24h TTL)
  - Markdown 渲染 + 代码语法高亮
  - 智能提示词优化
  - Tavily 搜索集成
  - 完整聊天界面 Demo

- 🔍 **类型检查配置**
  - mypy 配置 (`mypy.ini`)
  - VS Code Pylance 优化 (`.vscode/settings.json`)
  - 修复 10 个基础类型错误

### 🔧 改进
- 合并 `models.py` 和 `models_v2.py` (-184 行重复代码, -54%)
- API 路由异步改造 (7 处关键 await)
- 数据库配置加载优化
- HTTP 客户端连接池复用
- 错误处理统一化

### 🐛 修复
- PostgreSQLCheckpointer `aget_tuple()` 未实现
- iFlytek API 配置加载问题
- 流式响应数据库持久化
- 工具调用结果序列化
- API Key 认证开发模式禁用

### 📊 性能提升
- 数据库查询异步化
- 内存缓存 LRU 优化
- 连接池配置优化

### 🔒 安全
- 数据库密码环境变量化
- SQL 注入防护 (ORM 参数化查询)
- 异步事务管理

### 📝 文档
- [phase2-database-integration-report.md](docs/phase2-database-integration-report.md) - 数据库集成报告
- [CODE_MERGE_REPORT_2025-10-31.md](docs/CODE_MERGE_REPORT_2025-10-31.md) - 代码合并报告
- [CODE_REVIEW_2025-10-31.md](docs/CODE_REVIEW_2025-10-31.md) - 代码审查报告
- [VSCODE_TYPE_CHECK_CONFIG.md](docs/VSCODE_TYPE_CHECK_CONFIG.md) - 类型检查配置
- 更新 PROJECT.md, CHANGELOG.md, progress.md

### 🧪 测试
- 数据库集成测试
- 工具调用测试
- 流式响应测试
- 异步操作测试

### ⚙️ 配置
- 数据库配置 (DATABASE_URL, pool size, etc.)
- Alembic 配置 (`alembic.ini`)
- mypy 配置 (`mypy.ini`)
- VS Code 配置 (`.vscode/settings.json`)

### 📦 依赖更新
- sqlalchemy>=2.0.23
- asyncpg>=0.29.0
- alembic>=1.13.0
- psycopg2-binary>=2.9.9
- mypy==1.18.2
- types-PyYAML

---

## [0.2.0] - 2025-10-15

### ✨ 新增
- 🎤 **语音服务集成**
  - 科大讯飞 STT (语音识别) 完整支持
  - 科大讯飞 TTS (语音合成) 完整支持
  - WebSocket 实时语音流处理
  - 流式 TTS 音频生成和推送

- 🌐 **对话 API 完善**
  - 对话历史查询接口 `GET /api/conversation/history/{session_id}`
  - 会话清除接口 `DELETE /api/conversation/clear/{session_id}`
  - 流式对话历史持久化
  - API Key 认证机制

- ⚡ **代码质量优化**
  - 代码去重 (减少 ~35 行重复代码)
  - 资源管理优化 (Async Context Manager)
  - 全面中文本地化 (文档、注释、错误消息)
  - LLM 兼容性层完善

- 📚 **文档体系建设**
  - PROJECT.md - 完整项目架构和上下文
  - DEVELOPMENT.md - 开发者指南
  - progress.md - 详细进度跟踪
  - achievements/ - 成果文档目录结构
  - INDEX.md - 成果索引

### 🔧 改进
- HTTP 客户端复用机制
- URL 构建逻辑统一
- 错误消息用户友好化
- 日志输出中文化
- 代码注释完善

### 🐛 修复
- GPT-5 系列 temperature 参数不兼容问题
- LLM URL 构建错误
- HTTP 请求头编码问题
- 流式响应历史记录丢失
- WebSocket 连接稳定性

### 📊 性能提升
- TTS 首字节延迟降至 <500ms
- LLM 响应延迟降至 <600ms
- WebSocket 连接时间 <100ms

### 🔒 安全
- 添加 API Key 认证
- 环境变量敏感信息保护
- CORS 策略配置

### 📝 文档
- 15+ 篇开发成果文档
- TTS 快速开始指南
- 对话 API 使用指南
- 代码优化完整报告
- 环境配置说明书

### 🧪 测试
- 基础单元测试套件
- 对话流程测试
- API 端点测试
- 用户验收测试通过

---

## [0.1.0] - 2025-10-14

### ✨ 新增
- 🤖 **LangGraph 对话流程**
  - StateGraph 工作流定义
  - 核心节点: process_input, call_llm, handle_tools, format_response
  - 条件路由逻辑
  - 会话状态管理 (MemorySaver)

- 🌐 **FastAPI 应用框架**
  - RESTful API 端点
  - SSE 流式响应 (POST/GET)
  - WebSocket 流式响应
  - CORS 中间件
  - 健康检查端点

- 🧠 **LLM 集成**
  - OpenAI-Compatible API 支持
  - 多模型选择 (default/fast/creative)
  - 异步 HTTP 调用
  - 错误处理和重试
  - 流式响应支持

- 💬 **对话功能**
  - 文本对话 MVP
  - 多轮对话上下文维护
  - 会话管理
  - 消息历史记录

- ⚙️ **配置系统**
  - Pydantic 配置模型
  - 环境变量支持
  - 分层配置管理
  - 配置验证

### 📝 文档
- 功能规格文档 (spec.md)
- 实施计划 (plan.md)
- 任务分解 (tasks.md)
- 快速开始指南 (quickstart.md)
- API 基础文档

### 🧪 测试
- 基础测试脚本 (test_conversation.py)
- 配置文件 (pytest.ini)

### 🏗️ 基础设施
- 项目结构搭建
- 依赖管理 (requirements.txt)
- 环境变量模板 (.env.example)
- Git 版本控制

---

## [0.0.1] - 2025-10-13

### 🎉 项目初始化
- 项目仓库创建
- 基础目录结构
- README 和 LICENSE
- 初始规划文档

---

## 版本说明

### [0.2.0] - Phase 2 Complete
**发布日期**: 2025-10-15  
**主要成就**: 
- ✅ 语音功能完整集成
- ✅ API 体系完善
- ✅ 代码质量大幅提升
- ✅ 文档体系建立

**统计数据**:
- 代码行数: ~5000 行
- 文档数量: 20+ 篇
- API 端点: 12+
- 代码质量: 4.8/5

### [0.1.0] - Phase 1 Complete
**发布日期**: 2025-10-14  
**主要成就**:
- ✅ 对话 MVP 完成
- ✅ LangGraph 工作流实现
- ✅ 流式响应支持

**统计数据**:
- 代码行数: ~3000 行
- API 端点: 5
- 基础功能完成度: 100%

---

## 里程碑时间线

```
2025-10-13  📍 M0: 项目启动
2025-10-14  📍 M1: MVP Demo (文本对话)
2025-10-14  📍 M2: Voice Ready (语音集成)
2025-10-15  📍 M3: Code Quality (优化完成)
2025-10-22  📍 M4: Tool Integration (计划)
2025-11-05  📍 M5: Production Ready (计划)
```

---

## 贡献者

感谢所有为项目做出贡献的开发者!

### Phase 2 (2025-10-14 ~ 2025-10-15)
- **语音集成**: Team
- **API 开发**: Team
- **代码优化**: Team
- **文档编写**: Team

### Phase 1 (2025-10-13 ~ 2025-10-14)
- **架构设计**: Team
- **核心开发**: Team
- **测试验证**: Team

---

## 技术债务追踪

### 已解决 ✅
- ✅ 代码重复 (Phase 2D 解决)
- ✅ 缺少资源清理 (Phase 2D 解决)
- ✅ 文档不全 (Phase 2D 解决)
- ✅ LLM 兼容性 (Phase 2D 解决)

### 待解决 ⏳
- ⏳ 内存会话存储限制 (Phase 3 - Redis)
- ⏳ 缺少 MCP 工具 (Phase 2E)
- ⏳ 测试覆盖率不足 (持续改进)
- ⏳ 性能基准测试 (Phase 3)

---

## 破坏性变更

### [0.2.0]
- 无破坏性变更 (向后兼容)

### [0.1.0]
- 初始版本,无破坏性变更

---

## 迁移指南

### 从 0.1.0 升级到 0.2.0

**环境变量更新**:
```bash
# 新增科大讯飞配置
IFLYTEK_APPID=your_appid
IFLYTEK_APIKEY=your_apikey
IFLYTEK_APISECRET=your_apisecret

# 新增 TTS 配置
VOICE_AGENT_SPEECH__TTS__PROVIDER=iflytek
VOICE_AGENT_SPEECH__TTS__VOICE=x4_lingxiaoxuan_oral

# 新增认证配置 (可选)
API_KEY_ENABLED=true
API_KEYS=your-api-key
```

**代码更新**:
- 无需修改现有代码
- 可选: 使用新的语音 API
- 可选: 启用 API Key 认证

**数据迁移**:
- 无需数据迁移 (内存存储)

---

## 已知问题

### [0.2.0]
- 会话数据在服务重启后丢失 (使用内存存储)
- MCP 工具尚未实现
- 测试覆盖率约 60% (目标 80%)

### 临时解决方案
- 使用持久化存储前避免频繁重启
- 工具功能将在 Phase 2E 提供
- 核心功能已有基础测试覆盖

---

## 路线图

### v0.3.0 (计划 2025-10-22)
- MCP 工具集成
- 搜索工具
- 计算器工具
- 工具调用流程

### v0.4.0 (计划 2025-11-05)
- Redis 会话存储
- Docker 容器化
- 监控系统
- CI/CD 流水线

### v1.0.0 (计划 2025-12-01)
- 生产环境就绪
- 完整测试覆盖
- 性能优化
- 文档完善

---

## 许可证

[待定]

---

## 联系方式

- **项目仓库**: [GitHub Repository]
- **问题报告**: [GitHub Issues]
- **文档**: [Project Documentation]

---

*本变更日志遵循 [Keep a Changelog](https://keepachangelog.com/) 规范*  
*最后更新: 2025-10-15*
