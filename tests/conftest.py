"""
Pytest 配置文件

设置测试环境的Python路径和公共fixtures
"""

import sys
from pathlib import Path

# 将 src 目录添加到 Python 路径
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import pytest


@pytest.fixture
def sample_config():
    """提供示例配置用于测试"""
    from config.models import VoiceAgentConfig
    return VoiceAgentConfig()

