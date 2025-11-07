"""
Configuration management for the voice agent system.

This module handles loading configuration from environment variables (.env file).
"""

import logging
from pathlib import Path
from typing import Optional
from pydantic import ValidationError

from .models import VoiceAgentConfig


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


def load_config(env_file: Optional[Path] = None) -> VoiceAgentConfig:
    """
    Load configuration from environment variables.

    Args:
        env_file: Path to .env file. Defaults to .env in project root.

    Returns:
        Validated configuration object

    Raises:
        ConfigurationError: If configuration loading or validation fails

    Note:
        不再使用全局单例模式。配置应该在应用启动时加载并存储到 app.state。
        使用 core.dependencies.get_config() 通过依赖注入获取配置。
    """
    env_file = env_file or Path(__file__).parent.parent.parent / ".env"

    try:
        # Pydantic Settings automatically loads from .env
        config = VoiceAgentConfig()

        logger.info("Configuration loaded successfully")
        logger.info(f"  Environment: {config.environment}")
        logger.info(f"  LLM Provider: {config.llm.provider}")
        logger.info(f"  LLM Base URL: {config.llm.base_url}")
        logger.info(f"  Default Model: {config.llm.models.default}")
        logger.info(f"  API Host: {config.api.host}:{config.api.port}")

        return config

    except ValidationError as e:
        error_msg = f"Configuration validation failed: {e}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg) from e
    except Exception as e:
        error_msg = f"Failed to load configuration: {str(e)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg) from e


# 向后兼容的辅助函数（将被弃用）
def get_config() -> VoiceAgentConfig:
    """
    [已弃用] 获取配置实例

    警告：此函数仅用于向后兼容，未来版本将移除。
    请使用 core.dependencies.get_config() 通过依赖注入获取配置。

    Returns:
        VoiceAgentConfig 实例
    """
    import warnings
    warnings.warn(
        "config.settings.get_config() is deprecated. "
        "Use core.dependencies.get_config() with dependency injection instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return load_config()

