"""
iFlytek WebSocket Authentication

科大讯飞 WebSocket 认证工具，支持 STT 和 TTS 服务的 HMAC-SHA256 签名。
"""

import hashlib
import hmac
import base64
from urllib.parse import urlencode, urlparse
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime
from typing import Tuple

# 这个类里面实现了讯飞的认证流程
class IFlytekAuthError(Exception):
    """iFlytek 认证错误"""
    pass


class IFlytekAuthenticator:
    """
    iFlytek WebSocket 认证器
    
    提供统一的 HMAC-SHA256 签名和 URL 构建功能，
    支持 STT、TTS 等所有基于 WebSocket 的服务。
    
    认证流程:
    1. 解析 WebSocket URL（schema, host, path）
    2. 生成 RFC1123 格式时间戳
    3. 构造签名原文: "host: {host}\\ndate: {date}\\nGET {path} HTTP/1.1"
    4. 使用 APISecret 进行 HMAC-SHA256 签名
    5. 构造 authorization 字符串并 Base64 编码
    6. 拼接查询参数: host + date + authorization
    
    使用示例:
        auth = IFlytekAuthenticator(
            api_key="your_api_key",
            api_secret="your_api_secret"
        )
        
        ws_url = auth.build_auth_url(
            base_url="wss://iat.cn-huabei-1.xf-yun.com/v1"
        )
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """
        初始化认证器
        
        Args:
            api_key: iFlytek API Key
            api_secret: iFlytek API Secret
        
        Raises:
            IFlytekAuthError: 如果参数无效
        """
        if not api_key or not api_secret:
            raise IFlytekAuthError("API key and secret are required")
        
        self.api_key = api_key
        self.api_secret = api_secret
    
    def _parse_url(self, url: str) -> Tuple[str, str, str]:
        """
        解析 WebSocket URL
        
        Args:
            url: WebSocket URL (例如: wss://host.com/path)
        
        Returns:
            (schema, host, path) 元组
            - schema: "wss://" 或 "ws://"
            - host: 主机名（不含路径）
            - path: 路径部分（含 /）
        
        Raises:
            IFlytekAuthError: 如果 URL 格式无效
        """
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            
            schema = f"{parsed.scheme}://"
            host = parsed.netloc
            path = parsed.path or "/"
            
            return schema, host, path
        
        except Exception as e:
            raise IFlytekAuthError(f"Failed to parse URL: {e}") from e
    
    def _generate_timestamp(self) -> str:
        """
        生成 RFC1123 格式的时间戳
        
        Returns:
            RFC1123 格式字符串，例如: "Mon, 14 Oct 2025 08:30:00 GMT"
        """
        now = datetime.now()
        timestamp = mktime(now.timetuple())
        return format_date_time(timestamp)
    
    def _create_signature(self, host: str, date: str, path: str) -> str:
        """
        创建 HMAC-SHA256 签名
        
        Args:
            host: 主机名
            date: RFC1123 时间戳
            path: URL 路径
        
        Returns:
            Base64 编码的签名字符串
        """
        # 构造签名原文
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        
        # HMAC-SHA256 签名
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        # Base64 编码
        return base64.b64encode(signature_sha).decode('utf-8')
    
    def _create_authorization(self, signature: str) -> str:
        """
        创建 authorization 字符串
        
        Args:
            signature: Base64 编码的签名
        
        Returns:
            Base64 编码的 authorization 字符串
        """
        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        
        return base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
    
    def build_auth_url(self, base_url: str) -> str:
        """
        构建带认证参数的 WebSocket URL
        
        Args:
            base_url: 基础 WebSocket URL
                例如: "wss://iat.cn-huabei-1.xf-yun.com/v1"
        
        Returns:
            完整的认证 URL，包含 host、date、authorization 查询参数
        
        Raises:
            IFlytekAuthError: 如果 URL 构建失败
        
        Example:
            >>> auth = IFlytekAuthenticator("key", "secret")
            >>> url = auth.build_auth_url("wss://iat.cn-huabei-1.xf-yun.com/v1")
            >>> print(url)
            wss://iat.cn-huabei-1.xf-yun.com/v1?host=...&date=...&authorization=...
        """
        try:
            # 1. 解析 URL
            schema, host, path = self._parse_url(base_url)
            
            # 2. 生成时间戳
            date = self._generate_timestamp()
            
            # 3. 创建签名
            signature = self._create_signature(host, date, path)
            
            # 4. 创建 authorization
            authorization = self._create_authorization(signature)
            
            # 5. 构建查询参数
            query_params = {
                "host": host,
                "date": date,
                "authorization": authorization
            }
            
            # 6. 拼接完整 URL
            full_url = f"{base_url}?{urlencode(query_params)}"
            
            return full_url
        
        except IFlytekAuthError:
            raise
        except Exception as e:
            raise IFlytekAuthError(f"Failed to build auth URL: {e}") from e
    
    def validate_credentials(self) -> bool:
        """
        验证凭证格式是否有效
        
        Returns:
            True 如果凭证格式有效，False 否则
        """
        # 基本格式检查
        if not self.api_key or len(self.api_key) < 16:
            return False
        
        if not self.api_secret or len(self.api_secret) < 16:
            return False
        
        return True


def create_iflytek_auth_url(
    base_url: str,
    api_key: str,
    api_secret: str
) -> str:
    """
    快捷函数：创建 iFlytek 认证 URL
    
    Args:
        base_url: WebSocket 基础 URL
        api_key: API Key
        api_secret: API Secret
    
    Returns:
        完整的认证 URL
    
    Raises:
        IFlytekAuthError: 如果认证失败
    
    Example:
        >>> url = create_iflytek_auth_url(
        ...     "wss://iat.cn-huabei-1.xf-yun.com/v1",
        ...     "your_key",
        ...     "your_secret"
        ... )
    """
    auth = IFlytekAuthenticator(api_key, api_secret)
    return auth.build_auth_url(base_url)


# STT 和 TTS 的常用端点
STT_BASE_URL = "wss://iat.cn-huabei-1.xf-yun.com/v1"
TTS_BASE_URL = "wss://tts-api.xfyun.cn/v2/tts"  # 通用端点，非私有化部署


if __name__ == "__main__":
    # 测试认证器
    import os
    
    api_key = os.getenv("IFLYTEK_APIKEY", "test_key_32_characters_long____")
    api_secret = os.getenv("IFLYTEK_APISECRET", "test_secret_32_characters_long_")
    
    auth = IFlytekAuthenticator(api_key, api_secret)
    
    # 测试 STT URL
    print("=== STT Authentication URL ===")
    stt_url = auth.build_auth_url(STT_BASE_URL)
    print(f"URL Length: {len(stt_url)}")
    print(f"URL: {stt_url[:100]}...")
    
    # 测试 TTS URL
    print("\n=== TTS Authentication URL ===")
    tts_url = auth.build_auth_url(TTS_BASE_URL)
    print(f"URL Length: {len(tts_url)}")
    print(f"URL: {tts_url[:100]}...")
    
    # 验证凭证
    print("\n=== Credentials Validation ===")
    print(f"Valid: {auth.validate_credentials()}")
