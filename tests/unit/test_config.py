"""
Unit tests for configuration management.

Tests configuration loading, validation, environment variable overrides,
and error handling scenarios.
"""

import os
import tempfile
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config import (
    ConfigManager,
    ConfigurationError,
    VoiceAgentConfig,
    get_config,
    load_config,
    LLMProvider,
    TTSProvider,
    STTProvider,
    LogLevel,
)


class TestConfigModels:
    """Test configuration data models."""
    
    def test_minimal_config_creation(self):
        """Test creating config with minimal required fields."""
        config_data = {
            "llm": {
                "api_key": "test-key-12345"
            }
        }
        config = VoiceAgentConfig(**config_data)
        
        assert config.llm.api_key == "test-key-12345"
        assert config.llm.provider == LLMProvider.OPENAI
        assert config.api.port == 8000
        assert config.environment == "development"
    
    def test_full_config_creation(self):
        """Test creating config with all fields specified."""
        config_data = {
            "api": {
                "host": "0.0.0.0",
                "port": 9000,
                "reload": True,
                "workers": 2
            },
            "llm": {
                "provider": "anthropic",
                "api_key": "test-anthropic-key",
                "base_url": "https://api.anthropic.com",
                "models": {
                    "default": "claude-3",
                    "fast": "claude-instant",
                    "creative": "claude-3"
                },
                "timeout": 45,
                "max_tokens": 4096,
                "temperature": 0.8
            },
            "speech": {
                "tts": {
                    "provider": "elevenlabs",
                    "voice": "rachel",
                    "speed": 1.2,
                    "format": "wav"
                },
                "stt": {
                    "provider": "google",
                    "language": "en-GB",
                    "model": "latest"
                }
            },
            "environment": "testing"
        }
        
        config = VoiceAgentConfig(**config_data)
        
        assert config.api.host == "0.0.0.0"
        assert config.api.port == 9000
        assert config.llm.provider == LLMProvider.ANTHROPIC
        assert config.llm.models.default == "claude-3"
        assert config.speech.tts.provider == TTSProvider.ELEVENLABS
        assert config.speech.stt.provider == STTProvider.GOOGLE
        assert config.environment == "testing"
    
    def test_config_validation_errors(self):
        """Test configuration validation catches errors."""
        # Missing required API key
        with pytest.raises(Exception):
            VoiceAgentConfig(llm={})
        
        # Invalid port
        with pytest.raises(Exception):
            VoiceAgentConfig(
                llm={"api_key": "test-key"},
                api={"port": 70000}
            )
        
        # Invalid environment
        with pytest.raises(Exception):
            VoiceAgentConfig(
                llm={"api_key": "test-key"},
                environment="invalid-env"
            )
        
        # Invalid base URL
        with pytest.raises(Exception):
            VoiceAgentConfig(
                llm={
                    "api_key": "test-key",
                    "base_url": "not-a-url"
                }
            )


