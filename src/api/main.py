"""
FastAPI Main Application

Main FastAPI application setup with CORS, middleware, and route registration.
This serves as the entry point for the Voice Agent API service.
"""

import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from .routes import chat_router, session_router, health_router, tools_router, rag_router, set_voice_agent
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
    try:
        import os
        from config.settings import get_config
        app.state.config = get_config()
        logger.info("✅ Configuration loaded and cached in app.state")
        
        # 设置 API Keys 到环境变量（如果配置中有）
        if hasattr(app.state.config, 'security') and hasattr(app.state.config.security, 'api_keys'):
            api_keys = app.state.config.security.api_keys
            if api_keys:
                os.environ['API_KEYS'] = ','.join(api_keys)
                logger.info(f"✅ API keys loaded from config: {len(api_keys)} key(s)")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise
    
    # Initialize MCP tools
    try:
        from mcp.init_tools import initialize_default_tools
        # 🔧 Pass config to tools for Tavily API integration
        config_dict = app.state.config.model_dump() if hasattr(app.state.config, 'model_dump') else {}
        registered_tools = initialize_default_tools(config=config_dict)
        logger.info(f"Initialized {len(registered_tools)} MCP tools: {', '.join(registered_tools)}")
    except Exception as e:
        logger.warning(f"Could not initialize MCP tools: {e}")
    
    # Initialize voice agent
    try:
        # Import with fallback handling
        try:
            from agent.graph import create_voice_agent
            agent = create_voice_agent()  # 移除 environment 参数，现在从 .env 自动加载
            set_voice_agent(agent)
            logger.info("Voice agent initialized successfully")
            
            # Initialize conversation service
            try:
                from services.conversation_service import initialize_conversation_service
                from .voice_routes import get_stt_service, get_tts_streaming_service
                
                stt_service = get_stt_service()
                tts_service = get_tts_streaming_service()
                
                # Initialize conversation service (will be used by routes)
                _ = initialize_conversation_service(
                    agent=agent,
                    stt_service=stt_service,
                    tts_service=tts_service
                )
                logger.info("Conversation service initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize conversation service: {e}")
                logger.info("Conversation endpoints will not be available")
                
        except Exception as e:
            logger.warning(f"Could not initialize voice agent: {e}")
            logger.info("API will run in degraded mode without agent functionality")
    except ImportError:
        logger.warning("Agent modules not available - running in mock mode")
    
    # 初始化 Session Manager（支持自动降级）
    try:
        from utils.session_manager import HybridSessionManager
        from database.repositories import ConversationRepository
        from database.connection import init_db, create_tables, get_db_engine
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
        from config.settings import ConfigManager
        
        # 加载配置
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # 尝试初始化数据库
        db_engine = None
        if config.database.enabled:
            logger.info("🔌 Attempting to connect to database...")
            db_engine = await init_db(config.database)
            
            if db_engine:
                # 创建表
                try:
                    await create_tables()
                    logger.info("✅ Database tables created/verified")
                except Exception as e:
                    logger.warning(f"⚠️ Table creation warning: {e}")
        
        # 初始化 Session Manager
        if db_engine:
            # 数据库可用，使用混合模式
            async_session_maker = async_sessionmaker(
                db_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            db_session = async_session_maker()
            conversation_repo = ConversationRepository(db_session)
            
            app.state.session_manager = HybridSessionManager(
                conversation_repo=conversation_repo,
                memory_limit=20,
                ttl_hours=24,
                enable_database=True
            )
            
            app.state.db_engine = db_engine
            app.state.db_session = db_session
            logger.info("✅ SessionManager initialized (memory + database)")
        else:
            # 数据库不可用，使用纯内存模式
            app.state.session_manager = HybridSessionManager(
                conversation_repo=None,
                memory_limit=20,
                ttl_hours=24,
                enable_database=False
            )
            logger.info("✅ SessionManager initialized (memory-only mode)")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize session manager: {e}")
        logger.warning("⚠️ Using fallback session manager")
        
        # 最后的降级方案：纯内存管理器（使用别名 SessionHistoryManager）
        try:
            from utils.session_manager import SessionHistoryManager
            app.state.session_manager = SessionHistoryManager(max_history=20, ttl_hours=24)
            logger.info("✅ SessionManager initialized (fallback mode)")
        except Exception as fallback_error:
            logger.error(f"Failed to initialize fallback session manager: {fallback_error}")
            raise
    
    logger.info("Voice Agent API service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Voice Agent API service...")
    
    # 清理数据库资源
    try:
        # 关闭数据库 session
        if hasattr(app.state, 'db_session'):
            await app.state.db_session.close()
            logger.info("✅ Database session closed")
        
        # 关闭数据库引擎
        if hasattr(app.state, 'db_engine'):
            await app.state.db_engine.dispose()
            logger.info("✅ Database engine disposed")
            
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