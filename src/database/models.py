"""
Database ORM Models

SQLAlchemy models for conversation persistence.
"""
# 
import uuid

from sqlalchemy import (
    Column, String, Text, Integer, ForeignKey, Index, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship, DeclarativeBase
from sqlalchemy.sql import func

Base: type[DeclarativeBase] = declarative_base()  # type: ignore[assignment]


class User(Base):
    """User account model."""
    
    __tablename__ = "users"
    
    # 主键使用 user_id 以匹配认证系统
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)  # 保留旧字段以兼容
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1, nullable=False)  # 1=active, 0=inactive
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_active = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    meta_data = Column(JSONB, default=dict, nullable=False)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username}, email={self.email})>"


class Session(Base):
    """Conversation session model."""
    
    __tablename__ = "sessions"
    
    session_id = Column(String(255), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, index=True)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, PAUSED, TERMINATED
    context_summary = Column(Text, nullable=True)
    meta_data = Column(JSONB, default=dict, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.timestamp")
    tool_calls = relationship("ToolCall", back_populates="session", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_status_activity', 'status', 'last_activity'),
        Index('idx_session_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Session(session_id={self.session_id}, status={self.status})>"


class Message(Base):
    """Conversation message model."""
    
    __tablename__ = "messages"
    
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # USER, ASSISTANT, SYSTEM, TOOL
    content = Column(Text, nullable=False)
    meta_data = Column(JSONB, default=dict, nullable=False)  # audio_format, confidence_score, etc.
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    tool_calls = relationship("ToolCall", back_populates="message")
    
    # Indexes
    __table_args__ = (
        Index('idx_message_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_message_role_timestamp', 'role', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        try:
            content = str(self.content)
            content_preview = content[:50] + "..." if len(content) > 50 else content
        except Exception:
            content_preview = "[content]"
        return f"<Message(message_id={self.message_id}, role={self.role}, content={content_preview})>"


class ToolCall(Base):
    """Tool execution record model."""
    
    __tablename__ = "tool_calls"
    
    call_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.message_id", ondelete="CASCADE"), nullable=True, index=True)
    tool_name = Column(String(255), nullable=False, index=True)
    parameters = Column(JSONB, default=dict, nullable=False)
    result = Column(JSONB, default=dict, nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Phase 3C: webhook-specific fields
    webhook_url = Column(String(500), nullable=True)
    response_status = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="tool_calls")
    message = relationship("Message", back_populates="tool_calls")
    
    # Indexes
    __table_args__ = (
        Index('idx_toolcall_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_toolcall_name_timestamp', 'tool_name', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<ToolCall(call_id={self.call_id}, tool_name={self.tool_name}, execution_time={self.execution_time_ms}ms)>"

