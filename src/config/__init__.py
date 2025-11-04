"""
Configuration package for the voice agent system.

This package provides configuration management with support for:
- .env file configuration
- Environment variable parsing
- Configuration validation
- Simplified pure .env approach (no YAML)
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
    DatabaseConfig,
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
    reload_config,
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
    "DatabaseConfig",
    
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
    "reload_config",
]