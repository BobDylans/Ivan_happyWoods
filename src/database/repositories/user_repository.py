"""
用户数据库仓储 (User Repository)

提供用户表的 CRUD 操作：
- 创建用户
- 查询用户（按 ID、用户名、邮箱）
- 更新用户信息

Phase 3B - User Login System
Created: 2025-11-03
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class UserRepository:
    """用户数据库操作仓储"""
    
    def __init__(self, session: AsyncSession):
        """
        初始化用户仓储
        
        Args:
            session: SQLAlchemy 异步 Session
        """
        self.session = session
    
    async def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None
    ) -> User:
        """
        创建新用户
        
        Args:
            username: 用户名（唯一）
            email: 邮箱（唯一）
            hashed_password: 哈希后的密码
            full_name: 全名（可选）
            
        Returns:
            User: 创建的用户对象
            
        Raises:
            IntegrityError: 如果用户名或邮箱已存在
            
        Example:
            >>> repo = UserRepository(session)
            >>> user = await repo.create_user(
            ...     username="john_doe",
            ...     email="john@example.com",
            ...     hashed_password=hashed_pwd,
            ...     full_name="John Doe"
            ... )
            >>> print(user.username)
            john_doe
        """
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        return user
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名查询用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 用户对象，不存在返回 None
            
        Example:
            >>> user = await repo.get_user_by_username("john_doe")
            >>> if user:
            ...     print(user.email)
        """
        stmt = select(User).filter_by(username=username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱查询用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            Optional[User]: 用户对象，不存在返回 None
            
        Example:
            >>> user = await repo.get_user_by_email("john@example.com")
            >>> if user:
            ...     print(user.username)
        """
        stmt = select(User).filter_by(email=email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        根据用户 ID 查询用户
        
        Args:
            user_id: 用户 UUID
            
        Returns:
            Optional[User]: 用户对象，不存在返回 None
            
        Example:
            >>> from uuid import UUID
            >>> user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
            >>> user = await repo.get_user_by_id(user_id)
        """
        stmt = select(User).filter_by(user_id=user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user(self, user_id: UUID, **kwargs) -> Optional[User]:
        """
        更新用户信息
        
        Args:
            user_id: 用户 UUID
            **kwargs: 要更新的字段（full_name, email, is_active 等）
            
        Returns:
            Optional[User]: 更新后的用户对象，用户不存在返回 None
            
        Example:
            >>> user = await repo.update_user(
            ...     user_id=user_id,
            ...     full_name="John Smith",
            ...     is_active=True
            ... )
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        await self.session.commit()
        await self.session.refresh(user)
        
        return user