class TestConfigManager:
    """Test configuration manager functionality."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory with test config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create base config
            base_config = {
                "llm": {
                    "api_key": "base-key",
                    "provider": "openai"
                },
                "api": {
                    "port": 8000
                }
            }
            with open(config_dir / "base.yaml", 'w') as f:
                yaml.dump(base_config, f)
            
            # Create development config
            dev_config = {
                "api": {
                    "port": 9000,
                    "reload": True
                },
                "debug": True
            }
            with open(config_dir / "development.yaml", 'w') as f:
                yaml.dump(dev_config, f)
            
            yield config_dir
    
    def test_config_loading(self, temp_config_dir):
        """Test basic configuration loading."""
        manager = ConfigManager(temp_config_dir)
        config = manager.load_config("development")
        
        assert config.llm.api_key == "base-key"
        assert config.api.port == 9000  # Overridden by development config
        assert config.api.reload is True
        assert config.debug is True
        assert config.environment == "development"
    
    def test_environment_variable_overrides(self, temp_config_dir):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            "VOICE_AGENT_LLM__API_KEY": "env-override-key",
            "VOICE_AGENT_API__PORT": "7000",
            "VOICE_AGENT_DEBUG": "false"
        }):
            manager = ConfigManager(temp_config_dir)
            config = manager.load_config("development")
            
            assert config.llm.api_key == "env-override-key"
            assert config.api.port == 7000
            assert config.debug is False
    
    def test_config_validation(self, temp_config_dir):
        """Test configuration validation."""
        manager = ConfigManager(temp_config_dir)
        
        # Valid config
        valid_config = {
            "llm": {"api_key": "valid-key-12345"},
            "api": {"port": 8000}
        }
        assert manager.validate_config(valid_config) is True
        
        # Invalid config
        invalid_config = {
            "llm": {"api_key": "short"},  # Too short
            "api": {"port": 70000}  # Invalid port
        }
        assert manager.validate_config(invalid_config) is False
    
    def test_missing_config_file(self):
        """Test handling of missing configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(Path(temp_dir))
            
            # Should fail if no config files exist and no env vars set
            with pytest.raises(ConfigurationError):
                manager.load_config("nonexistent")
    
    def test_config_file_changes_detection(self, temp_config_dir):
        """Test detection of configuration file changes."""
        manager = ConfigManager(temp_config_dir)
        manager.load_config("development")
        
        # Initially no changes
        assert manager.has_config_changed() is False
        
        # Modify a config file
        import time
        time.sleep(0.1)  # Ensure timestamp difference
        config_file = temp_config_dir / "development.yaml"
        with open(config_file, 'a') as f:
            f.write("\n# Modified\n")
        
        # Should detect change
        assert manager.has_config_changed() is True
    
    def test_environment_value_conversion(self, temp_config_dir):
        """Test conversion of environment variable values."""
        with patch.dict(os.environ, {
            "VOICE_AGENT_API__PORT": "8080",
            "VOICE_AGENT_DEBUG": "true",
            "VOICE_AGENT_LLM__TEMPERATURE": "0.5",
            "VOICE_AGENT_TOOLS__ENABLED": "search,calculator,time"
        }):
            manager = ConfigManager(temp_config_dir)
            config = manager.load_config("development")
            
            assert isinstance(config.api.port, int)
            assert config.api.port == 8080
            assert isinstance(config.debug, bool)
            assert config.debug is True
            assert isinstance(config.llm.temperature, float)
            assert config.llm.temperature == 0.5


class TestConfigIntegration:
    """Test configuration integration with application."""
    
    def test_get_config_function(self):
        """Test global config access function."""
        with patch.dict(os.environ, {
            "VOICE_AGENT_LLM__API_KEY": "global-test-key"
        }):
            config = get_config()
            assert isinstance(config, VoiceAgentConfig)
            assert config.llm.api_key == "global-test-key"
    
    def test_load_config_function(self):
        """Test global config loading function."""
        with patch.dict(os.environ, {
            "VOICE_AGENT_LLM__API_KEY": "load-test-key",
            "VOICE_AGENT_ENVIRONMENT": "testing"
        }):
            config = load_config()
            assert config.environment == "testing"
            assert config.llm.api_key == "load-test-key"
    
    @patch.dict(os.environ, {
        "VOICE_AGENT_LLM__API_KEY": "env-test-key"
    })
    def test_config_environment_prefix(self):
        """Test that VOICE_AGENT_ prefix works correctly."""
        config = load_config()
        assert config.llm.api_key == "env-test-key"


class TestConfigErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_yaml_file(self):
        """Test handling of invalid YAML files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create invalid YAML file
            with open(config_dir / "development.yaml", 'w') as f:
                f.write("invalid: yaml: content: [unclosed")
            
            manager = ConfigManager(config_dir)
            with pytest.raises(ConfigurationError):
                manager.load_config("development")
    
    def test_configuration_error_message(self):
        """Test that configuration errors have helpful messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(Path(temp_dir))
            
            try:
                manager.load_config("nonexistent")
            except ConfigurationError as e:
                assert "Failed to load configuration" in str(e)
                assert isinstance(e.__cause__, Exception)


if __name__ == "__main__":
    pytest.main([__file__])