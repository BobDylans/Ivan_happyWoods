"""
API Routes

FastAPI route handlers for all endpoints including chat, sessions, and health checks.
"""

import time
import uuid
import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from .stream_manager import get_stream_manager
from .event_utils import create_start_event, create_end_event, create_cancelled_event, create_error_event
from .models_v2 import (
    ChatRequest, ChatResponse, SessionRequest, SessionResponse, 
    ConversationHistoryRequest, ConversationHistoryResponse,
    HealthResponse, HealthStatus, ComponentHealth, ErrorResponse,
    ModelConfigRequest, SessionInfo, ChatMessage, MessageRole
)

# Import agent functionality with fallback
try:
    from agent.graph import create_voice_agent
    from agent.state import MessageRole as AgentMessageRole
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    create_voice_agent = None
    AgentMessageRole = None

try:
    from config.settings import ConfigManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    ConfigManager = None


logger = logging.getLogger(__name__)


# Global agent instance (will be initialized in main.py)
_voice_agent = None
_start_time = datetime.now()
_session_store: Dict[str, Dict[str, Any]] = {}  # Simple in-memory session store


def get_voice_agent():
    """Dependency to get the voice agent instance."""
    global _voice_agent
    if _voice_agent is None:
        if AGENT_AVAILABLE:
            try:
                _voice_agent = create_voice_agent(environment="development")
            except Exception as e:
                logger.warning(f"Could not create voice agent: {e}")
                _voice_agent = None
        else:
            logger.warning("Agent functionality not available")
    return _voice_agent


def set_voice_agent(agent):
    """Set the global voice agent instance."""
    global _voice_agent
    _voice_agent = agent


def get_session_manager(request: Request):
    """Dependency to get the session manager from app.state."""
    return request.app.state.session_manager


# Create routers
chat_router = APIRouter(prefix="/chat", tags=["Chat"])
session_router = APIRouter(prefix="/session", tags=["Session"])
health_router = APIRouter(prefix="/health", tags=["Health"])
tools_router = APIRouter(prefix="/tools", tags=["Tools"])


@chat_router.post("/", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    req: Request,  # ✅ 添加 Request 以访问 app.state
    agent = Depends(get_voice_agent)
):
    """
    Send a message to the voice agent and get a response.
    
    This endpoint processes user messages through the conversation agent,
    handles tool calls, and returns formatted responses.
    """
    start_time = time.time()
    
    try:
        # 如果没有提供sessionId和message_id，则生成新的
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"
        
        # Create message ID
        message_id = f"msg_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        # 如果agent不可用，返回错误
        if agent is None:
            # Fallback response when agent is not available
            return ChatResponse(
                success=False,
                response="Voice agent is currently unavailable. Please try again later.",
                session_id=session_id,
                message_id=message_id,
                timestamp=datetime.now(),
                error="Agent not available",
                error_code="SERVICE_UNAVAILABLE"
            )
        
        #判断是否需要流式返回
        effective_model_cfg = request.model_params or request.model_config_override
        if request.stream:
            # 🔧 获取 session_manager 和历史记录
            session_manager = req.app.state.session_manager
            external_history = session_manager.get_history(session_id)
            
            async def event_generator():
                try:
                    variant = request.model_variant
                    effective_cfg = effective_model_cfg
                    if variant and not effective_cfg:
                        if variant == 'fast':
                            effective_cfg = {"model": agent.config.llm.models.fast}
                        elif variant == 'creative':
                            effective_cfg = {"model": agent.config.llm.models.creative}
                        else:
                            effective_cfg = {"model": agent.config.llm.models.default}
                    collected = []
                    async for event in agent.process_message_stream(
                        user_input=request.message,
                        session_id=session_id,
                        user_id=request.user_id,
                        model_config=effective_cfg,
                        external_history=external_history  # 🔧 传递历史记录
                    ):
                        if event.get('type') == 'delta' and event.get('content'):
                            collected.append(event['content'])
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        if event.get('type') == 'end':
                            break
                    
                    # 🔧 流式完成后保存消息到历史
                    if collected:
                        full_response = "".join(collected)
                        logger.info(f"💾 [POST /chat/] 保存对话到历史 - session: {session_id}, user: {request.message[:50]}..., assistant: {len(full_response)} 字符")
                        session_manager.add_message(session_id, "user", request.message)
                        session_manager.add_message(session_id, "assistant", full_response)
                        logger.info(f"✅ [POST /chat/] 历史记录已保存，当前历史长度: {len(session_manager.get_history(session_id))}")
                        
                except Exception as e:
                    yield f"data: {json.dumps({'type':'error','error':str(e)}, ensure_ascii=False)}\n\n"
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        else:
            # 🔧 非流式模式：获取历史记录
            session_manager = req.app.state.session_manager
            external_history = session_manager.get_history(session_id)
            
            result = await agent.process_message(
                user_input=request.message,
                session_id=session_id,
                user_id=request.user_id,
                model_config=effective_model_cfg,
                external_history=external_history  # 🔧 传递历史记录
            )
            
            # 🔧 保存消息到历史
            if result.get("success") and result.get("response"):
                try:
                    session_manager.add_message(session_id, "user", request.message)
                    session_manager.add_message(session_id, "assistant", result.get("response"))
                    logger.info(f"💾 [POST /chat/ 非流式] 已保存对话到历史 - session: {session_id}")
                except Exception as e:
                    logger.warning(f"保存会话历史失败: {e}")
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Update session store
        _session_store[session_id] = {
            "session_id": session_id,
            "user_id": request.user_id,
            "last_activity": datetime.now(),
            "message_count": _session_store.get(session_id, {}).get("message_count", 0) + 1
        }
        
        if isinstance(result, dict):
            return ChatResponse(
                success=result.get("success", True),
                response=result.get("response", ""),
                session_id=session_id,
                message_id=message_id,
                timestamp=datetime.now(),
                intent=result.get("metadata", {}).get("intent"),
                tool_calls=result.get("metadata", {}).get("tool_calls", 0),
                processing_time_ms=processing_time,
                error=result.get("error") if not result.get("success", True) else None
            )
        raise HTTPException(status_code=500, detail="Unexpected result type")
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            success=False,
            response="I apologize, but I encountered an error processing your message.",
            session_id=request.session_id or f"session_{uuid.uuid4().hex[:12]}",
            message_id=f"msg_{uuid.uuid4().hex[:8]}_{int(time.time())}",
            timestamp=datetime.now(),
            processing_time_ms=processing_time,
            error=str(e),
            error_code="INTERNAL_ERROR"
        )


