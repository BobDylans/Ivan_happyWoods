"""
认证服务模块 (Authentication Service)

提供用户认证相关的核心功能：
- 密码哈希和验证 (bcrypt)
- JWT Token 生成和验证
- Token 刷新机制

Phase 3B - User Login System
Created: 2025-11-03
Updated: 2025-11-03 (直接使用 bcrypt，避免 passlib 兼容性问题)
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
from jose import jwt, JWTError


# ============================================
# Configuration
# ============================================

# JWT Settings (从环境变量读取)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# ============================================
# Password Hashing (直接使用 bcrypt)
# ============================================

def hash_password(password: str) -> str:
    """
    使用 bcrypt 哈希密码
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希后的密码字符串
        
    Note:
        bcrypt 限制密码长度为 72 字节，超出部分会被自动截断
        
    Example:
        >>> hashed = hash_password("my_secret_password")
        >>> print(len(hashed))  # bcrypt hash 长度约为 60
        60
    """
    # bcrypt 限制密码为 72 字节，手动截断以避免错误
    password_bytes = password.encode('utf-8')[:72]
    
    # 使用 bcrypt 直接哈希（bcrypt.hashpw 需要 bytes 类型）
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # 返回字符串格式
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: 数据库中存储的哈希密码
        
    Returns:
        bool: 密码是否匹配
        
    Note:
        bcrypt 限制密码长度为 72 字节，超出部分会被自动截断
        
    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    # bcrypt 限制密码为 72 字节，手动截断以保持与哈希时一致
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    
    # 使用 bcrypt.checkpw 验证
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ============================================
# JWT Token Management
# ============================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT Access Token
    
    Args:
        data: Token 中要包含的数据（通常是 user_id, username 等）
        expires_delta: Token 有效期（可选，默认 30 分钟）
        
    Returns:
        str: JWT Token 字符串
        
    Example:
        >>> token = create_access_token({"sub": "user123"})
        >>> print(len(token) > 100)  # JWT token 长度 > 100
        True
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    创建 JWT Refresh Token (长期有效)
    
    Args:
        data: Token 中要包含的数据
        
    Returns:
        str: Refresh Token 字符串
        
    Example:
        >>> token = create_refresh_token({"sub": "user123"})
        >>> decoded = decode_token(token)
        >>> decoded["type"]
        'refresh'
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码并验证 JWT Token
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        Optional[Dict]: Token 中的数据（如果验证成功），否则返回 None
        
    Example:
        >>> token = create_access_token({"sub": "user123"})
        >>> payload = decode_token(token)
        >>> payload["sub"]
        'user123'
        >>> payload["type"]
        'access'
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ============================================
# Token Validation Helpers
# ============================================

def is_token_expired(token: str) -> bool:
    """
    检查 Token 是否过期
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        bool: Token 是否过期（True=已过期）
    """
    payload = decode_token(token)
    if not payload:
        return True
    
    exp = payload.get("exp")
    if not exp:
        return True
    
    return datetime.utcfromtimestamp(exp) < datetime.utcnow()


def get_token_type(token: str) -> Optional[str]:
    """
    获取 Token 类型 (access 或 refresh)
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        Optional[str]: Token 类型 ('access' 或 'refresh')，验证失败返回 None
    """
    payload = decode_token(token)
    if not payload:
        return None
    return payload.get("type")
