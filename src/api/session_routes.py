"""
会话管理 API 路由 (Session Management Routes)

提供会话管理相关的 API 端点：
- GET /api/v1/conversation/sessions/ - 获取用户会话列表
- GET /api/v1/conversation/sessions/{session_id} - 获取会话详情
- POST /api/v1/conversation/sessions/create - 创建新会话
- DELETE /api/v1/conversation/sessions/{session_id} - 删除会话

Phase 3B - Session Management
Created: 2025-11-04
"""

from typing import Annotated, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from .auth_routes import get_current_user
from core.dependencies import get_db_session
from database.repositories.session_repository import SessionRepository
from database.repositories.message_repository import MessageRepository
from database.repositories.conversation_repository import ConversationRepository
from database.models import User
from utils.session_manager import get_session_manager

logger = logging.getLogger(__name__)


# ============================================
# Router Setup
# ============================================

router = APIRouter(prefix="/api/v1/conversation", tags=["Session Management"])


# ============================================
# Pydantic Models
# ============================================

class SessionListResponse(BaseModel):
    """会话列表响应"""
    total: int = Field(..., description="总会话数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    has_more: bool = Field(..., description="是否还有更多")
    sessions: List[dict] = Field(..., description="会话列表")


class SessionDetailResponse(BaseModel):
    """会话详情响应"""
    session_id: str = Field(..., description="会话 ID")
    status: str = Field(..., description="会话状态")
    total_messages: int = Field(..., description="消息总数")
    created_at: str = Field(..., description="创建时间")
    last_activity: str = Field(..., description="最后活动时间")
    messages: List[dict] = Field(..., description="消息列表")


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field(None, description="会话标题（可选）")


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    session_id: str = Field(..., description="会话 ID")
    title: str = Field(..., description="会话标题")
    created_at: str = Field(..., description="创建时间")


class DeleteSessionResponse(BaseModel):
    """删除会话响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    session_id: str = Field(..., description="已删除的会话 ID")


# ============================================
# API Endpoints
# ============================================

@router.get(
    "/sessions/",
    response_model=SessionListResponse,
    summary="获取用户会话列表",
    description="获取当前登录用户的所有会话（分页）"
)
async def get_user_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小"),
    status: Optional[str] = Query(None, description="会话状态过滤 (ACTIVE/TERMINATED)")
):
    """
    获取用户会话列表
    
    **认证方式**: JWT Token (Bearer)
    
    **示例**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/conversation/sessions/?page=1&page_size=10" \\
         -H "Authorization: Bearer YOUR_JWT_TOKEN"
    ```
    """
    try:
        session_repo = SessionRepository(db_session)
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取用户会话
        sessions = await session_repo.get_user_sessions(
            user_id=current_user.user_id,
            status=status,
            limit=page_size + 1,  # 多取一条判断是否有更多
            offset=offset
        )
        
        # 判断是否有更多
        has_more = len(sessions) > page_size
        if has_more:
            sessions = sessions[:page_size]
        
        # 获取总数
        total = await session_repo.count_sessions(
            user_id=current_user.user_id,
            status=status
        )
        
        # 构建响应
        session_list = []
        for session in sessions:
            # 获取消息数量
            msg_repo = MessageRepository(db_session)
            message_count = await msg_repo.count_session_messages(session.session_id)
            
            session_list.append({
                "session_id": session.session_id,
                "status": session.status,
                "message_count": message_count,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat()
            })
        
        return SessionListResponse(
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
            sessions=session_list
        )
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话列表失败: {str(e)}"
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    summary="获取会话详情",
    description="获取指定会话的详细信息和消息历史"
)
async def get_session_detail(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(50, ge=1, le=200, description="消息数量限制")
):
    """
    获取会话详情
    
    **认证方式**: JWT Token (Bearer)
    
    **示例**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/conversation/sessions/test_session_001" \\
         -H "Authorization: Bearer YOUR_JWT_TOKEN"
    ```
    """
    try:
        session_repo = SessionRepository(db_session)
        
        # 获取会话
        session = await session_repo.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"会话不存在: {session_id}"
            )
        
        # 验证会话所属用户
        if session.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此会话"
            )
        
        # 获取消息
        msg_repo = MessageRepository(db_session)
        messages = await msg_repo.get_messages(
            session_id=session_id,
            limit=limit
        )
        
        # 构建消息列表
        message_list = []
        for msg in messages:
            message_list.append({
                "message_id": str(msg.message_id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            })
        
        return SessionDetailResponse(
            session_id=session.session_id,
            status=session.status,
            total_messages=len(message_list),
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            messages=message_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话详情失败: {str(e)}"
        )


@router.post(
    "/sessions/create",
    response_model=CreateSessionResponse,
    summary="创建新会话",
    description="为当前用户创建一个新的会话"
)
async def create_new_session(
    request: CreateSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)]
):
    """
    创建新会话
    
    **认证方式**: JWT Token (Bearer)
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/conversation/sessions/create" \\
         -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
         -H "Content-Type: application/json" \\
         -d '{"title": "我的新对话"}'
    ```
    """
    try:
        # 生成会话 ID
        import uuid
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        
        # 创建会话
        session_repo = SessionRepository(db_session)
        new_session = await session_repo.create_session(
            session_id=session_id,
            user_id=current_user.user_id,
            metadata={"title": request.title} if request.title else {}
        )
        
        await db_session.commit()
        
        logger.info(f"✅ 用户 {current_user.username} 创建新会话: {session_id}")
        
        return CreateSessionResponse(
            success=True,
            message="会话创建成功",
            session_id=session_id,
            title=request.title or "新对话",
            created_at=new_session.created_at.isoformat()
        )
        
    except Exception as e:
        await db_session.rollback()
        logger.error(f"创建会话失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败: {str(e)}"
        )


@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteSessionResponse,
    summary="删除会话",
    description="删除指定的会话及其所有消息（不可恢复）"
)
async def delete_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)]
):
    """
    删除会话
    
    **认证方式**: JWT Token (Bearer)
    
    **警告**: 此操作不可恢复，会删除会话及所有相关消息！
    
    **示例**:
    ```bash
    curl -X DELETE "http://localhost:8000/api/v1/conversation/sessions/test_session_001" \\
         -H "Authorization: Bearer YOUR_JWT_TOKEN"
    ```
    """
    try:
        session_repo = SessionRepository(db_session)
        
        # 1. 验证会话存在
        session = await session_repo.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"会话不存在: {session_id}"
            )
        
        # 2. 验证会话所属用户
        if session.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除此会话"
            )
        
        # 3. 从数据库删除
        conversation_repo = ConversationRepository(db_session)
        deleted = await conversation_repo.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会话删除失败"
            )
        
        await db_session.commit()
        
        # 4. 从内存缓存删除
        session_manager = get_session_manager()
        if session_manager:
            try:
                await session_manager.clear_session(session_id)
                logger.info(f"✅ 内存缓存已清除: {session_id}")
            except Exception as cache_error:
                logger.warning(f"清除内存缓存失败（已忽略）: {cache_error}")
        else:
            logger.debug("会话管理器未初始化，跳过内存清除")
        
        logger.info(f"✅ 用户 {current_user.username} 删除会话: {session_id}")
        
        return DeleteSessionResponse(
            success=True,
            message="会话已成功删除",
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        logger.error(f"删除会话失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除会话失败: {str(e)}"
        )
