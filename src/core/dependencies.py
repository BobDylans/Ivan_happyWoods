"""
Core Dependencies Module

统一的依赖注入系统，完全替代全局变量。
使用 FastAPI 的 app.state 和 Depends() 模式。

设计原则：
1. 所有服务通过 app.state 存储（应用级单例）
2. 使用 Depends() 进行依赖注入
3. 支持测试时的 mock
4. 清晰的生命周期管理
"""

import logging
from typing import Optional, AsyncGenerator
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from .observability import Observability

logger = logging.getLogger(__name__)


# ============================================================================
# 配置管理
# ============================================================================

def get_config(request: Request):
    """
    获取配置管理器实例

    Args:
        request: FastAPI Request 对象

    Returns:
        VoiceAgentConfig 实例

    Example:
        @app.get("/info")
        async def info(config = Depends(get_config)):
            return {"provider": config.llm.provider}
    """
    if not hasattr(request.app.state, 'config'):
        raise RuntimeError("Configuration not initialized. Check lifespan in main.py")
    return request.app.state.config


# ============================================================================
# Agent 管理
# ============================================================================

def get_voice_agent(request: Request):
    """
    获取 VoiceAgent 实例

    Args:
        request: FastAPI Request 对象

    Returns:
        VoiceAgent 实例或 None（如果未初始化）

    Example:
        @app.post("/chat")
        async def chat(
            message: str,
            agent = Depends(get_voice_agent)
        ):
            result = await agent.process_message(message)
            return result
    """
    if not hasattr(request.app.state, 'voice_agent'):
        logger.warning("Voice agent not available")
        return None
    return request.app.state.voice_agent


# ============================================================================
# 数据库会话管理（改进版：每个请求一个会话）
# ============================================================================

