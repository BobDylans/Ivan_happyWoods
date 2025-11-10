"""
FastAPI Main Application

Main FastAPI application setup with CORS, middleware, and route registration.
This serves as the entry point for the Voice Agent API service.
"""

import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Callable, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from .routes import chat_router, session_router, health_router, tools_router, rag_router
from .voice_routes import voice_router
from .conversation_routes import conversation_router
from .auth_routes import router as auth_router  # 🔧 添加认证路由
from .session_routes import router as session_management_router  # 🔧 添加会话管理路由 (Phase 3B)
from .models import ErrorResponse
from .auth import APIKeyMiddleware
from .middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware
)

# 使用新的依赖注入系统
from core.dependencies import AppState
from core.observability import Observability

# fastAPI中提到的中间件相当于java中的过滤器
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Voice Agent API service...")
    # 重点是将MCP工具，agent等一系列功能一起初始化
    # 🚀 优化1: 集中配置管理 - 一次性加载配置到app.state
    observability: Optional[Observability] = None
    try:
        import os
        from config.settings import load_config
        config = load_config()
        AppState.set_config(app, config)
        logger.info("✅ Configuration loaded and cached in app.state")

        # 初始化 Observability 跟踪器
        observability = Observability()
        AppState.set_observability(app, observability)

        # 设置 API Keys 到环境变量（如果配置中有）
        if hasattr(config, 'security') and hasattr(config.security, 'api_keys'):
            api_keys = config.security.api_keys
            if api_keys:
                os.environ['API_KEYS'] = ','.join(api_keys)
                logger.info(f"✅ API keys loaded from config: {len(api_keys)} key(s)")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise
    tool_call_persister: Optional[Callable] = None
    # Initialize MCP tools
    try:
        from mcp.init_tools import initialize_default_tools
        from mcp.registry import ToolRegistry

        # 创建并注册 tool registry
        tool_registry = ToolRegistry()
        AppState.set_tool_registry(app, tool_registry)

        # 🔧 Pass config to tools for Tavily API integration
        config_dict = config.model_dump() if hasattr(config, 'model_dump') else {}
        registered_tools = initialize_default_tools(config=config_dict)
        logger.info(f"Initialized {len(registered_tools)} MCP tools: {', '.join(registered_tools)}")
    except Exception as e:
        logger.warning(f"Could not initialize MCP tools: {e}")

    # Initialize database
    try:
        from database.connection import init_db, create_tables

        if config.database.enabled:
            logger.info("🔌 Attempting to connect to database...")
            db_engine, db_session_factory = await init_db(config.database)

            if db_engine and db_session_factory:
                # 设置到 app.state
                AppState.set_database(app, db_engine, db_session_factory)

                # 创建表
                try:
                    await create_tables(db_engine)
                    logger.info("✅ Database tables created/verified")
                except Exception as e:
                    logger.warning(f"⚠️ Table creation warning: {e}")

                async def persist_tool_call(
                    session_id: str,
                    tool_call,
                    result,
                    execution_ms: Optional[float] = None,
                ) -> None:
                    """Persist tool call using a fresh AsyncSession."""
                    from database.repositories import ToolCallRepository  # Local import

                    async with db_session_factory() as db_session:
                        repo = ToolCallRepository(db_session)
                        if result.success and result.result:
                            payload = {"data": result.result, "success": True}
                        else:
                            payload = {"success": False, "error": result.error}

                        if not isinstance(payload.get("data"), (dict, list, str, int, float, type(None))):
                            payload["data"] = str(payload["data"])

                        await repo.save_tool_call(
                            session_id=session_id,
                            tool_name=tool_call.name,
                            parameters=tool_call.arguments,
                            result=payload,
                            execution_time_ms=int(execution_ms) if execution_ms is not None else None,
                        )
                        await db_session.commit()

                tool_call_persister = persist_tool_call
            else:
                logger.warning("⚠️ Database connection failed, will use memory-only mode")
        else:
            logger.info("📝 Database disabled in configuration, using memory-only mode")

    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        logger.info("Will continue with memory-only mode")

    # Initialize voice agent
    try:
        from agent.graph import create_voice_agent
        agent = create_voice_agent(
            config=config,
            observability=observability,
            tool_call_persister=tool_call_persister,
        )
        AppState.set_voice_agent(app, agent)
        logger.info("✅ Voice agent initialized successfully")

    except Exception as e:
        logger.warning(f"Could not initialize voice agent: {e}")
        logger.info("API will run in degraded mode without agent functionality")

    # Initialize Session Manager (supports automatic fallback)
    try:
        from utils.session_manager import HybridSessionManager

        # Check if database is available
        if hasattr(app.state, 'db_session_factory'):
            # Database available, use hybrid mode
            session_manager = HybridSessionManager(
                session_factory=app.state.db_session_factory,
                memory_limit=20,
                ttl_hours=24,
                enable_database=True
            )
            AppState.set_session_manager(app, session_manager)
            logger.info("✅ SessionManager initialized (memory + database)")
        else:
            # Database not available, use memory-only mode
            session_manager = HybridSessionManager(
                session_factory=None,
                memory_limit=20,
                ttl_hours=24,
                enable_database=False
            )
            AppState.set_session_manager(app, session_manager)
            logger.info("✅ SessionManager initialized (memory-only mode)")

    except Exception as e:
        logger.error(f"❌ Failed to initialize session manager: {e}")
        logger.warning("⚠️ Using fallback session manager")

        # Last fallback: pure memory manager
        try:
            from utils.session_manager import SessionHistoryManager
            session_manager = SessionHistoryManager(max_history=20, ttl_hours=24)
            AppState.set_session_manager(app, session_manager)
            logger.info("✅ SessionManager initialized (fallback mode)")
        except Exception as fallback_error:
            logger.error(f"Failed to initialize fallback session manager: {fallback_error}")
            raise
    
    logger.info("Voice Agent API service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Voice Agent API service...")

    # Clean up database resources
    try:
        from database.connection import close_db

        # Close database engine if available
        if hasattr(app.state, 'db_engine') and app.state.db_engine is not None:
            await close_db(app.state.db_engine)
            logger.info("✅ Database connection closed")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

    logger.info("Voice Agent API service stopped")


