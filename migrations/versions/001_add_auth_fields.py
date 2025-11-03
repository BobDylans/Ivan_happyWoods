"""Add authentication fields to User model

Revision ID: 001_add_auth_fields
Revises: 
Create Date: 2025-11-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_add_auth_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """添加认证字段到 users 表"""
    
    # 1. 添加新列（允许 NULL，稍后更新）
    op.add_column('users', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'))
    
    # 2. 为现有用户生成 user_id（使用现有的 id）
    op.execute("UPDATE users SET user_id = id WHERE user_id IS NULL")
    
    # 3. 为现有用户设置默认邮箱（使用 username@legacy.local）
    op.execute("UPDATE users SET email = username || '@legacy.local' WHERE email IS NULL")
    
    # 4. 为现有用户设置默认密码（需要用户重置密码）
    # 使用 bcrypt 生成的 'changeme' 的哈希
    op.execute("""
        UPDATE users 
        SET hashed_password = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF6gNiMS'
        WHERE hashed_password IS NULL
    """)
    
    # 5. 设置 is_active 默认值
    op.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
    
    # 6. 将新列设为 NOT NULL
    op.alter_column('users', 'user_id', nullable=False)
    op.alter_column('users', 'email', nullable=False)
    op.alter_column('users', 'hashed_password', nullable=False)
    op.alter_column('users', 'is_active', nullable=False)
    
    # 7. 创建唯一约束
    op.create_unique_constraint('users_user_id_key', 'users', ['user_id'])
    op.create_unique_constraint('users_email_key', 'users', ['email'])
    
    # 8. 创建索引
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_user_id', 'users', ['user_id'])
    
    # 9. 更新 sessions 表的外键（如果存在）
    try:
        op.drop_constraint('sessions_user_id_fkey', 'sessions', type_='foreignkey')
        op.create_foreign_key(
            'sessions_user_id_fkey', 
            'sessions', 'users',
            ['user_id'], ['user_id'],
            ondelete='CASCADE'
        )
    except Exception:
        pass  # 如果外键不存在，忽略
    
    print("✅ 认证字段添加成功！")
    print("⚠️  现有用户的默认密码为 'changeme'，请提醒用户修改密码")


def downgrade():
    """回滚认证字段"""
    
    # 删除索引
    op.drop_index('ix_users_user_id', 'users')
    op.drop_index('ix_users_email', 'users')
    
    # 删除唯一约束
    op.drop_constraint('users_email_key', 'users', type_='unique')
    op.drop_constraint('users_user_id_key', 'users', type_='unique')
    
    # 删除列
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'email')
    op.drop_column('users', 'user_id')
    
    print("✅ 认证字段已回滚")
