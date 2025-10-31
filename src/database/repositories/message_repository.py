"""
Message Repository

Data access layer for message management.
"""
# 这里专门处理和消息相关的数据库操作

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Message

logger = logging.getLogger(__name__)


class MessageRepository:
    """Repository for message CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: AsyncSession instance
        """
        self.session = session
    
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> Message:
        """
        Save a new message.
        
        Args:
            session_id: Session identifier
            role: Message role (USER, ASSISTANT, SYSTEM, TOOL)
            content: Message content
            metadata: Optional message metadata
            timestamp: Optional custom timestamp
            
        Returns:
            Created Message object
        """
        new_message = Message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
            timestamp=timestamp or datetime.utcnow()
        )
        
        self.session.add(new_message)
        await self.session.flush()
        
        logger.debug(f"Saved message: {new_message.message_id} for session {session_id}")
        return new_message
    
    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Message]:
        """
        Get messages for a session with optional filters.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            role: Optional role filter
            start_time: Optional start timestamp filter
            end_time: Optional end timestamp filter
            
        Returns:
            List of Message objects
        """
        query = select(Message).where(Message.session_id == session_id)
        
        # Apply filters
        conditions = []
        if role:
            conditions.append(Message.role == role)
        if start_time:
            conditions.append(Message.timestamp >= start_time)
        if end_time:
            conditions.append(Message.timestamp <= end_time)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Order by timestamp
        query = query.order_by(Message.timestamp.asc())
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_message_count(
        self,
        session_id: str,
        role: Optional[str] = None
    ) -> int:
        """
        Get message count for a session.
        
        Args:
            session_id: Session identifier
            role: Optional role filter
            
        Returns:
            Number of messages
        """
        query = select(func.count(Message.message_id)).where(
            Message.session_id == session_id
        )
        
        if role:
            query = query.where(Message.role == role)
        
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def get_latest_messages(
        self,
        session_id: str,
        count: int = 10
    ) -> List[Message]:
        """
        Get the most recent messages for a session.
        
        Args:
            session_id: Session identifier
            count: Number of messages to return
            
        Returns:
            List of Message objects (most recent first)
        """
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp.desc())
            .limit(count)
        )
        
        messages = list(result.scalars().all())
        # Return as-is: most recent first (descending order)
        return messages
    
    async def delete_old_messages(
        self,
        days_old: int = 30
    ) -> int:
        """
        Delete messages older than specified days.
        
        Args:
            days_old: Number of days
            
        Returns:
            Number of messages deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        result = await self.session.execute(
            delete(Message).where(Message.timestamp < cutoff_date)
        )
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} messages older than {days_old} days")
        
        return deleted_count
    
    async def delete_session_messages(self, session_id: str) -> int:
        """
        Delete all messages for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of messages deleted
        """
        result = await self.session.execute(
            delete(Message).where(Message.session_id == session_id)
        )
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} messages for session {session_id}")
        
        return deleted_count
    
    async def get_total_message_count(self) -> int:
        """
        Get total message count across all sessions.
        
        Returns:
            Total number of messages
        """
        result = await self.session.execute(
            select(func.count(Message.message_id))
        )
        return result.scalar_one()

