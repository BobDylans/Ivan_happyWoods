"""Conversation Repository - Unified data access layer."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from .session_repository import SessionRepository
from .message_repository import MessageRepository
from ..models import Session, Message

logger = logging.getLogger(__name__)


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repo = SessionRepository(session)
        self.message_repo = MessageRepository(session)
    
    async def get_or_create_session(
        self, session_id: str, user_id: Optional[UUID] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        existing_session = await self.session_repo.get_session(session_id)
        if existing_session:
            await self.session_repo.update_session_activity(session_id)
            return existing_session
        return await self.session_repo.create_session(session_id, user_id, metadata)
    
    async def save_message(
        self, session_id: str, role: str, content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        await self.get_or_create_session(session_id)
        return await self.message_repo.save_message(session_id, role, content, metadata)
    
    async def get_latest_messages(self, session_id: str, count: int = 20) -> List[Message]:
        return await self.message_repo.get_latest_messages(session_id, count)
    
    async def get_conversation_history_dict(
        self, session_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        messages = await self.get_latest_messages(session_id, limit)
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                "metadata": msg.meta_data
            }
            for msg in messages
        ]
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all related messages.
        
        Args:
            session_id: Session identifier to delete
            
        Returns:
            True if deleted successfully, False if session not found
        """
        try:
            # Delete session (cascade will delete related messages)
            deleted = await self.session_repo.delete_session(session_id)
            if deleted:
                logger.info(f"🗑️ 已删除会话及相关数据: {session_id}")
            else:
                logger.warning(f"⚠️ 会话不存在或已被删除: {session_id}")
            return deleted
        except Exception as e:
            logger.error(f"删除会话失败 {session_id}: {e}", exc_info=True)
            raise
