"""
Voice Services Package

提供语音识别（STT）和语音合成（TTS）服务。
"""

from .iflytek_auth import IFlytekAuthenticator, IFlytekAuthError, create_iflytek_auth_url

__all__ = [
    "IFlytekAuthenticator",
    "IFlytekAuthError",
    "create_iflytek_auth_url",
]