@chat_router.post("/stream")
async def chat_message_stream(
    request: ChatRequest,
    req: Request,  # 添加 Request 以访问 app.state
    agent = Depends(get_voice_agent)
):
    """Stream a chat response using Server-Sent Events style JSON lines."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not available")
    session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"
    
    # 🔧 获取 session_manager 和历史记录
    session_manager = req.app.state.session_manager
    external_history = session_manager.get_history(session_id)
    
    async def event_generator():
        accumulated_content = []  # 收集完整回复
        try:
            async for event in agent.process_message_stream(
                user_input=request.message,
                session_id=session_id,
                user_id=request.user_id,
                model_config=request.model_params,
                external_history=external_history  # 🔧 传递历史记录
            ):
                # 收集 delta 内容
                if event.get("type") == "delta" and "content" in event:
                    accumulated_content.append(event["content"])
                
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # 🔧 流式完成后保存消息到历史
            if accumulated_content:
                full_response = "".join(accumulated_content)
                logger.info(f"💾 保存对话到历史 - session: {session_id}, user: {request.message[:50]}..., assistant: {len(full_response)} 字符")
                session_manager.add_message(session_id, "user", request.message)
                session_manager.add_message(session_id, "assistant", full_response)
                logger.info(f"✅ 历史记录已保存，当前历史长度: {len(session_manager.get_history(session_id))}")
                
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','error':str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@chat_router.get("/stream")
async def chat_message_stream_get(
    message: str,
    req: Request,  # 添加 Request
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    model_variant: Optional[str] = None,
    agent = Depends(get_voice_agent)
):
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not available")
    session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
    
    # 🔧 获取历史记录
    session_manager = req.app.state.session_manager
    external_history = session_manager.get_history(session_id)
    
    async def event_generator():
        accumulated_content = []
        cfg = None
        if model_variant:
            if model_variant == 'fast':
                cfg = {"model": agent.config.llm.models.fast}
            elif model_variant == 'creative':
                cfg = {"model": agent.config.llm.models.creative}
            else:
                cfg = {"model": agent.config.llm.models.default}
        
        try:
            async for event in agent.process_message_stream(
                user_input=message,
                session_id=session_id,
                user_id=user_id,
                model_config=cfg,
                external_history=external_history  # 🔧 传递历史
            ):
                if event.get("type") == "delta" and "content" in event:
                    accumulated_content.append(event["content"])
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # 🔧 保存消息
            if accumulated_content:
                full_response = "".join(accumulated_content)
                logger.info(f"💾 [GET] 保存对话到历史 - session: {session_id}, message: {message[:50]}..., response: {len(full_response)} 字符")
                session_manager.add_message(session_id, "user", message)
                session_manager.add_message(session_id, "assistant", full_response)
                logger.info(f"✅ [GET] 历史记录已保存，当前历史长度: {len(session_manager.get_history(session_id))}")
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','error':str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@chat_router.websocket("/ws")
async def chat_ws(websocket: WebSocket, agent = Depends(get_voice_agent)):
    if agent is None:
        await websocket.close(code=1013)
        return
    
    await websocket.accept()
    stream_manager = get_stream_manager()
    
    # 🔧 获取 session_manager
    session_manager = websocket.app.state.session_manager
    
    current_session_id: Optional[str] = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if isinstance(data, dict) and data.get("type") == "close":
                await websocket.close()
                return
            
            if isinstance(data, dict) and data.get("type") == "cancel":
                # True cancellation: cancel the running streaming task
                cancel_session_id = data.get("session_id") or current_session_id
                if cancel_session_id:
                    cancelled = await stream_manager.cancel_task(cancel_session_id)
                    if cancelled:
                        logger.info(f"Stream cancelled for session {cancel_session_id}")
                        await websocket.send_json(create_cancelled_event(
                            session_id=cancel_session_id,
                            reason="User requested cancellation"
                        ))
                    else:
                        await websocket.send_json(create_error_event(
                            error="No active stream to cancel",
                            session_id=cancel_session_id,
                            error_code="NO_ACTIVE_STREAM"
                        ))
                continue
            
            message = data.get("message")
            session_id = data.get("session_id") or f"session_{uuid.uuid4().hex[:12]}"
            current_session_id = session_id
            user_id = data.get("user_id")
            model_cfg = data.get("model_config")
            variant = data.get("model_variant")
            
            # 🔧 获取历史记录
            external_history = session_manager.get_history(session_id)
            
            if variant and model_cfg is None:
                # Map variant -> model
                if variant == "fast":
                    model_cfg = {"model": agent.config.llm.models.fast}
                elif variant == "creative":
                    model_cfg = {"model": agent.config.llm.models.creative}
                else:
                    model_cfg = {"model": agent.config.llm.models.default}
            
            # Create streaming task
            async def stream_task():
                accumulated_content = []  # 🔧 收集回复
                try:
                    # Send start event (will be duplicated from agent but ensures consistency)
                    # The agent's stream will also send start, this is intentional for now
                    
                    async for event in agent.process_message_stream(
                        user_input=message,
                        session_id=session_id,
                        user_id=user_id,
                        model_config=model_cfg,
                        external_history=external_history  # 🔧 传递历史
                    ):
                        # 🔧 收集 delta 内容
                        if event.get("type") == "delta" and "content" in event:
                            accumulated_content.append(event["content"])
                        
                        await websocket.send_json(event)
                    
                    # 🔧 保存消息到历史
                    if accumulated_content:
                        full_response = "".join(accumulated_content)
                        logger.info(f"💾 [WebSocket] 保存对话到历史 - session: {session_id}, message: {message[:50] if message else 'N/A'}..., response: {len(full_response)} 字符")
                        session_manager.add_message(session_id, "user", message)
                        session_manager.add_message(session_id, "assistant", full_response)
                        logger.info(f"✅ [WebSocket] 历史记录已保存，当前历史长度: {len(session_manager.get_history(session_id))}")
                    
                    # Agent stream already sends end event, no need to duplicate
                
                except asyncio.CancelledError:
                    # Stream was cancelled
                    logger.info(f"Stream task cancelled for session {session_id}")
                    await websocket.send_json(create_cancelled_event(
                        session_id=session_id,
                        reason="Stream cancelled by system"
                    ))
                    raise
                
                finally:
                    await stream_manager.unregister_task(session_id)
            
            # Register and run the task
            task = asyncio.create_task(stream_task())
            await stream_manager.register_task(session_id, task)
            await task
    
    except WebSocketDisconnect:
        if current_session_id:
            await stream_manager.cancel_task(current_session_id)
        return
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json(create_error_event(
                error=str(e),
                session_id=current_session_id,
                error_code="WEBSOCKET_ERROR"
            ))
        finally:
            if current_session_id:
                await stream_manager.cancel_task(current_session_id)
            await websocket.close()


@chat_router.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    include_metadata: bool = False,
    agent = Depends(get_voice_agent)
) -> ConversationHistoryResponse:
    """
    Retrieve conversation history for a session.
    
    Returns the message history for the specified session with pagination support.
    """
    try:
        if agent is None:
            return ConversationHistoryResponse(
                success=False,
                session_id=session_id,
                messages=[],
                total_count=0,
                has_more=False,
                error="Agent not available"
            )
        
        # Get conversation history from agent
        history_result = await agent.get_conversation_history(session_id, limit + offset)
        
        if not history_result.get("success", False):
            return ConversationHistoryResponse(
                success=False,
                session_id=session_id,
                messages=[],
                total_count=0,
                has_more=False,
                error=history_result.get("error", "Failed to retrieve history")
            )
        
        all_messages = history_result.get("messages", [])
        total_count = len(all_messages)
        
        # Apply pagination
        paginated_messages = all_messages[offset:offset + limit]
        has_more = offset + limit < total_count
        
        # Convert to API message format
        api_messages = []
        for msg in paginated_messages:
            api_message = ChatMessage(
                id=msg.get("id", f"msg_{uuid.uuid4().hex[:8]}"),
                role=MessageRole(msg.get("role", "user")),
                content=msg.get("content", ""),
                timestamp=datetime.fromisoformat(msg.get("timestamp", datetime.now().isoformat())),
                metadata=msg.get("metadata", {}) if include_metadata else {}
            )
            api_messages.append(api_message)
        
        return ConversationHistoryResponse(
            success=True,
            session_id=session_id,
            messages=api_messages,
            total_count=total_count,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        return ConversationHistoryResponse(
            success=False,
            session_id=session_id,
            messages=[],
            total_count=0,
            has_more=False,
            error=str(e)
        )


@session_router.post("/", response_model=SessionResponse)
async def create_session(request: SessionRequest = None) -> SessionResponse:
    """
    Create a new conversation session.
    
    Creates a new session with optional user context and returns session information.
    """
    try:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        
        session_info = SessionInfo(
            session_id=session_id,
            user_id=request.user_id if request else None,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            message_count=0,
            active=True
        )
        
        # Store session
        _session_store[session_id] = {
            "session_id": session_id,
            "user_id": request.user_id if request else None,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
            "initial_context": request.initial_context if request else {}
        }
        
        return SessionResponse(
            success=True,
            session=session_info,
            message=f"Session {session_id} created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return SessionResponse(
            success=False,
            error=str(e)
        )


@session_router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """
    Get information about a specific session.
    
    Returns session metadata and activity information.
    """
    try:
        session_data = _session_store.get(session_id)
        
        if not session_data:
            return SessionResponse(
                success=False,
                error=f"Session {session_id} not found"
            )
        
        session_info = SessionInfo(
            session_id=session_data["session_id"],
            user_id=session_data.get("user_id"),
            created_at=session_data["created_at"],
            last_activity=session_data["last_activity"],
            message_count=session_data.get("message_count", 0),
            active=True
        )
        
        return SessionResponse(
            success=True,
            session=session_info,
            message=f"Session {session_id} information retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        return SessionResponse(
            success=False,
            error=str(e)
        )


@session_router.delete("/{session_id}", response_model=SessionResponse)
async def delete_session(
    session_id: str,
    agent = Depends(get_voice_agent)
) -> SessionResponse:
    """
    Delete a conversation session.
    
    Removes session data and conversation history.
    """
    try:
        if session_id not in _session_store:
            return SessionResponse(
                success=False,
                error=f"Session {session_id} not found"
            )
        
        # Clear agent conversation if available
        if agent:
            await agent.clear_conversation(session_id)
        
        # Remove from session store
        del _session_store[session_id]
        
        return SessionResponse(
            success=True,
            message=f"Session {session_id} deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return SessionResponse(
            success=False,
            error=str(e)
        )


@health_router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    System health check endpoint.
    
    Returns comprehensive health status of all system components.
    """
    try:
        current_time = datetime.now()
        uptime = (current_time - _start_time).total_seconds()
        
        components = []
        overall_status = HealthStatus.HEALTHY
        
        # Check agent core
        agent_health = await _check_agent_health()
        components.append(agent_health)
        if agent_health.status != HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # Check configuration system
        config_health = _check_config_health()
        components.append(config_health)
        if config_health.status != HealthStatus.HEALTHY and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # Check session store
        session_health = _check_session_health()
        components.append(session_health)
        
        # Calculate metrics
        metrics = {
            "active_sessions": len(_session_store),
            "total_sessions_created": len(_session_store),  # Simplified
            "memory_usage_mb": 0,  # Would implement actual memory monitoring
            "uptime_hours": round(uptime / 3600, 2)
        }
        
        return HealthResponse(
            status=overall_status,
            timestamp=current_time,
            version="1.0.0-dev",
            uptime_seconds=uptime,
            components=components,
            metrics=metrics
        )
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return HealthResponse(
            status=HealthStatus.UNHEALTHY,
            timestamp=datetime.now(),
            version="1.0.0-dev",
            uptime_seconds=0,
            components=[],
            metrics={}
        )


