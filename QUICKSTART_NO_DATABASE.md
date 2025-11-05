# 快速开始 - 无需数据库运行模式

**适用场景**: 本地开发、快速测试、数据库未安装

---

## 🚀 5 分钟快速启动

### 步骤 1: 配置环境变量

**方式 A: 修改 .env 文件**

```bash
# 禁用数据库
VOICE_AGENT_DATABASE__ENABLED=false

# 配置 OpenAI（或其他 LLM）
VOICE_AGENT_LLM__API_KEY=your_api_key_here
VOICE_AGENT_LLM__BASE_URL=https://api.openai.com/v1
VOICE_AGENT_LLM__PROVIDER=openai
VOICE_AGENT_LLM__MODELS__DEFAULT=gpt-5-mini
```

**方式 B: 使用环境变量**

```bash
# Windows PowerShell
$env:VOICE_AGENT_DATABASE__ENABLED="false"
$env:VOICE_AGENT_LLM__API_KEY="your_api_key_here"

# Linux / macOS
export VOICE_AGENT_DATABASE__ENABLED=false
export VOICE_AGENT_LLM__API_KEY=your_api_key_here
```

---

### 步骤 2: 安装依赖

```bash
pip install -r requirements.txt
```

---

### 步骤 3: 启动服务

```bash
python start_server.py
```

**预期日志**:
```
📝 Database disabled in config, using MemorySaver
✅ HybridSessionManager initialized (memory-only mode)
✅ Voice agent initialized successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### 步骤 4: 测试

**测试 1: 健康检查**
```bash
curl http://localhost:8000/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "database": "disabled",
  "timestamp": "2025-11-05T12:00:00"
}
```

**测试 2: 发送对话**
```bash
curl -X POST http://localhost:8000/api/conversation/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_001",
    "message": "你好，请介绍一下你自己"
  }'
```

**测试 3: 使用测试脚本**
```bash
python test_llm_basic.py
```

---

## 📝 功能说明

### ✅ 可用功能（内存模式）

- ✅ **LLM 对话**: OpenAI / Ollama 调用正常
- ✅ **会话管理**: 单次运行期间保持会话上下文
- ✅ **工具调用**: MCP 工具正常工作
- ✅ **流式响应**: SSE 流式输出
- ✅ **语音合成**: TTS 功能
- ✅ **语音识别**: STT 功能

### ⚠️ 限制（内存模式）

- ⚠️ **重启丢失**: 服务重启后会话历史丢失
- ⚠️ **单机运行**: 不支持多实例部署
- ⚠️ **内存限制**: 每个会话最多保留 20 条消息

---

## 🔄 切换到数据库模式

### 步骤 1: 启动数据库

**使用 Docker**:
```bash
docker run -d \
  --name voice_agent_postgres \
  -e POSTGRES_DB=voice_agent \
  -e POSTGRES_USER=agent_user \
  -e POSTGRES_PASSWORD=changeme123 \
  -p 5432:5432 \
  postgres:15
```

### 步骤 2: 修改配置

**.env 文件**:
```bash
# 启用数据库
VOICE_AGENT_DATABASE__ENABLED=true
VOICE_AGENT_DATABASE__HOST=localhost
VOICE_AGENT_DATABASE__PORT=5432
VOICE_AGENT_DATABASE__DATABASE=voice_agent
VOICE_AGENT_DATABASE__USER=agent_user
VOICE_AGENT_DATABASE__PASSWORD=changeme123
```

### 步骤 3: 重启服务

```bash
python start_server.py
```

**预期日志**:
```
🔌 Attempting to connect to database...
✅ Database connection pool initialized: localhost:5432/voice_agent
✅ Database tables created/verified
✅ HybridSessionManager initialized (memory + database)
✅ Using PostgreSQL checkpointer for state persistence
```

---

## 🆚 模式对比

| 功能 | 内存模式 | 数据库模式 |
|------|----------|------------|
| **启动速度** | 快 (< 1s) | 中 (2-3s) |
| **会话持久化** | ❌ 重启丢失 | ✅ 永久保存 |
| **多实例部署** | ❌ 不支持 | ✅ 支持 |
| **历史记录查询** | ⚠️ 仅当前会话 | ✅ 完整历史 |
| **用户管理** | ❌ 不支持 | ✅ 支持 |
| **适用场景** | 开发/测试 | 生产环境 |

---

## ❓ 常见问题

### Q1: 为什么选择内存模式？

**A**: 
- 本地开发更快捷，无需安装和配置数据库
- 测试时不会污染数据库
- 临时测试功能时更方便

---

### Q2: 内存模式安全吗？

**A**: 
- ✅ LLM API 调用使用 HTTPS 加密
- ✅ 数据仅存储在内存中，重启自动清除
- ⚠️ 不适合存储敏感信息

---

### Q3: 如何知道当前运行在哪种模式？

**A**: 查看启动日志或访问健康检查端点：
```bash
curl http://localhost:8000/health
```

响应中的 `database` 字段会显示:
- `"disabled"` - 内存模式
- `"connected"` - 数据库模式

---

### Q4: 可以在运行时切换模式吗？

**A**: 不可以。需要:
1. 修改配置文件
2. 重启服务

---

### Q5: OpenAI LLM 调用会受影响吗？

**A**: ✅ 不会！LLM 功能完全独立于数据库。

---

## 📚 更多文档

- [完整重构说明](docs/CODE_REFACTORING_SUMMARY.md)
- [数据库集成计划](docs/guides/DATABASE_INTEGRATION_PLAN.md)
- [项目文档](PROJECT.md)

---

## ✅ 检查清单

开始使用前请确认:

- [ ] 已安装 Python 3.11+
- [ ] 已安装依赖: `pip install -r requirements.txt`
- [ ] 已配置 LLM API Key
- [ ] 已设置 `VOICE_AGENT_DATABASE__ENABLED=false`
- [ ] 服务正常启动
- [ ] 健康检查通过

---

**快速开始完成！** 🎉

现在可以使用所有 LLM 功能，无需担心数据库问题。

如需完整功能（会话持久化、用户管理），请参考数据库模式配置。

---

**更新日期**: 2025-11-05  
**版本**: v0.3.2

