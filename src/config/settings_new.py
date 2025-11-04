"""
Configuration management for the voice agent system.

This module handles loading configuration from environment variables (.env file).
"""

import os
import logging
from pathlib import Path
from typing import Optional
from pydantic import ValidationError
from dotenv import load_dotenv

from .models import VoiceAgentConfig


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class ConfigManager:
    """
    Configuration manager that handles loading from environment variables.
    
    Supports:
    - .env file loading
    - Environment variable parsing
    - Configuration validation
    - Singleton pattern for caching
    """
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            env_file: Path to .env file. Defaults to .env in project root.
        """
        self.env_file = env_file or Path(__file__).parent.parent.parent / ".env"
        self.config: Optional[VoiceAgentConfig] = None
        
        logger.info(f"ConfigManager initialized with env_file: {self.env_file}")
    
    def load_config(self) -> VoiceAgentConfig:
        """
        Load configuration from environment variables.
        
        Returns:
            Validated configuration object
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        try:
            # Load .env file if it exists
            if self.env_file.exists():
                logger.info(f"Loading environment variables from: {self.env_file}")
                load_dotenv(self.env_file, override=True)
            else:
                logger.warning(f".env file not found: {self.env_file}")
                logger.info("Using system environment variables only")
            
            # Create configuration from environment variables
            # Pydantic will automatically read VOICE_AGENT_* variables
            self.config = VoiceAgentConfig()
            
            logger.info("Configuration loaded successfully")
            logger.info(f"  Environment: {self.config.environment}")
            logger.info(f"  LLM Provider: {self.config.llm.provider}")
            logger.info(f"  LLM Base URL: {self.config.llm.base_url}")
            logger.info(f"  Default Model: {self.config.llm.models.default}")
            logger.info(f"  API Host: {self.config.api.host}:{self.config.api.port}")
            
            return self.config
            
        except ValidationError as e:
            error_msg = f"Configuration validation failed: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
    
    def get_config(self) -> VoiceAgentConfig:
        """
        Get current configuration, loading if not already loaded.
        
        Returns:
            Current configuration object
            
        Raises:
            ConfigurationError: If no configuration is loaded
        """
        if self.config is None:
            self.load_config()
        return self.config
    
    def reload_config(self) -> VoiceAgentConfig:
        """
        Force reload configuration from environment variables.
        
        Returns:
            Reloaded configuration object
        """
        logger.info("Force reloading configuration...")
        self.config = None
        return self.load_config()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> VoiceAgentConfig:
    """
    Get the current configuration.
    
    This is the main function used throughout the application to access configuration.
    """
    return get_config_manager().get_config()


def load_config() -> VoiceAgentConfig:
    """Load configuration (same as get_config for compatibility)."""
    return get_config()


def reload_config() -> VoiceAgentConfig:
    """Force reload configuration from environment variables."""
    return get_config_manager().reload_config()