# 其中封装了应用的结构,
# 并且附带了说明和解释
app = FastAPI(
    title="Voice Agent API",
    description="""
    Voice Agent API provides conversational AI capabilities with tool integration.
    
    ## Features
    
    * **Chat Conversations**: Send messages and receive intelligent responses
    * **Session Management**: Create and manage conversation sessions
    * **Tool Integration**: Automatic tool calling for search, calculations, and more
    * **Health Monitoring**: System health checks and metrics
    * **Real-time Processing**: Fast response times with async processing
    
    ## Authentication
    
    API key authentication is required for all endpoints (except health checks).
    Include your API key in the `X-API-Key` header.
    
    ## Rate Limits
    
    * 100 requests per minute per API key
    * 1000 requests per hour per API key
    
    ## WebSocket Support
    
    Real-time conversation support available via WebSocket connections.
    """,
    version="1.0.0",
    contact={
        "name": "Voice Agent API Support",
        "email": "support@voiceagent.ai",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# 实现了跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（包括 file:// 协议）
    allow_credentials=False,  # 设为 False 以允许 *
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# 添加了Host验证
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "testserver", "*.voiceagent.ai"]
)

# 认证
app.add_middleware(APIKeyMiddleware)

# Security Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100, requests_per_hour=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(f"{process_time:.4f}")

    observability = getattr(request.app.state, "observability", None)
    if observability:
        observability.observe(
            "http.server.duration_ms",
            process_time * 1000,
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
        )
        observability.increment(
            "http.server.request_count",
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
        )
    return response


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracing."""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            timestamp=datetime.now(),
            request_id=getattr(request.state, "request_id", None)
        ).model_dump(mode='json')  # 使用 model_dump 确保 datetime 被正确序列化
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={"exception_type": type(exc).__name__},
            timestamp=datetime.now(),
            request_id=getattr(request.state, "request_id", None)
        ).model_dump(mode='json')  # 使用 model_dump 确保 datetime 被正确序列化
    )


# 注册路由
app.include_router(chat_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(tools_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")  # 语音服务路由
app.include_router(conversation_router, prefix="/api/v1")  # 对话服务路由
app.include_router(rag_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])  # 🔧 认证路由 (Phase 3B)
app.include_router(session_management_router)  # 🔧 会话管理路由 (Phase 3B) - prefix 已在 router 中定义


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Voice Agent API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# API Info endpoint
@app.get("/api/v1/info", tags=["Info"])
async def api_info():
    """Get API information and capabilities."""
    return {
        "name": "Voice Agent API",
        "version": "1.0.0",
        "description": "Conversational AI with tool integration",
        "capabilities": [
            "Natural language conversations",
            "Automatic tool calling",
            "Session management",
            "Multi-user support",
            "Real-time processing"
        ],
        "supported_languages": ["English"],
        "max_message_length": 4000,
        "rate_limits": {
            "requests_per_minute": 100,
            "requests_per_hour": 1000
        },
        "endpoints": {
            "chat": "/api/v1/chat",
            "sessions": "/api/v1/session",
            "health": "/api/v1/health",
            "docs": "/docs"
        }
    }


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema with additional metadata."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Voice Agent API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    # Add security to all endpoints except health
    for path, path_item in openapi_schema["paths"].items():
        if not path.startswith("/api/v1/health"):
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    operation.setdefault("security", []).append({"ApiKeyAuth": []})
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# WebSocket endpoint (placeholder for future implementation)
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time conversations."""
    await websocket.accept()
    await websocket.send_json({
        "type": "connection",
        "message": "WebSocket connection established",
        "timestamp": time.time()
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Echo back for now (would integrate with agent in full implementation)
            await websocket.send_json({
                "type": "response",
                "message": f"Received: {data.get('message', '')}",
                "timestamp": time.time()
            })
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1000)


if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )