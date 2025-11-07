"""
用户认证 API 路由 (Authentication Routes)

提供用户认证相关的 API 端点：
- POST /api/v1/auth/register - 用户注册
- POST /api/v1/auth/login - 用户登录
- GET /api/v1/auth/me - 获取当前用户信息
- POST /api/v1/auth/refresh - 刷新 Access Token

Phase 3B - User Login System
Created: 2025-11-03
"""

from typing import Annotated
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field

from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES
)
from database.repositories.user_repository import UserRepository
from core.dependencies import get_db_session


# ============================================
# Router Setup
# ============================================

router = APIRouter()

# OAuth2 Password Bearer for JWT authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ============================================
# Pydantic Models
# ============================================

class UserRegisterRequest(BaseModel):
    """用户注册请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名（3-50 字符）")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, description="密码（至少 8 字符）")
    full_name: str | None = Field(None, max_length=100, description="全名（可选）")


class UserLoginResponse(BaseModel):
    """用户登录响应模型"""
    access_token: str = Field(..., description="JWT Access Token (30 分钟有效)")
    refresh_token: str = Field(..., description="JWT Refresh Token (7 天有效)")
    token_type: str = Field(default="bearer", description="Token 类型")
    expires_in: int = Field(..., description="Access Token 过期时间（秒）")


class UserInfoResponse(BaseModel):
    """用户信息响应模型"""
    user_id: UUID
    username: str
    email: str
    full_name: str | None
    is_active: bool
    created_at: str


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求模型"""
    refresh_token: str = Field(..., description="Refresh Token")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


# ============================================
# Dependency: Get Current User
# ============================================

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_db_session)
):
    """
    依赖注入：从 JWT Token 中获取当前用户
    
    Args:
        token: JWT Access Token
        session: 数据库 Session
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: Token 无效或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 解码 Token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    # 检查 Token 类型
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 类型错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 获取用户 ID
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception
    
    # 从数据库查询用户
    user_repo = UserRepository(session)
    user = await user_repo.get_user_by_id(user_id)
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    return user


# ============================================
# API Endpoints
# ============================================

@router.post(
    "/auth/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="创建新用户账户"
)
async def register_user(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    用户注册端点
    
    - 检查用户名和邮箱是否已存在
    - 哈希密码
    - 创建用户记录
    
    **请求示例**:
    ```json
    {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "SecurePass123",
        "full_name": "John Doe"
    }
    ```
    
    **响应示例**:
    ```json
    {
        "message": "用户注册成功"
    }
    ```
    """
    user_repo = UserRepository(session)
    
    # 检查用户名是否已存在
    existing_user = await user_repo.get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被使用"
        )
    
    # 检查邮箱是否已存在
    existing_email = await user_repo.get_user_by_email(request.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 哈希密码
    hashed_password = hash_password(request.password)
    
    # 创建用户
    try:
        await user_repo.create_user(
            username=request.username,
            email=request.email,
            hashed_password=hashed_password,
            full_name=request.full_name
        )
        
        return MessageResponse(message="用户注册成功")
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post(
    "/auth/login",
    response_model=UserLoginResponse,
    summary="用户登录",
    description="使用用户名和密码登录，返回 JWT Token"
)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_db_session)
):
    """
    用户登录端点（OAuth2 Password Flow）
    
    - 验证用户名和密码
    - 生成 Access Token 和 Refresh Token
    
    **请求参数** (application/x-www-form-urlencoded):
    - username: 用户名
    - password: 密码
    
    **响应示例**:
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800
    }
    ```
    """
    user_repo = UserRepository(session)
    
    # 查询用户
    user = await user_repo.get_user_by_username(form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    # 生成 Token
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.user_id)}
    )
    
    return UserLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get(
    "/auth/me",
    response_model=UserInfoResponse,
    summary="获取当前用户信息",
    description="使用 JWT Token 获取当前登录用户的信息"
)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """
    获取当前用户信息端点
    
    **需要认证**: 在 Header 中包含 `Authorization: Bearer <access_token>`
    
    **响应示例**:
    ```json
    {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "is_active": true,
        "created_at": "2025-11-03T10:30:00"
    }
    ```
    """
    return UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )


@router.post(
    "/auth/refresh",
    response_model=UserLoginResponse,
    summary="刷新 Access Token",
    description="使用 Refresh Token 获取新的 Access Token"
)
async def refresh_access_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    刷新 Token 端点
    
    - 验证 Refresh Token
    - 生成新的 Access Token 和 Refresh Token
    
    **请求示例**:
    ```json
    {
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    
    **响应示例**:
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800
    }
    ```
    """
    # 解码 Refresh Token
    payload = decode_token(request.refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Refresh Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查 Token 类型
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 类型错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 获取用户 ID
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 数据无效"
        )
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户 ID 格式错误"
        )
    
    # 验证用户是否存在
    user_repo = UserRepository(session)
    user = await user_repo.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    # 生成新的 Token
    new_access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.user_id)}
    )
    
    return UserLoginResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
