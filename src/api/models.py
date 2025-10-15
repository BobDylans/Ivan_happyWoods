"""
API Data Models

Pydantic models for API request and response schemas.
These models define the structure for all API endpoints.
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


class ChatMessage(BaseModel):
    """Individual chat message model."""
    id: str = Field(..., description="Unique message identifier")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class ChatRequest(BaseModel):
    """Request model for chat endpoints."""
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier") 
    model_config: Optional[Dict[str, Any]] = Field(default=None, description="Model configuration overrides")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Hello, can you help me search for Python tutorials?",
                "session_id": "session_123",
                "user_id": "user_456",
                "model_config": {
                    "temperature": 0.7,
                    "model": "gpt-4"
                }
            }
        }
    }


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
    
    # Usage statistics
    usage: Optional[Dict[str, Any]] = Field(default=None, description="Token usage statistics")
    
    # Error information
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "success": True,
                "response": "I found some great Python tutorials for you!",
                "session_id": "session_123",
                "message_id": "msg_789",
                "timestamp": "2025-10-13T10:30:00Z",
                "intent": "search",
                "confidence": 0.95,
                "tool_calls": 1,
                "processing_time_ms": 1250.5,
                "usage": {
                    "total_tokens": 150,
                    "prompt_tokens": 80,
                    "completion_tokens": 70
                }
            }
        }


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    message_count: int = Field(default=0, description="Total messages in session")
    active: bool = Field(default=True, description="Whether session is active")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionRequest(BaseModel):
    """Request model for session operations."""
    user_id: Optional[str] = Field(default=None, description="User identifier")
    initial_context: Optional[Dict[str, Any]] = Field(default=None, description="Initial session context")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_456",
                "initial_context": {
                    "language": "en",
                    "timezone": "UTC"
                }
            }
        }


class SessionResponse(BaseModel):
    """Response model for session endpoints."""
    success: bool = Field(..., description="Whether the request was successful")
    session: Optional[SessionInfo] = Field(default=None, description="Session information")
    message: Optional[str] = Field(default=None, description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "session": {
                    "session_id": "session_123",
                    "user_id": "user_456",
                    "created_at": "2025-10-13T10:00:00Z",
                    "last_activity": "2025-10-13T10:30:00Z",
                    "message_count": 5,
                    "active": True
                },
                "message": "Session created successfully"
            }
        }


class ConversationHistoryRequest(BaseModel):
    """Request model for conversation history."""
    session_id: str = Field(..., description="Session identifier")
    limit: Optional[int] = Field(default=50, ge=1, le=200, description="Maximum number of messages to retrieve")
    offset: Optional[int] = Field(default=0, ge=0, description="Number of messages to skip")
    include_metadata: bool = Field(default=False, description="Whether to include message metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "session_123",
                "limit": 20,
                "offset": 0,
                "include_metadata": True
            }
        }


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""
    success: bool = Field(..., description="Whether the request was successful")
    session_id: str = Field(..., description="Session identifier")
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    total_count: int = Field(..., description="Total number of messages in session")
    has_more: bool = Field(..., description="Whether there are more messages available")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "session_id": "session_123",
                "messages": [
                    {
                        "id": "msg_1",
                        "role": "user",
                        "content": "Hello!",
                        "timestamp": "2025-10-13T10:00:00Z",
                        "metadata": {}
                    },
                    {
                        "id": "msg_2", 
                        "role": "assistant",
                        "content": "Hi! How can I help you?",
                        "timestamp": "2025-10-13T10:00:01Z",
                        "metadata": {"intent": "greeting"}
                    }
                ],
                "total_count": 10,
                "has_more": True
            }
        }


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
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


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
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-10-13T10:30:00Z",
                "version": "1.0.0",
                "uptime_seconds": 3600.0,
                "components": [
                    {
                        "name": "agent_core",
                        "status": "healthy",
                        "message": "Agent core is operational",
                        "response_time_ms": 12.5,
                        "last_check": "2025-10-13T10:30:00Z"
                    },
                    {
                        "name": "llm_service",
                        "status": "healthy", 
                        "message": "LLM service is responsive",
                        "response_time_ms": 245.8,
                        "last_check": "2025-10-13T10:30:00Z"
                    }
                ],
                "metrics": {
                    "requests_per_minute": 125,
                    "average_response_time_ms": 890.5,
                    "active_sessions": 23,
                    "memory_usage_mb": 512.7
                }
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = Field(default=False, description="Always false for error responses")
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request identifier for tracing")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "success": False,
                "error": "Invalid session identifier",
                "error_code": "INVALID_SESSION",
                "details": {
                    "session_id": "invalid_session_123",
                    "suggestion": "Please create a new session or use a valid session ID"
                },
                "timestamp": "2025-10-13T10:30:00Z",
                "request_id": "req_abc123"
            }
        }


# Model configuration request
class ModelConfigRequest(BaseModel):
    """Request model for updating model configuration."""
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4000, description="Maximum tokens")
    model: Optional[str] = Field(default=None, description="Model name to use")
    tools_enabled: Optional[List[str]] = Field(default=None, description="List of enabled tools")
    
    class Config:
        schema_extra = {
            "example": {
                "temperature": 0.7,
                "max_tokens": 1500,
                "model": "gpt-4",
                "tools_enabled": ["search_tool", "calculator", "time_tool"]
            }
        }


# WebSocket message models
class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }