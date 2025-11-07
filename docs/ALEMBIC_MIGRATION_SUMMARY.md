# Alembic 迁移系统集成总结

📅 **日期**: 2025-11-08  
🎯 **目标**: 统一数据库管理，使用 Alembic 进行版本控制

---

## ✅ 完成的工作

### 1. 创建 RAG 表的 Alembic 迁移

**文件**: `migrations/versions/002_add_rag_tables.py`

创建了完整的 RAG 元数据表结构：

- **rag_corpora**: 用户文档集合
  - 字段: corpus_id, user_id, corpus_name, collection_name, description
  - 外键: user_id → users.user_id (CASCADE)
  - 唯一约束: (user_id, corpus_name), collection_name
  - 索引: user_id, corpus_name, collection_name

- **rag_documents**: 文档记录
  - 字段: doc_id, corpus_id, filename, file_hash, file_size, mime_type, metadata
  - 外键: corpus_id → rag_corpora.corpus_id (CASCADE)
  - 索引: corpus_id, filename, file_hash

- **rag_chunks**: 文本块记录
  - 字段: chunk_id, doc_id, qdrant_point_id, chunk_index, text_preview, char_count, metadata
  - 外键: doc_id → rag_documents.doc_id (CASCADE)
  - 唯一约束: qdrant_point_id
  - 索引: doc_id, qdrant_point_id, chunk_index

**特点**:
- ✅ 完整的 upgrade() 和 downgrade() 函数
- ✅ 级联删除保证数据一致性
- ✅ 合理的索引提升查询性能
- ✅ JSONB 字段存储灵活的元数据

### 2. 重构 `scripts/init_db.py`

**主要变更**:
```python
# 之前：直接调用 create_tables()
await create_tables()

# 现在：调用 Alembic
subprocess.run(["alembic", "upgrade", "head"])
```

**新功能**:
- ✅ 使用 Alembic 管理 schema 创建
- ✅ `--drop` 选项会重置 Alembic 历史 (`alembic stamp base`)
- ✅ 显示应用的迁移详情
- ✅ 更清晰的错误提示和故障排除建议

**使用方式**:
```bash
# 初始化数据库（使用 Alembic）
python scripts/init_db.py

# 重置数据库
python scripts/init_db.py --drop

# 加载测试数据
python scripts/init_db.py --test-data
```

### 3. 废弃 `scripts/upgrade_rag_schema.py`

**变更原因**:
- 该脚本直接调用 `create_tables()`，绕过了 Alembic
- 会导致迁移历史不一致
- 不适合团队协作和生产环境

**新行为**:
- 运行时显示废弃警告
- 提示用户使用 `alembic upgrade head`
- 提供交互式选项直接运行 Alembic
- 保留旧实现（标记为 `_legacy`）仅供紧急情况

**推荐替代**:
```bash
# 而不是：python scripts/upgrade_rag_schema.py
# 使用：
alembic upgrade head
```

### 4. 创建详细文档

#### `docs/DATABASE_MIGRATION_GUIDE.md`
**全面的 Alembic 使用指南**，包括：
- 📖 概述和快速开始
- 🔧 常用命令大全
- 📝 创建新迁移的最佳实践
- 🚀 应用和回滚迁移
- 💡 最佳实践和安全建议
- 🔍 故障排除指南
- 📊 与 `scripts/` 的对比表

#### `migrations/README`
**更新的快速参考**，包括：
- 🚀 快速开始（首次设置、更新数据库）
- 📋 常用命令清单
- 📚 现有迁移说明
- 🔧 故障排除快速指南

---

## 📊 对比：之前 vs 现在

### 数据库初始化

| 方面 | 之前 | 现在 |
|------|------|------|
| **方式** | `create_tables()` | `alembic upgrade head` |
| **版本控制** | ❌ 无 | ✅ 完整追踪 |
| **回滚能力** | ❌ 不支持 | ✅ 支持 downgrade |
| **团队协作** | ⚠️ 容易冲突 | ✅ Git 合并友好 |
| **生产安全** | ⚠️ 风险高 | ✅ 渐进式更新 |

### Schema 变更

| 场景 | 之前 | 现在 |
|------|------|------|
| **添加列** | 修改模型 → 删库重建 | `alembic revision` → `upgrade` |
| **数据迁移** | 手动 SQL | Alembic 迁移脚本 |
| **错误回滚** | ❌ 需要备份恢复 | ✅ `alembic downgrade -1` |
| **查看历史** | ❌ 无法追溯 | ✅ `alembic history` |

---

## 🎯 使用流程

### 开发环境

