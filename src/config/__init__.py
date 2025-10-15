"""
Configuration package for the voice agent system.

This package provides configuration management with support for:
- YAML configuration files
- Environment variable overrides
- Configuration validation
- Hot-reloading in development
"""

from .models import (
    VoiceAgentConfig,
    APIConfig,
    LLMConfig,
    LLMModels,
    SpeechConfig,
    TTSConfig,
    STTConfig,
    ToolsConfig,
    ToolConfig,
    SessionConfig,
    LoggingConfig,
    SecurityConfig,
    LLMProvider,
    TTSProvider,
    STTProvider,
    LogLevel,
)

from .settings import (
    ConfigManager,
    ConfigurationError,
    get_config,
    get_config_manager,
    load_config,
    reload_config_if_changed,
)

__all__ = [
    # Configuration models
    "VoiceAgentConfig",
    "APIConfig",
    "LLMConfig",
    "LLMModels",
    "SpeechConfig",
    "TTSConfig",
    "STTConfig",
    "ToolsConfig",
    "ToolConfig",
    "SessionConfig",
    "LoggingConfig",
    "SecurityConfig",
    
    # Enums
    "LLMProvider",
    "TTSProvider",
    "STTProvider",
    "LogLevel",
    
    # Configuration management
    "ConfigManager",
    "ConfigurationError",
    "get_config",
    "get_config_manager",
    "load_config",
    "reload_config_if_changed",
]