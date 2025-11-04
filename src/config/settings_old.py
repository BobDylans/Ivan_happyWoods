"""
Configuration management for the voice agent system.

This module handles loading configuration from YAML files and environment variables,
with support for hierarchical configuration and hot-reloading in development.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import ValidationError

from .models import VoiceAgentConfig, ENV_VAR_MAPPING


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class ConfigManager:
    """
    Configuration manager that handles loading from files and environment variables.
    
    Supports:
    - YAML configuration files
    - Environment variable overrides
    - Hierarchical configuration (base + environment-specific)
    - Configuration validation
    - Hot-reloading in development mode
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files.
                       Defaults to ./config from project root.
        """
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self.config: Optional[VoiceAgentConfig] = None
        self._file_timestamps: Dict[str, float] = {}
        
        logger.info(f"ConfigManager initialized with config_dir: {self.config_dir}")
    
    def load_config(self, environment: Optional[str] = None) -> VoiceAgentConfig:
        """
        Load configuration from files and environment variables.
        
        Args:
            environment: Target environment (development, production, etc.)
                        If None, uses VOICE_AGENT_ENVIRONMENT env var or 'development'
        
        Returns:
            Validated configuration object
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        try:
            # Determine environment
            env = environment or os.getenv("VOICE_AGENT_ENVIRONMENT", "development")
            logger.info(f"Loading configuration for environment: {env}")
            
            # Load base configuration
            config_data = self._load_yaml_config(env)
            
            # Apply environment variable overrides
            config_data = self._apply_env_overrides(config_data)
            
            # Validate and create configuration object
            self.config = VoiceAgentConfig(**config_data)
            
            # Store file timestamps for hot-reloading
            self._update_file_timestamps(env)
            
            logger.info("Configuration loaded successfully")
            return self.config
            
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
    
    def _load_yaml_config(self, environment: str) -> Dict[str, Any]:
        """Load configuration from YAML files."""
        config_data = {}
        
        # Load base configuration if it exists
        base_config_path = self.config_dir / "base.yaml"
        if base_config_path.exists():
            logger.debug(f"Loading base config from: {base_config_path}")
            with open(base_config_path, 'r', encoding='utf-8') as f:
                config_data.update(yaml.safe_load(f) or {})
        
        # Load environment-specific configuration
        env_config_path = self.config_dir / f"{environment}.yaml"
        if env_config_path.exists():
            logger.debug(f"Loading environment config from: {env_config_path}")
            with open(env_config_path, 'r', encoding='utf-8') as f:
                env_config = yaml.safe_load(f) or {}
                config_data = self._merge_configs(config_data, env_config)
        else:
            logger.warning(f"Environment config file not found: {env_config_path}")
        
        return config_data
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        logger.debug("Applying environment variable overrides")
        
        # Apply mapped environment variables
        for env_var, config_path in ENV_VAR_MAPPING.items():
            value = os.getenv(env_var)
            if value is not None:
                logger.debug(f"Override from {env_var}: {config_path} = {value}")
                self._set_nested_value(config_data, config_path, self._convert_env_value(value))
        
        # Apply automatic Pydantic environment variable parsing
        # This allows any config field to be overridden with VOICE_AGENT_ prefix
        for key, value in os.environ.items():
            if key.startswith("VOICE_AGENT_") and key not in ENV_VAR_MAPPING:
                # Convert VOICE_AGENT_SECTION__FIELD to section.field
                config_path = key[12:].lower().replace("__", ".")  # Remove VOICE_AGENT_ prefix
                logger.debug(f"Auto-override from {key}: {config_path} = {value}")
                self._set_nested_value(config_data, config_path, self._convert_env_value(value))
        
        return config_data
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set a nested dictionary value using dot notation."""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate Python type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # List conversion (comma-separated)
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # Return as string
        return value
    
    def _update_file_timestamps(self, environment: str) -> None:
        """Update file timestamps for hot-reloading detection."""
        files_to_track = [
            self.config_dir / "base.yaml",
            self.config_dir / f"{environment}.yaml"
        ]
        
        for file_path in files_to_track:
            if file_path.exists():
                self._file_timestamps[str(file_path)] = file_path.stat().st_mtime
    
    def has_config_changed(self) -> bool:
        """Check if any configuration files have been modified."""
        for file_path, timestamp in self._file_timestamps.items():
            path = Path(file_path)
            if path.exists() and path.stat().st_mtime > timestamp:
                return True
        return False
    
    def reload_if_changed(self) -> bool:
        """
        Reload configuration if files have changed.
        
        Returns:
            True if configuration was reloaded, False otherwise
        """
        if self.has_config_changed():
            logger.info("Configuration files changed, reloading...")
            try:
                old_env = self.config.environment if self.config else "development"
                self.load_config(old_env)
                return True
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")
                return False
        return False
    
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
    
    def validate_config(self, config_data: Dict[str, Any]) -> bool:
        """
        Validate configuration data without loading it.
        
        Args:
            config_data: Configuration dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            VoiceAgentConfig(**config_data)
            return True
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> VoiceAgentConfig:
    """Get the current configuration."""
    return get_config_manager().get_config()


def load_config(environment: Optional[str] = None) -> VoiceAgentConfig:
    """Load configuration with specified environment."""
    return get_config_manager().load_config(environment)


def reload_config_if_changed() -> bool:
    """Reload configuration if files have changed."""
    return get_config_manager().reload_if_changed()