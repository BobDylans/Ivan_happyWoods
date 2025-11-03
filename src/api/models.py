"""
API Data Models (Simplified)

Pydantic v2 compatible models for API request and response schemas.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration for API."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatRequest(BaseModel):
    """Request model for chat endpoints."""
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier") 
    model_config_override: Optional[Dict[str, Any]] = Field(default=None, description="Model configuration overrides")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    model_params: Optional[Dict[str, Any]] = Field(default=None, description="Alias for model config (preferred)")
    stream: bool = Field(default=False, description="Whether to stream the response")
    model_variant: Optional[str] = Field(default=None, description="Model variant: default|fast|creative")


class ChatResponse(BaseModel):
    """Response model for chat endpoints."""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="Agent's response message")
    session_id: str = Field(..., description="Session identifier")
    message_id: str = Field(..., description="Response message identifier")
    timestamp: datetime = Field(..., description="Response timestamp")
    
    # Metadata
    intent: Optional[str] = Field(default=None, description="Detected user intent")
    confidence: Optional[float] = Field(default=None, description="Intent confidence score")
    tool_calls: int = Field(default=0, description="Number of tool calls made")
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")
    
    # Error information
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    message_count: int = Field(default=0, description="Total messages in session")
    active: bool = Field(default=True, description="Whether session is active")


class SessionRequest(BaseModel):
    """Request model for session operations."""
    user_id: Optional[str] = Field(default=None, description="User identifier")
    initial_context: Optional[Dict[str, Any]] = Field(default=None, description="Initial session context")


class SessionResponse(BaseModel):
    """Response model for session endpoints."""
    success: bool = Field(..., description="Whether the request was successful")
    session: Optional[SessionInfo] = Field(default=None, description="Session information")
    message: Optional[str] = Field(default=None, description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Individual component health status."""
    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Component health status")
    message: Optional[str] = Field(default=None, description="Health status message")
    response_time_ms: Optional[float] = Field(default=None, description="Component response time")
    last_check: datetime = Field(..., description="Last health check time")


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""
    status: HealthStatus = Field(..., description="Overall system health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="System version")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    
    # Component health details
    components: List[ComponentHealth] = Field(..., description="Individual component health status")
    
    # System metrics
    metrics: Dict[str, Any] = Field(default_factory=dict, description="System performance metrics")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = Field(default=False, description="Always false for error responses")
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request identifier for tracing")


class ChatMessage(BaseModel):
    """Individual chat message model."""
    id: str = Field(..., description="Unique message identifier")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationHistoryRequest(BaseModel):
    """Request model for conversation history."""
    session_id: str = Field(..., description="Session identifier")
    limit: Optional[int] = Field(default=50, ge=1, le=200, description="Maximum number of messages to retrieve")
    offset: Optional[int] = Field(default=0, ge=0, description="Number of messages to skip")
    include_metadata: bool = Field(default=False, description="Whether to include message metadata")


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""
    success: bool = Field(..., description="Whether the request was successful")
    session_id: str = Field(..., description="Session identifier")
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    total_count: int = Field(..., description="Total number of messages in session")
    has_more: bool = Field(..., description="Whether there are more messages available")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ModelConfigRequest(BaseModel):
    """Request model for updating model configuration."""
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4000, description="Maximum tokens")
    model: Optional[str] = Field(default=None, description="Model name to use")
    tools_enabled: Optional[List[str]] = Field(default=None, description="List of enabled tools")


class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")


# ============================================
# Session Management Models (New)
# ============================================

class SessionListItem(BaseModel):
    """Session list item model for user sessions."""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    status: str = Field(..., description="Session status (ACTIVE, PAUSED, TERMINATED)")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    message_count: int = Field(default=0, description="Total messages in session")
    context_summary: Optional[str] = Field(default=None, description="Session context summary")


class SessionListResponse(BaseModel):
    """Response model for session list."""
    success: bool = Field(default=True, description="Whether the request was successful")
    sessions: List[SessionListItem] = Field(..., description="List of user sessions")
    total: int = Field(..., description="Total number of sessions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_more: bool = Field(..., description="Whether there are more sessions available")


class MessageDetail(BaseModel):
    """Detailed message information."""
    message_id: str = Field(..., description="Message identifier")
    session_id: str = Field(..., description="Session identifier")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Message creation time")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Message metadata")


class SessionDetailResponse(BaseModel):
    """Response model for session detail."""
    success: bool = Field(default=True, description="Whether the request was successful")
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    status: str = Field(..., description="Session status")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    context_summary: Optional[str] = Field(default=None, description="Session context summary")
    messages: List[MessageDetail] = Field(..., description="Session messages")
    total_messages: int = Field(..., description="Total number of messages")
    error: Optional[str] = Field(default=None, description="Error message if failed")