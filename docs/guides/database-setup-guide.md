# Database Setup Guide

## PostgreSQL + Qdrant + n8n 集成设置指南

本指南介绍如何设置和配置 Voice Agent 系统的数据库环境。

---

## 📋 前置要求

- Docker 和 Docker Compose
- Python 3.11+
- 已安装项目依赖 (`pip install -r requirements.txt`)

---

## 🚀 快速开始

### 1. 配置环境变量

复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，设置数据库密码：
```bash
POSTGRES_PASSWORD=your_secure_password_here
VOICE_AGENT_DATABASE__ENABLED=true
VOICE_AGENT_DATABASE__PASSWORD=your_secure_password_here
VOICE_AGENT_SESSION__STORAGE_TYPE=database
```

### 2. 启动服务

启动 PostgreSQL、Qdrant 和 n8n：
```bash
docker-compose up -d
```

查看服务状态：
```bash
docker-compose ps
```

### 3. 初始化数据库

运行数据库初始化脚本：
```bash
python scripts/init_db.py
```

可选：加载测试数据
```bash
python scripts/init_db.py --test-data
```

### 4. 验证安装

检查 PostgreSQL：
```bash
docker-compose exec postgres psql -U agent_user -d voice_agent -c "\dt"
```

应该看到以下表：
- users
- sessions
- messages
- tool_calls

---

## 🔧 服务访问

### PostgreSQL
- **Host**: localhost
- **Port**: 5432
- **Database**: voice_agent
- **Username**: agent_user
- **Password**: 在 `.env` 中设置

### Qdrant (Phase 3B)
- **Dashboard**: http://localhost:6333/dashboard
- **API**: http://localhost:6333
- **gRPC**: localhost:6334

### n8n (Phase 3C)
- **UI**: http://localhost:5678
- **Username**: 在 `.env` 中的 `N8N_BASIC_AUTH_USER`
- **Password**: 在 `.env` 中的 `N8N_BASIC_AUTH_PASSWORD`

---

## 📊 数据库 Schema

### users 表
存储用户账户信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | VARCHAR(255) | 唯一用户名 |
| created_at | TIMESTAMP | 创建时间 |
| last_active | TIMESTAMP | 最后活动时间 |
| metadata | JSONB | 用户偏好和配置 |

### sessions 表
存储对话会话信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | VARCHAR(255) | 主键 |
| user_id | UUID | 外键 → users.id |
| created_at | TIMESTAMP | 创建时间 |
| last_activity | TIMESTAMP | 最后活动时间 |
| status | VARCHAR(20) | ACTIVE/PAUSED/TERMINATED |
| context_summary | TEXT | 上下文摘要 |
| metadata | JSONB | 会话元数据 |

### messages 表
存储对话消息。

| 字段 | 类型 | 说明 |
|------|------|------|
| message_id | UUID | 主键 |
| session_id | VARCHAR(255) | 外键 → sessions.session_id |
| timestamp | TIMESTAMP | 消息时间戳 |
| role | VARCHAR(20) | USER/ASSISTANT/SYSTEM/TOOL |
| content | TEXT | 消息内容 |
| metadata | JSONB | 消息元数据 |
| created_at | TIMESTAMP | 创建时间 |

### tool_calls 表
存储工具调用记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| call_id | UUID | 主键 |
| session_id | VARCHAR(255) | 外键 → sessions.session_id |
| message_id | UUID | 外键 → messages.message_id |
| tool_name | VARCHAR(255) | 工具名称 |
| parameters | JSONB | 输入参数 |
| result | JSONB | 执行结果 |
| execution_time_ms | INTEGER | 执行时间（毫秒） |
| timestamp | TIMESTAMP | 调用时间 |
| webhook_url | VARCHAR(500) | Webhook URL (Phase 3C) |
| response_status | INTEGER | HTTP 状态码 (Phase 3C) |
| response_time_ms | INTEGER | 响应时间 (Phase 3C) |

---

## 🔄 数据库迁移 (Alembic)

### 创建新迁移
当修改数据库模型后：
```bash
alembic revision --autogenerate -m "描述变更内容"
```

### 应用迁移
```bash
# 升级到最新版本
alembic upgrade head

# 升级到特定版本
alembic upgrade <revision_id>
```

### 回滚迁移
```bash
# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>
```

### 查看迁移历史
```bash
# 当前版本
alembic current

# 历史记录
alembic history

# 查看SQL（不执行）
alembic upgrade head --sql
```

---

## 🧹 维护操作

### 清理旧数据
```python
# 删除30天前的消息
from database.repositories import MessageRepository
from database.connection import get_async_session

async with get_async_session() as session:
    repo = MessageRepository(session)
    deleted_count = await repo.delete_old_messages(days_old=30)
    print(f"Deleted {deleted_count} old messages")
```

### 备份数据库
```bash
# 导出数据库
docker-compose exec postgres pg_dump -U agent_user voice_agent > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U agent_user voice_agent < backup.sql
```

### 重置数据库
```bash
# 警告：这将删除所有数据！
python scripts/init_db.py --drop

# 重新创建表
python scripts/init_db.py
```

---

## 📈 监控和日志

### 查看 PostgreSQL 日志
```bash
docker-compose logs postgres
```

### 查看 Qdrant 日志
```bash
docker-compose logs qdrant
```

### 查看 n8n 日志
```bash
docker-compose logs n8n
```

### 数据库性能监控
```python
from database.connection import get_db_stats

stats = await get_db_stats()
print(stats)
# {
#     "status": "initialized",
#     "pool_size": 10,
#     "checked_in": 8,
#     "checked_out": 2,
#     ...
# }
```

---

## ⚠️ 故障排除

### 无法连接到 PostgreSQL
1. 确认容器正在运行：`docker-compose ps`
2. 检查端口是否被占用：`netstat -ano | findstr 5432` (Windows) 或 `lsof -i :5432` (Mac/Linux)
3. 检查 `.env` 文件中的密码是否正确
4. 查看日志：`docker-compose logs postgres`

### 数据库迁移失败
1. 检查当前迁移状态：`alembic current`
2. 查看迁移历史：`alembic history`
3. 手动回滚：`alembic downgrade -1`
4. 重新应用：`alembic upgrade head`

### 容器启动失败
1. 检查端口冲突：5432 (PostgreSQL), 6333 (Qdrant), 5678 (n8n)
2. 清理旧容器：`docker-compose down -v`
3. 重新启动：`docker-compose up -d`

---

## 🔒 安全建议

1. **生产环境**：
   - 使用强密码
   - 不要暴露数据库端口到公网
   - 启用 SSL/TLS 连接
   - 定期备份数据

2. **密码管理**：
   - 不要提交 `.env` 文件到 Git
   - 使用环境变量或密钥管理服务
   - 定期更换密码

3. **网络安全**：
   - 使用防火墙限制访问
   - 配置 PostgreSQL `pg_hba.conf`
   - 使用 VPN 或 SSH 隧道访问数据库

---

## 📚 相关文档

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [Qdrant 文档](https://qdrant.tech/documentation/)
- [n8n 文档](https://docs.n8n.io/)

---

## ✅ 检查清单

安装完成后，确认以下步骤：

- [ ] Docker 容器正在运行
- [ ] PostgreSQL 健康检查通过
- [ ] 数据库表已创建
- [ ] `.env` 文件已配置
- [ ] 应用配置已更新（`database.enabled=true`）
- [ ] 可以启动 Voice Agent API
- [ ] 可以创建会话和保存消息

---

**下一步**: 进入 Phase 3A Step 2 - 实现 SQLAlchemy ORM 模型和仓储层（已完成）

