"""
Configuration data models for the voice agent system.

This module defines Pydantic models for all configuration sections,
providing validation, type safety, and documentation for settings.
"""

from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import os


class LogLevel(str, Enum):
    """Available logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    CUSTOM = "custom"
    OLLAMA = "ollama"  # 本地 Ollama 模型


class TTSProvider(str, Enum):
    """Supported TTS providers."""
    OPENAI = "openai"
    AZURE = "azure"
    ELEVENLABS = "elevenlabs"
    IFLYTEK = "iflytek"
    CUSTOM = "custom"


class STTProvider(str, Enum):
    """Supported STT providers."""
    OPENAI = "openai"
    AZURE = "azure"
    GOOGLE = "google"
    IFLYTEK = "iflytek"
    CUSTOM = "custom"


class APIConfig(BaseModel):
    """API server configuration."""
    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, ge=1, le=65535, description="API server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    workers: int = Field(default=1, ge=1, description="Number of worker processes")
    
    @validator("host")
    def validate_host(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Host must be a non-empty string")
        return v


class LLMModels(BaseModel):
    """LLM model configuration for different use cases."""
    
    default: str = Field(default="gpt-5-mini", description="Default model for general use")
    fast: str = Field(default="gpt-5-nano", description="Fast model for quick responses")
    creative: str = Field(default="gpt-5-mini", description="Creative model for complex tasks")
    
    @validator("default", "fast", "creative")
    def validate_model(cls, v):
        """验证模型名称 - 支持 OpenAI、Claude、Ollama 格式"""
        # Ollama 模型格式: name:tag (如 qwen3:4b, llama3:8b)
        if ":" in v:
            # 检测是否为 Ollama 模型（包含常见模型名）
            ollama_keywords = ["qwen", "llama", "deepseek", "mistral", "phi", "gemma", "codellama"]
            if any(keyword in v.lower() for keyword in ollama_keywords):
                return v  # Ollama 模型，跳过验证
        
        # Claude 模型验证 (支持所有 Claude 模型)
        if v.startswith("claude-"):
            return v  # Claude 模型，允许通过
        
        # OpenAI GPT-5 系列模型验证
        allowed_models = [
            "gpt-5-mini",
            "gpt-5-mini-2025-08-07", 
            "gpt-5-nano",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ]
        if v in allowed_models:
            return v
        
        # 其他通用模型名称（放宽验证）
        # 如果模型名包含常见前缀，也允许通过
        common_prefixes = ["gpt-", "text-", "davinci", "curie", "babbage", "ada"]
        if any(v.startswith(prefix) for prefix in common_prefixes):
            return v
            
        # 如果都不匹配，报错
        raise ValueError(
            f"Model '{v}' is not recognized. "
            f"Supported formats: OpenAI models (gpt-*), Claude models (claude-*), "
            f"or Ollama models (name:tag format, e.g., qwen3:4b)"
        )
        return v


class LLMConfig(BaseModel):
    """LLM service configuration."""
    provider: LLMProvider = Field(default=LLMProvider.OPENAI, description="LLM provider")
    api_key: str = Field(..., description="API key for LLM service")
    base_url: str = Field(default="https://api.openai.com/v1", description="API base URL")
    models: LLMModels = Field(default_factory=LLMModels, description="Model configurations")
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")
    max_tokens: int = Field(default=8192, ge=1, description="Maximum tokens per response")  # 🆕 提升到 8192
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Response creativity")
    
    @validator("api_key")
    def validate_api_key(cls, v, values):
        """验证 API Key - Ollama 可以使用占位符"""
        # Ollama 不需要真实的 API Key
        provider = values.get("provider")
        if provider == LLMProvider.OLLAMA:
            return v or "ollama"  # 使用占位符
        
        # 其他提供商需要真实的 API Key
        if not v or len(v) < 10:
            raise ValueError("API key must be at least 10 characters long")
        return v
    
    @validator("base_url")
    def validate_base_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v


class TTSConfig(BaseModel):
    """Text-to-speech configuration."""
    provider: TTSProvider = Field(default=TTSProvider.IFLYTEK, description="TTS provider")
    api_key: Optional[str] = Field(default=None, description="API key for TTS service")
    base_url: Optional[str] = Field(default=None, description="TTS API base URL")
    voice: str = Field(default="x5_lingxiaoxuan_flow", description="Voice selection")
    speed: float = Field(default=50, ge=0, le=100, description="Speech speed (0-100 for iFlytek, 0.25-4.0 for OpenAI)")
    format: str = Field(default="mp3", description="Audio output format")
    
    # iFlytek specific
    appid: Optional[str] = Field(default=None, description="iFlytek APPID")
    api_secret: Optional[str] = Field(default=None, description="iFlytek API Secret")
    volume: int = Field(default=50, ge=0, le=100, description="iFlytek volume (0-100)")
    pitch: int = Field(default=50, ge=0, le=100, description="iFlytek pitch (0-100)")


class STTConfig(BaseModel):
    """Speech-to-text configuration."""
    provider: STTProvider = Field(default=STTProvider.IFLYTEK, description="STT provider")
    api_key: Optional[str] = Field(default=None, description="API key for STT service")
    base_url: Optional[str] = Field(default=None, description="STT API base URL")
    language: str = Field(default="mul_cn", description="Primary language code")
    model: str = Field(default="whisper-1", description="STT model to use")
    
    # iFlytek specific
    appid: Optional[str] = Field(default=None, description="iFlytek APPID")
    api_secret: Optional[str] = Field(default=None, description="iFlytek API Secret")
    domain: str = Field(default="slm", description="iFlytek domain (slm/iat)")
    accent: str = Field(default="mandarin", description="iFlytek accent")


class SpeechConfig(BaseModel):
    """Combined speech processing configuration."""
    tts: TTSConfig = Field(default_factory=TTSConfig, description="TTS settings")
    stt: STTConfig = Field(default_factory=STTConfig, description="STT settings")


class ToolConfig(BaseModel):
    """Individual tool configuration."""
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    api_key: Optional[str] = Field(default=None, description="Tool-specific API key")
    base_url: Optional[str] = Field(default=None, description="Tool-specific base URL")
    timeout: int = Field(default=10, ge=1, description="Tool timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")


class ToolsConfig(BaseModel):
    """MCP tools configuration."""
    enabled: List[str] = Field(
        default=["search_tool", "calculator", "time_tool"],
        description="List of enabled tools"
    )
    search_tool: ToolConfig = Field(default_factory=ToolConfig, description="Search tool config")
    calculator: ToolConfig = Field(default_factory=ToolConfig, description="Calculator config")
    time_tool: ToolConfig = Field(default_factory=ToolConfig, description="Time tool config")
    image_generator: ToolConfig = Field(default_factory=ToolConfig, description="Image gen config")
    document_analyzer: ToolConfig = Field(default_factory=ToolConfig, description="Doc analysis config")


class DatabaseConfig(BaseModel):
    """Database configuration for PostgreSQL persistence."""
    enabled: bool = Field(default=False, description="Enable database persistence")
    type: str = Field(default="postgresql", description="Database type")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database: str = Field(default="voice_agent", description="Database name")
    user: str = Field(default="agent_user", description="Database user")
    password: str = Field(default="changeme123", description="Database password")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=100, description="Max pool overflow")
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Database password must be at least 8 characters long")
        return v


class SessionConfig(BaseModel):
    """Session management configuration."""
    timeout_minutes: int = Field(default=30, ge=1, description="Session timeout in minutes")
    max_history: int = Field(default=50, ge=1, description="Maximum conversation history length")
    cleanup_interval: int = Field(default=300, ge=60, description="Cleanup interval in seconds")
    storage_type: str = Field(default="memory", description="Session storage type (memory/database/redis)")
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL if using Redis")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    format: str = Field(default="standard", description="Log format (standard/json/detailed)")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_file_size: str = Field(default="10MB", description="Maximum log file size")
    backup_count: int = Field(default=5, ge=0, description="Number of backup log files")


class SecurityConfig(BaseModel):
    """Security and authentication configuration."""
    api_keys: List[str] = Field(default=[], description="Valid API keys for authentication")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: List[str] = Field(default=["GET", "POST"], description="CORS allowed methods")
    rate_limit_per_minute: int = Field(default=60, ge=1, description="Rate limit per minute")


class VoiceAgentConfig(BaseSettings):
    """Main configuration model for the voice agent system."""
    
    # Core service configurations
    api: APIConfig = Field(default_factory=APIConfig, description="API server configuration")
    llm: LLMConfig = Field(..., description="LLM service configuration")
    speech: SpeechConfig = Field(default_factory=SpeechConfig, description="Speech processing config")
    tools: ToolsConfig = Field(default_factory=ToolsConfig, description="MCP tools configuration")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database configuration")
    session: SessionConfig = Field(default_factory=SessionConfig, description="Session management config")
    
    # System configurations
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")
    
    # Environment and metadata
    environment: str = Field(default="development", description="Environment name")
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "VOICE_AGENT_"
        env_nested_delimiter = "__"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量
        
    @validator("environment")
    def validate_environment(cls, v):
        allowed_envs = ["development", "testing", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v


# Environment variable mapping for quick access
ENV_VAR_MAPPING = {
    # API Configuration
    "VOICE_AGENT_API__HOST": "api.host",
    "VOICE_AGENT_API__PORT": "api.port",
    
    # LLM Configuration
    "VOICE_AGENT_LLM__API_KEY": "llm.api_key",
    "VOICE_AGENT_LLM__BASE_URL": "llm.base_url",
    "VOICE_AGENT_LLM__PROVIDER": "llm.provider",
    
    # iFlytek Voice Configuration (Phase 2B)
    "IFLYTEK_APPID": "speech.stt.appid",
    "IFLYTEK_APIKEY": "speech.stt.api_key",
    "IFLYTEK_APISECRET": "speech.stt.api_secret",
    "IFLYTEK_TTS_APPID": "speech.tts.appid",
    "IFLYTEK_TTS_APIKEY": "speech.tts.api_key",
    "IFLYTEK_TTS_APISECRET": "speech.tts.api_secret",
    
    # Session Configuration
    "VOICE_AGENT_SESSION__TIMEOUT_MINUTES": "session.timeout_minutes",
    "VOICE_AGENT_SESSION__STORAGE_TYPE": "session.storage_type",
    "VOICE_AGENT_SESSION__REDIS_URL": "session.redis_url",
    
    # Logging Configuration
    "VOICE_AGENT_LOG_LEVEL": "logging.level",
    "VOICE_AGENT_DEBUG": "debug",
    
    # Environment
    "VOICE_AGENT_ENVIRONMENT": "environment",
}