# Database Migration Guide

本文档说明如何使用 Alembic 管理数据库 schema 的迁移和版本控制。

## 📋 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [常用命令](#常用命令)
- [创建新迁移](#创建新迁移)
- [应用迁移](#应用迁移)
- [回滚迁移](#回滚迁移)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

---

## 概述

### 什么是 Alembic？

Alembic 是 SQLAlchemy 的数据库迁移工具，类似于 Git 对代码的版本控制。它允许你：

- ✅ 追踪数据库 schema 的变更历史
- ✅ 在不丢失数据的情况下修改表结构
- ✅ 在团队中同步数据库更改
- ✅ 支持升级和回滚操作
- ✅ 生产环境友好

### 目录结构

```
backEnd/
├── migrations/                 # Alembic 迁移目录
│   ├── versions/              # 迁移脚本版本
│   │   ├── 001_add_auth_fields.py
│   │   └── 002_add_rag_tables.py
│   ├── env.py                 # Alembic 环境配置
│   ├── script.py.mako         # 迁移脚本模板
│   └── README                 # 基本用法
├── alembic.ini               # Alembic 配置文件
└── scripts/                  # 辅助脚本
    └── init_db.py            # 数据库初始化（使用 Alembic）
```

---

## 快速开始

### 1. 初始化数据库（全新安装）

对于全新的数据库，使用初始化脚本：

```bash
# 方式 1：使用辅助脚本（推荐）
python scripts/init_db.py

# 方式 2：直接使用 Alembic
alembic upgrade head
```

### 2. 更新现有数据库

如果数据库已存在但需要应用新的迁移：

```bash
alembic upgrade head
```

### 3. 检查当前状态

```bash
# 查看当前版本
alembic current

# 查看迁移历史
alembic history --verbose
```

---

## 常用命令

### 查看状态

```bash
# 显示当前数据库版本
alembic current

# 显示完整迁移历史
alembic history

# 显示详细历史（包括描述）
alembic history --verbose

# 显示待应用的迁移
alembic show head
```

### 应用迁移

```bash
# 升级到最新版本
alembic upgrade head

# 升级到特定版本
alembic upgrade 002_add_rag_tables

# 升级一个版本
alembic upgrade +1

# 升级两个版本
alembic upgrade +2

# 仅显示 SQL（不执行）
alembic upgrade head --sql
```

### 回滚迁移

```bash
# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade 001_add_auth_fields

# 回滚到初始状态
alembic downgrade base

# 仅显示 SQL（不执行）
alembic downgrade -1 --sql
```

---

## 创建新迁移

### 自动生成迁移（推荐）

Alembic 可以检测模型变化并自动生成迁移脚本：

```bash
# 1. 修改 src/database/models.py 中的模型
# 2. 生成迁移脚本
alembic revision --autogenerate -m "Add user preferences table"

# 3. 检查生成的迁移脚本
# 文件位于: migrations/versions/xxx_add_user_preferences_table.py

# 4. 如有需要，手动调整迁移脚本

# 5. 应用迁移
alembic upgrade head
```

### 手动创建迁移

对于复杂的数据迁移，可以手动创建：

```bash
# 创建空白迁移脚本
alembic revision -m "migrate_user_data"

# 编辑生成的文件，实现 upgrade() 和 downgrade() 函数
```

**示例：添加新列**

```python
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
    op.create_index('ix_users_phone', 'users', ['phone'])

def downgrade():
    op.drop_index('ix_users_phone', 'users')
    op.drop_column('users', 'phone')
```

---

## 应用迁移

### 开发环境

```bash
# 1. 拉取最新代码
git pull

# 2. 应用迁移
alembic upgrade head

# 3. 验证
alembic current
```

### 生产环境

```bash
# 1. 备份数据库！
pg_dump voice_agent > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 查看待应用的迁移（不执行）
alembic upgrade head --sql > migration.sql
# 检查 migration.sql 确保安全

# 3. 应用迁移
alembic upgrade head

# 4. 验证
alembic current
psql voice_agent -c "\dt"  # 检查表
```

---

## 回滚迁移

### 紧急回滚

如果迁移后出现问题：

```bash
# 1. 立即回滚到上一个版本
alembic downgrade -1

# 2. 检查状态
alembic current

# 3. 验证应用功能
```

### 计划回滚

```bash
# 1. 查看历史
alembic history

# 2. 生成回滚 SQL（预览）
alembic downgrade -1 --sql

# 3. 执行回滚
alembic downgrade -1

# 4. 验证
alembic current
```

---

## 最佳实践

### 1. 迁移脚本命名

使用描述性的名称：

```bash
# ✅ 好的命名
alembic revision -m "add_user_email_verification"
alembic revision -m "create_rag_tables"
alembic revision -m "add_index_to_sessions"

# ❌ 不好的命名
alembic revision -m "update"
alembic revision -m "fix"
```

### 2. 分解大的迁移

将复杂的迁移分解为多个小步骤：

```bash
# 而不是一次性修改很多表
alembic revision -m "add_user_profile_fields"
alembic revision -m "migrate_user_data"
alembic revision -m "remove_old_user_fields"
```

### 3. 测试迁移

在应用到生产前测试：

```bash
# 1. 在开发环境测试
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# 2. 验证数据完整性
psql voice_agent -c "SELECT COUNT(*) FROM users;"

# 3. 在 staging 环境测试
# 4. 然后再应用到生产
```

### 4. 保持向后兼容

迁移应该是渐进的：

```python
# ✅ 好的做法：先添加可选列
def upgrade():
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))

# ❌ 不好的做法：直接添加必填列（会破坏现有数据）
def upgrade():
    op.add_column('users', sa.Column('email', sa.String(255), nullable=False))
```

### 5. 数据迁移策略

对于数据转换，分步进行：

```python
def upgrade():
    # 1. 添加新列（允许 NULL）
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    
    # 2. 迁移数据
    op.execute("UPDATE users SET email = username || '@legacy.local' WHERE email IS NULL")
    
    # 3. 设置为 NOT NULL
    op.alter_column('users', 'email', nullable=False)
    
    # 4. 添加约束
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
```

---

## 故障排除

### 问题 1：Alembic 找不到

```bash
# 错误：alembic: command not found

# 解决：
pip install alembic
# 或
.\venv\Scripts\Activate.ps1
pip install alembic
```

### 问题 2：迁移历史不一致

```bash
# 错误：Can't locate revision identified by 'xxx'

# 解决：检查数据库版本
alembic current

# 如果数据库版本不存在，手动设置
alembic stamp head  # 标记为最新版本
alembic stamp base  # 标记为初始状态
```

### 问题 3：自动生成的迁移不正确

```bash
# 问题：autogenerate 生成了错误的迁移

# 解决：
1. 删除错误的迁移文件
2. 检查模型定义是否正确
3. 重新生成
alembic revision --autogenerate -m "description"
4. 手动检查和编辑生成的文件
```

### 问题 4：生产环境迁移失败

```bash
# 紧急恢复步骤：

# 1. 回滚数据库
alembic downgrade -1

# 2. 或从备份恢复
psql voice_agent < backup_20251108_103000.sql

# 3. 检查迁移脚本是否有问题
cat migrations/versions/xxx_migration.py

# 4. 修复后重新测试
```

### 问题 5：与直接创建表冲突

```bash
# 问题：之前使用 create_tables() 直接创建了表

# 解决：标记当前数据库状态
alembic stamp head  # 告诉 Alembic 数据库已是最新状态
```

---

## 与 scripts/ 的对比

| 场景 | 使用 Alembic | 使用 scripts/ |
|------|-------------|--------------|
| **生产环境更新** | ✅ `alembic upgrade head` | ❌ 不推荐 |
| **开发环境初始化** | ✅ `python scripts/init_db.py` | ✅ 快速初始化 |
| **添加新字段** | ✅ `alembic revision` | ❌ 不合适 |
| **重置开发数据库** | ⚠️ 较慢 | ✅ `init_db.py --drop` |
| **批量导入文档** | ❌ 不合适 | ✅ `rag_ingest.py` |
| **版本控制** | ✅ 自动追踪 | ❌ 无追踪 |
| **团队协作** | ✅ 易于合并 | ⚠️ 容易冲突 |

---

## 现有迁移

### 001_add_auth_fields.py
- 添加用户认证相关字段
- 添加 `user_id`, `email`, `hashed_password` 等
- 创建唯一约束和索引

### 002_add_rag_tables.py
- 创建 RAG 元数据表
- `rag_corpora`: 用户文档集合
- `rag_documents`: 文档记录
- `rag_chunks`: 文本块记录

---

## 相关文档

- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [项目数据库模型](../src/database/models.py)
- [数据库连接配置](../src/database/connection.py)

---

## 总结

- ✅ **始终使用 Alembic** 管理 schema 变更
- ✅ **生产环境前测试** 所有迁移
- ✅ **保持向后兼容** 以支持渐进式更新
- ✅ **备份数据** 在执行迁移前
- ✅ **代码审查** 所有迁移脚本

如有问题，请参考上面的故障排除部分或查阅 Alembic 官方文档。

