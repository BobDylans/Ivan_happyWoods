"""
Core Module

核心依赖注入和应用状态管理
"""

from .dependencies import (
    # 依赖注入函数
    get_config,
    get_voice_agent,
    get_db_session,
    get_db_engine,
    get_session_manager,
    get_stream_manager,
    get_tool_registry,
    get_stt_service,
    get_tts_service,
    get_conversation_service,
    get_rag_service,
    # 应用状态管理
    AppState,
)

__all__ = [
    # 依赖注入
    'get_config',
    'get_voice_agent',
    'get_db_session',
    'get_db_engine',
    'get_session_manager',
    'get_stream_manager',
    'get_tool_registry',
    'get_stt_service',
    'get_tts_service',
    'get_conversation_service',
    'get_rag_service',
    # 应用状态
    'AppState',
]