async def _check_agent_health() -> ComponentHealth:
    """Check agent core health."""
    start_time = time.time()
    
    try:
        agent = get_voice_agent()
        if agent is None:
            return ComponentHealth(
                name="agent_core",
                status=HealthStatus.UNHEALTHY,
                message="Agent not available",
                last_check=datetime.now()
            )
        
        # Try a simple operation
        model_info = agent.get_model_info()
        response_time = (time.time() - start_time) * 1000
        
        return ComponentHealth(
            name="agent_core",
            status=HealthStatus.HEALTHY,
            message="Agent core is operational",
            response_time_ms=response_time,
            last_check=datetime.now()
        )
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ComponentHealth(
            name="agent_core",
            status=HealthStatus.UNHEALTHY,
            message=f"Agent error: {str(e)}",
            response_time_ms=response_time,
            last_check=datetime.now()
        )


def _check_config_health() -> ComponentHealth:
    """Check configuration system health."""
    try:
        if CONFIG_AVAILABLE:
            # Try to load configuration
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent / "config"
            if config_path.exists():
                return ComponentHealth(
                    name="configuration",
                    status=HealthStatus.HEALTHY,
                    message="Configuration system operational",
                    response_time_ms=5.0,
                    last_check=datetime.now()
                )
        
        return ComponentHealth(
            name="configuration",
            status=HealthStatus.DEGRADED,
            message="Configuration system not fully available",
            last_check=datetime.now()
        )
        
    except Exception as e:
        return ComponentHealth(
            name="configuration",
            status=HealthStatus.UNHEALTHY,
            message=f"Configuration error: {str(e)}",
            last_check=datetime.now()
        )