```bash
# 1. 首次初始化
python scripts/init_db.py

# 2. 修改模型后创建迁移
# 编辑 src/database/models.py
alembic revision --autogenerate -m "Add user preferences"

# 3. 查看生成的迁移文件
cat migrations/versions/xxx_add_user_preferences.py

# 4. 应用迁移
alembic upgrade head

# 5. 测试回滚
alembic downgrade -1
alembic upgrade head
```

### 生产环境

```bash
# 1. 拉取最新代码
git pull

# 2. 备份数据库
pg_dump voice_agent > backup_$(date +%Y%m%d).sql

# 3. 预览迁移 SQL（不执行）
alembic upgrade head --sql > migration.sql

# 4. 检查 SQL
cat migration.sql

# 5. 应用迁移
alembic upgrade head

# 6. 验证
alembic current
psql voice_agent -c "\dt"
```

---

## 🔄 迁移路径

### 从旧方式迁移到 Alembic

如果你的数据库是用 `create_tables()` 创建的：

```bash
# 1. 确认当前表结构
psql voice_agent -c "\dt"

# 2. 标记数据库为最新状态
alembic stamp head

# 3. 验证
alembic current
# 应该显示: 002_add_rag_tables

# 4. 以后使用 Alembic 进行变更
alembic revision --autogenerate -m "Your changes"
```

---

## 📚 现有迁移

### 001_add_auth_fields
- **作用**: 添加用户认证字段
- **表**: users
- **新增**: user_id, email, hashed_password, full_name, is_active
- **约束**: 唯一 (user_id, email)
- **索引**: user_id, email, username

### 002_add_rag_tables
- **作用**: 创建 RAG 元数据表
- **表**: rag_corpora, rag_documents, rag_chunks
- **关系**: 
  - rag_corpora ← rag_documents ← rag_chunks
  - users → rag_corpora (user_id)
- **级联**: DELETE CASCADE 保证数据一致性

---

## 🎓 最佳实践

### 1. 迁移命名
```bash
# ✅ 好的命名
alembic revision -m "add_user_email_verification"
alembic revision -m "create_notifications_table"
alembic revision -m "add_index_to_messages"

# ❌ 不好的命名
alembic revision -m "update"
alembic revision -m "fix"
alembic revision -m "changes"
```

### 2. 渐进式迁移
```python
# ✅ 分步骤
def upgrade():
    # 1. 添加可选列
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    
    # 2. 迁移数据
    op.execute("UPDATE users SET email = username || '@domain.com'")
    
    # 3. 设置为必填
    op.alter_column('users', 'email', nullable=False)
    
    # 4. 添加约束
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
```

### 3. 测试迁移
```bash
# 开发环境测试
alembic upgrade head    # 升级
alembic downgrade -1    # 回滚
alembic upgrade head    # 再次升级

# 验证数据完整性
psql voice_agent -c "SELECT COUNT(*) FROM users;"
```

### 4. 生产前检查
```bash
# 1. 生成 SQL 预览
alembic upgrade head --sql > migration_preview.sql

# 2. 人工审查
cat migration_preview.sql

# 3. 在 staging 环境测试
# 4. 准备回滚计划
alembic downgrade -1 --sql > rollback.sql

# 5. 执行迁移
alembic upgrade head
```

---

## 🔧 故障排除

### 问题：Alembic 找不到
```bash
pip install alembic
```

### 问题：迁移历史不匹配
```bash
# 查看当前状态
alembic current

# 如果是新数据库但表已存在
alembic stamp head

# 如果需要重置
alembic stamp base
```

### 问题：autogenerate 不检测变化
```bash
# 1. 确保模型已导入
# 检查 migrations/env.py 中的 target_metadata

# 2. 清除 __pycache__
find . -type d -name __pycache__ -exec rm -rf {} +

# 3. 重新生成
alembic revision --autogenerate -m "description"
```

---

## 📖 相关文档

- [DATABASE_MIGRATION_GUIDE.md](./DATABASE_MIGRATION_GUIDE.md) - 详细的 Alembic 使用指南
- [migrations/README](../migrations/README) - 快速参考
- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)

---

## 🎉 总结

通过这次集成，我们实现了：

✅ **统一的数据库管理**
- 所有 schema 变更通过 Alembic 管理
- `scripts/init_db.py` 调用 Alembic
- `scripts/upgrade_rag_schema.py` 标记为废弃

✅ **完整的版本控制**
- 每次变更都有迁移记录
- 可以查看完整历史
- 支持升级和回滚

✅ **生产就绪**
- 安全的渐进式更新
- 可预览 SQL
- 支持回滚

✅ **团队友好**
- Git 合并无冲突
- 清晰的迁移历史
- 标准化的流程

✅ **完善的文档**
- 详细的使用指南
- 故障排除手册
- 最佳实践示例

现在，项目的数据库管理更加专业、安全和可维护！🚀

