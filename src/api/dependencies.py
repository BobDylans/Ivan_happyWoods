"""
API Dependencies and Caching

统一的依赖注入和缓存管理，避免重复初始化服务实例。

优化说明:
- 使用 lru_cache 缓存昂贵的对象创建
- 集中管理所有依赖，便于维护和测试
- 减少内存占用和初始化时间
"""

import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 配置缓存
# ============================================================================

@lru_cache(maxsize=1)
def get_config_cached():
    """
    获取缓存的配置管理器实例
    
    使用LRU缓存确保配置只加载一次，避免重复的文件读取和解析。
    
    Returns:
        ConfigManager实例
    """
    from config.settings import get_config
    logger.debug("Loading configuration (cached)")
    return get_config()


# ============================================================================
# MCP工具注册表缓存
# ============================================================================

@lru_cache(maxsize=1)
def get_tool_registry_cached():
    """
    获取缓存的MCP工具注册表实例
    
    Returns:
        ToolRegistry实例
    """
    from mcp import get_tool_registry
    logger.debug("Getting tool registry (cached)")
    return get_tool_registry()


# ============================================================================
# TTS服务缓存
# ============================================================================

_tts_service_cache: Optional[object] = None
_tts_streaming_cache: Optional[object] = None


def get_tts_service_cached(voice: str = "x5_lingxiaoxuan_flow"):
    """
    获取缓存的TTS服务实例
    
    Args:
        voice: 发音人（用于区分不同配置）
    
    Returns:
        IFlytekTTSService实例
    """
    global _tts_service_cache
    
    if _tts_service_cache is None:
        from services.voice.tts_simple import IFlytekTTSService
        config = get_config_cached()
        
        _tts_service_cache = IFlytekTTSService(
            appid=config.speech.tts.appid,
            api_key=config.speech.tts.api_key,
            api_secret=config.speech.tts.api_secret,
            voice=voice,
            speed=config.speech.tts.speed,
            volume=config.speech.tts.volume,
            pitch=config.speech.tts.pitch
        )
        logger.debug("TTS service initialized (cached)")
    
    return _tts_service_cache


def get_tts_streaming_cached(voice: str = "x5_lingxiaoxuan_flow"):
    """
    获取缓存的流式TTS服务实例
    
    Args:
        voice: 发音人
    
    Returns:
        IFlytekTTSStreamingService实例
    """
    global _tts_streaming_cache
    
    if _tts_streaming_cache is None:
        from services.voice.tts_streaming import IFlytekTTSStreamingService
        config = get_config_cached()
        
        _tts_streaming_cache = IFlytekTTSStreamingService(
            appid=config.speech.tts.appid,
            api_key=config.speech.tts.api_key,
            api_secret=config.speech.tts.api_secret,
            voice=voice,
            speed=config.speech.tts.speed,
            volume=config.speech.tts.volume,
            pitch=config.speech.tts.pitch
        )
        logger.debug("TTS streaming service initialized (cached)")
    
    return _tts_streaming_cache


# ============================================================================
# STT服务缓存
# ============================================================================

_stt_service_cache: Optional[object] = None


def get_stt_service_cached():
    """
    获取缓存的STT服务实例
    
    Returns:
        IFlytekSTTService实例
    """
    global _stt_service_cache
    
    if _stt_service_cache is None:
        from services.voice.stt_simple import IFlytekSTTService, STTConfig
        config = get_config_cached()
        
        stt_config = STTConfig(
            appid=config.speech.stt.appid,
            api_key=config.speech.stt.api_key,
            api_secret=config.speech.stt.api_secret,
            base_url="wss://iat.cn-huabei-1.xf-yun.com/v1",
            domain="slm",
            language="mul_cn",
            accent="mandarin"
        )
        
        _stt_service_cache = IFlytekSTTService(stt_config)
        logger.debug("STT service initialized (cached)")
    
    return _stt_service_cache


# ============================================================================
# 缓存管理工具
# ============================================================================

def clear_all_caches():
    """
    清除所有缓存（用于测试或重新加载）
    """
    global _tts_service_cache, _tts_streaming_cache, _stt_service_cache
    
    _tts_service_cache = None
    _tts_streaming_cache = None
    _stt_service_cache = None
    
    # 清除LRU缓存
    get_config_cached.cache_clear()
    get_tool_registry_cached.cache_clear()
    
    logger.info("All caches cleared")


def get_cache_info():
    """
    获取缓存状态信息
    
    Returns:
        dict: 包含所有缓存的hit/miss统计
    """
    return {
        "config_cache": get_config_cached.cache_info()._asdict(),
        "tool_registry_cache": get_tool_registry_cached.cache_info()._asdict(),
        "tts_cached": _tts_service_cache is not None,
        "tts_streaming_cached": _tts_streaming_cache is not None,
        "stt_cached": _stt_service_cache is not None,
    }