def _check_session_health() -> ComponentHealth:
    """Check session store health."""
    try:
        session_count = len(_session_store)
        return ComponentHealth(
            name="session_store",
            status=HealthStatus.HEALTHY,
            message=f"Session store operational ({session_count} active sessions)",
            response_time_ms=1.0,
            last_check=datetime.now()
        )
        
    except Exception as e:
        return ComponentHealth(
            name="session_store", 
            status=HealthStatus.UNHEALTHY,
            message=f"Session store error: {str(e)}",
            last_check=datetime.now()
        )


# ===========================
# Tools Endpoints
# ===========================

@tools_router.get("/")
async def list_tools():
    """
    List all available MCP tools.
    
    Returns information about registered tools including their names,
    descriptions, and parameter schemas.
    """
    try:
        from src.mcp import get_tool_registry
        
        registry = get_tool_registry()
        tools = registry.list_tools()
        
        tool_info = []
        for tool in tools:
            tool_info.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default
                    }
                    for p in tool.parameters
                ]
            })
        
        return {
            "success": True,
            "tools": tool_info,
            "total": len(tool_info)
        }
    
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return {
            "success": False,
            "error": str(e),
            "tools": []
        }


@tools_router.get("/schemas")
async def get_tool_schemas():
    """
    Get OpenAI-compatible function calling schemas for all tools.
    
    Returns schemas that can be used with OpenAI's function calling API.
    """
    try:
        from src.mcp import get_tool_registry
        
        registry = get_tool_registry()
        schemas = registry.get_schemas()
        
        return {
            "success": True,
            "schemas": schemas,
            "total": len(schemas)
        }
    
    except Exception as e:
        logger.error(f"Error getting schemas: {e}")
        return {
            "success": False,
            "error": str(e),
            "schemas": []
        }


@tools_router.post("/execute/{tool_name}")
async def execute_tool(tool_name: str, parameters: Dict[str, Any]):
    """
    Manually execute a specific tool with parameters.
    
    This endpoint allows direct tool invocation for testing and debugging.
    In normal operation, tools are called automatically by the LLM.
    """
    try:
        from src.mcp import get_tool_registry
        
        registry = get_tool_registry()
        result = await registry.execute(tool_name, **parameters)
        
        return {
            "success": True,
            "tool": tool_name,
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {
            "success": False,
            "tool": tool_name,
            "error": str(e)
        }