async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（每个请求独立会话）

    Args:
        request: FastAPI Request 对象

    Yields:
        AsyncSession 实例

    Example:
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(User))
            return result.scalars().all()

    重要：使用上下文管理器确保会话正确关闭
    """
    if not hasattr(request.app.state, 'db_session_factory'):
        raise RuntimeError("Database not initialized")

    session_factory = request.app.state.db_session_factory

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_engine(request: Request) -> AsyncEngine:
    """
    获取数据库引擎（仅用于特殊情况）

    Args:
        request: FastAPI Request 对象

    Returns:
        AsyncEngine 实例
    """
    if not hasattr(request.app.state, 'db_engine'):
        raise RuntimeError("Database engine not initialized")
    return request.app.state.db_engine


# ============================================================================
# 会话管理（Session Manager）
# ============================================================================

def get_session_manager(request: Request):
    """
    获取会话管理器实例

    Args:
        request: FastAPI Request 对象

    Returns:
        HybridSessionManager 实例

    Example:
        @app.get("/history/{session_id}")
        async def get_history(
            session_id: str,
            manager = Depends(get_session_manager)
        ):
            history = await manager.get_history(session_id)
            return {"messages": history}
    """
    if not hasattr(request.app.state, 'session_manager'):
        raise RuntimeError("Session manager not initialized")
    return request.app.state.session_manager


# ============================================================================
# 流管理器（Stream Manager）
# ============================================================================

def get_stream_manager(request: Request):
    """
    获取流管理器实例

    Args:
        request: FastAPI Request 对象

    Returns:
        StreamTaskManager 实例

    Example:
        @app.websocket("/ws")
        async def websocket_endpoint(
            websocket: WebSocket,
            stream_mgr = Depends(get_stream_manager)
        ):
            await stream_mgr.register_task(session_id, task)
    """
    if not hasattr(request.app.state, 'stream_manager'):
        # 惰性初始化
        from api.stream_manager import StreamTaskManager
        request.app.state.stream_manager = StreamTaskManager()
        logger.info("Stream manager initialized on-demand")
    return request.app.state.stream_manager


# ============================================================================
# MCP 工具注册表
# ============================================================================

def get_tool_registry(request: Request):
    """
    获取 MCP 工具注册表

    Args:
        request: FastAPI Request 对象

    Returns:
        ToolRegistry 实例

    Example:
        @app.get("/tools")
        async def list_tools(registry = Depends(get_tool_registry)):
            return {"tools": registry.list_tool_names()}
    """
    if not hasattr(request.app.state, 'tool_registry'):
        raise RuntimeError("Tool registry not initialized")
    return request.app.state.tool_registry


# ============================================================================
# Observability
# ============================================================================

def get_observability(request: Request) -> Observability:
    """
    获取 Observability 实例

    Args:
        request: FastAPI Request 对象

    Returns:
        Observability 实例
    """
    if not hasattr(request.app.state, 'observability'):
        raise RuntimeError("Observability tracker not initialized")
    return request.app.state.observability


# ============================================================================
# 语音服务（STT/TTS）
# ============================================================================

def get_stt_service(request: Request):
    """
    获取 STT 服务实例

    Args:
        request: FastAPI Request 对象

    Returns:
        IFlyTekSTTService 实例

    Example:
        @app.post("/stt")
        async def speech_to_text(
            audio: UploadFile,
            stt = Depends(get_stt_service)
        ):
            result = await stt.recognize(audio_data)
            return {"text": result.text}
    """
    if not hasattr(request.app.state, 'stt_service'):
        # 惰性初始化
        from services.voice.stt import IFlyTekSTTService, STTConfig
        config = get_config(request)

        stt_config = STTConfig(
            appid=config.speech.stt.appid,
            api_key=config.speech.stt.api_key,
            api_secret=config.speech.stt.api_secret,
            base_url=config.speech.stt.base_url or "wss://iat.cn-huabei-1.xf-yun.com/v1",
            domain=config.speech.stt.domain or "slm",
            language=config.speech.stt.language or "mul_cn",
            accent=config.speech.stt.accent or "mandarin"
        )

        request.app.state.stt_service = IFlyTekSTTService(stt_config)
        logger.info("STT service initialized on-demand")

    return request.app.state.stt_service


def get_tts_service(request: Request):
    """
    获取 TTS 流式服务实例

    Args:
        request: FastAPI Request 对象

    Returns:
        IFlytekTTSStreamingService 实例

    Example:
        @app.post("/tts")
        async def text_to_speech(
            text: str,
            tts = Depends(get_tts_service)
        ):
            async def audio_generator():
                async for chunk in tts.synthesize_stream(text):
                    yield chunk
            return StreamingResponse(audio_generator())
    """
    if not hasattr(request.app.state, 'tts_service'):
        # 惰性初始化
        from services.voice.tts import IFlytekTTSStreamingService
        config = get_config(request)

        request.app.state.tts_service = IFlytekTTSStreamingService(
            appid=config.speech.tts.appid,
            api_key=config.speech.tts.api_key,
            api_secret=config.speech.tts.api_secret,
            voice=config.speech.tts.voice,
            speed=config.speech.tts.speed,
            volume=config.speech.tts.volume,
            pitch=config.speech.tts.pitch
        )
        logger.info("TTS service initialized on-demand")

    return request.app.state.tts_service


# ============================================================================
# 对话服务（Conversation Service）
# ============================================================================

def get_conversation_service(request: Request):
    """
    获取对话服务实例

    Args:
        request: FastAPI Request 对象

    Returns:
        ConversationService 实例

    Example:
        @app.post("/conversation")
        async def conversation(
            text: str,
            service = Depends(get_conversation_service)
        ):
            result = await service.process_conversation(text=text)
            return result
    """
    if not hasattr(request.app.state, 'conversation_service'):
        # 惰性初始化
        from services.conversation_service import ConversationService

        agent = get_voice_agent(request)
        stt = get_stt_service(request)
        tts = get_tts_service(request)

        if not agent:
            raise RuntimeError("Cannot initialize conversation service without agent")

        request.app.state.conversation_service = ConversationService(
            agent=agent,
            stt_service=stt,
            tts_service=tts
        )
        logger.info("Conversation service initialized on-demand")

    return request.app.state.conversation_service


# ============================================================================
# RAG 服务
# ============================================================================

def get_rag_service(request: Request):
    """
    获取 RAG 服务实例

    Args:
        request: FastAPI Request 对象

    Returns:
        RAGService 实例或 None

    Example:
        @app.post("/rag/query")
        async def rag_query(
            query: str,
            rag = Depends(get_rag_service)
        ):
            if rag is None:
                raise HTTPException(503, "RAG not enabled")
            results = await rag.retrieve(query)
            return results
    """
    if not hasattr(request.app.state, 'rag_service'):
        config = get_config(request)

        if not config.rag.enabled:
            logger.info("RAG is disabled in configuration")
            return None

        try:
            from rag.service import RAGService
            request.app.state.rag_service = RAGService(config.rag)
            logger.info("RAG service initialized on-demand")
        except ImportError:
            logger.warning("RAG service not available (missing dependencies)")
            return None

    return request.app.state.rag_service


# ============================================================================
# 应用状态辅助函数（用于 main.py 中的初始化）
# ============================================================================

class AppState:
    """
    应用状态容器，用于在 lifespan 中初始化服务

    这是一个辅助类，提供清晰的接口来管理应用状态。
    """

    @staticmethod
    def set_config(app, config):
        """设置配置实例"""
        app.state.config = config
        logger.info("✅ Config initialized in app.state")

    @staticmethod
    def set_voice_agent(app, agent):
        """设置 VoiceAgent 实例"""
        app.state.voice_agent = agent
        logger.info("✅ Voice agent initialized in app.state")

    @staticmethod
    def set_database(app, engine, session_factory):
        """设置数据库引擎和会话工厂"""
        app.state.db_engine = engine
        app.state.db_session_factory = session_factory
        logger.info("✅ Database initialized in app.state")

    @staticmethod
    def set_session_manager(app, manager):
        """设置会话管理器"""
        app.state.session_manager = manager
        logger.info("✅ Session manager initialized in app.state")

    @staticmethod
    def set_stream_manager(app, manager):
        """设置流管理器"""
        app.state.stream_manager = manager
        logger.info("✅ Stream manager initialized in app.state")

    @staticmethod
    def set_tool_registry(app, registry):
        """设置工具注册表"""
        app.state.tool_registry = registry
        logger.info("✅ Tool registry initialized in app.state")

    @staticmethod
    def set_observability(app, observer: Observability):
        """设置 Observability 实例"""
        app.state.observability = observer
        logger.info("✅ Observability initialized in app.state")

    @staticmethod
    def set_stt_service(app, service):
        """设置 STT 服务"""
        app.state.stt_service = service
        logger.info("✅ STT service initialized in app.state")

    @staticmethod
    def set_tts_service(app, service):
        """设置 TTS 服务"""
        app.state.tts_service = service
        logger.info("✅ TTS service initialized in app.state")

    @staticmethod
    def set_conversation_service(app, service):
        """设置对话服务"""
        app.state.conversation_service = service
        logger.info("✅ Conversation service initialized in app.state")

    @staticmethod
    def cleanup(app):
        """清理所有状态（用于测试）"""
        for attr in ['config', 'voice_agent', 'db_engine', 'db_session_factory',
                     'session_manager', 'stream_manager', 'tool_registry',
                     'stt_service', 'tts_service', 'conversation_service', 'rag_service']:
            if hasattr(app.state, attr):
                delattr(app.state, attr)
        logger.info("🧹 App state cleaned up")
