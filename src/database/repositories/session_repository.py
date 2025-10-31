"""
Session Repository

Data access layer for session management.
"""
# 这里专门处理会话相关
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Session, User

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for session CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: AsyncSession instance
        """
        self.session = session
    
    async def create_session(
        self,
        session_id: str,
        user_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new conversation session.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user ID
            metadata: Optional session metadata
            
        Returns:
            Created Session object
        """
        new_session = Session(
            session_id=session_id,
            user_id=user_id,
            status="ACTIVE",
            meta_data=metadata or {}  # 修正：使用 meta_data 字段名
        )
        
        self.session.add(new_session)
        await self.session.flush()
        
        logger.info(f"Created session: {session_id}")
        return new_session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object or None if not found
        """
        result = await self.session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def update_session_activity(self, session_id: str) -> bool:
        """
        Update session last_activity timestamp.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if updated, False if session not found
        """
        result = await self.session.execute(
            update(Session)
            .where(Session.session_id == session_id)
            .values(last_activity=datetime.utcnow())
        )
        
        updated = result.rowcount > 0
        if updated:
            logger.debug(f"Updated activity for session: {session_id}")
        
        return updated
    
    async def update_status(self, session_id: str, status: str) -> bool:
        """
        Update session status.
        
        Args:
            session_id: Session identifier
            status: New status (ACTIVE, PAUSED, TERMINATED)
            
        Returns:
            True if updated, False if session not found
        """
        result = await self.session.execute(
            update(Session)
            .where(Session.session_id == session_id)
            .values(status=status, last_activity=datetime.utcnow())
        )
        
        updated = result.rowcount > 0
        if updated:
            logger.debug(f"Updated status for session {session_id} to {status}")
        
        return updated
    
    async def terminate_session(self, session_id: str) -> bool:
        """
        Mark session as terminated.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if terminated, False if session not found
        """
        result = await self.session.execute(
            update(Session)
            .where(Session.session_id == session_id)
            .values(status="TERMINATED", last_activity=datetime.utcnow())
        )
        
        terminated = result.rowcount > 0
        if terminated:
            logger.info(f"Terminated session: {session_id}")
        
        return terminated
    
    async def get_user_sessions(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User identifier
            status: Optional status filter (ACTIVE, PAUSED, TERMINATED)
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List of Session objects
        """
        query = select(Session).where(Session.user_id == user_id)
        
        if status:
            query = query.where(Session.status == status)
        
        query = query.order_by(Session.last_activity.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_active_sessions(self, limit: int = 100) -> List[Session]:
        """
        Get all active sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of active Session objects
        """
        result = await self.session.execute(
            select(Session)
            .where(Session.status == "ACTIVE")
            .order_by(Session.last_activity.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_sessions(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Count sessions with optional filters.
        
        Args:
            user_id: Optional user ID filter
            status: Optional status filter
            
        Returns:
            Number of matching sessions
        """
        query = select(func.count(Session.session_id))
        
        conditions = []
        if user_id:
            conditions.append(Session.user_id == user_id)
        if status:
            conditions.append(Session.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions.
        
        Returns:
            Number of active sessions
        """
        return await self.count_sessions(status="ACTIVE")
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all related data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if session not found
        """
        result = await self.session.execute(
            delete(Session).where(Session.session_id == session_id)
        )
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted session: {session_id}")
        
        return deleted
    
    async def update_context_summary(
        self,
        session_id: str,
        summary: str
    ) -> bool:
        """
        Update session context summary.
        
        Args:
            session_id: Session identifier
            summary: Context summary text
            
        Returns:
            True if updated, False if session not found
        """
        result = await self.session.execute(
            update(Session)
            .where(Session.session_id == session_id)
            .values(context_summary=summary)
        )
        
        return result.rowcount > 0

