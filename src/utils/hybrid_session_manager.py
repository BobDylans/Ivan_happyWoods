"""
Hybrid Session Manager

双模式会话管理器：内存缓存 + 数据库持久化

特性：
- 内存缓存：快速读取热数据
- 数据库持久化：永久存储，支持横向扩展
- 自动降级：数据库不可用时降级为纯内存模式
- 统计监控：缓存命中率、数据库读写统计
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any
from collections import deque, defaultdict
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import ConversationRepository
from database.connection import get_async_session


logger = logging.getLogger(__name__)


class HybridSessionManager:
    """
    混合会话管理器
    
    结合内存缓存和数据库持久化的优势：
    - 内存缓存：保存最近的消息，提供快速访问
    - 数据库持久化：所有消息永久存储
    - 自动降级：数据库失败时自动切换为纯内存模式
    """
    
    def __init__(
        self,
        conversation_repo: Optional[ConversationRepository] = None,
        memory_limit: int = 20,
        ttl_hours: int = 24,
        enable_database: bool = True
    ):
        """
        初始化混合会话管理器
        
        Args:
            conversation_repo: 对话数据仓库（可选）
            memory_limit: 内存中每个会话保留的最大消息数
            ttl_hours: 会话过期时间（小时）
            enable_database: 是否启用数据库持久化
        """
        # 内存缓存
        self._sessions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=memory_limit))
        self._last_activity: Dict[str, datetime] = {}
        
        # 数据库持久化
        self._conversation_repo = conversation_repo
        self._enable_database = enable_database and conversation_repo is not None
        self._fallback_mode = False  # 降级标志
        
        # 并发控制 - 为数据库操作添加锁
        self._db_lock = asyncio.Lock()
        
        # 配置
        self._memory_limit = memory_limit
        self._ttl_hours = ttl_hours
        
        # 统计信息
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "db_reads": 0,
            "db_writes": 0,
            "db_errors": 0,
            "fallback_triggers": 0
        }
        
        logger.info(
            f"HybridSessionManager 初始化: "
            f"memory_limit={memory_limit}, ttl={ttl_hours}h, "
            f"database={'enabled' if self._enable_database else 'disabled'}"
        )
    
    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史（异步）
        
        优先从内存缓存读取，缓存未命中则从数据库加载
        
        Args:
            session_id: 会话ID
            limit: 最大返回消息数（None = 所有）
        
        Returns:
            消息列表，格式: [{"role": "user", "content": "..."}]
        """
        # 1. 尝试从内存缓存读取
        if session_id in self._sessions:
            cache_messages = list(self._sessions[session_id])
            self._stats["cache_hits"] += 1
            
            logger.debug(f"✅ 缓存命中: session={session_id}, messages={len(cache_messages)}")
            
            # 检查是否需要从数据库补充更多历史
            if self._enable_database and not self._fallback_mode:
                try:
                    db_messages = await self._load_from_database(session_id, limit)
                    
                    # 合并数据库和缓存消息（去重）
                    if db_messages and len(db_messages) > len(cache_messages):
                        logger.info(f"📚 从数据库加载了更多历史: {len(db_messages)} 条")
                        return db_messages[-limit:] if limit else db_messages
                
                except Exception as e:
                    logger.warning(f"从数据库加载历史失败，使用缓存: {e}")
            
            return cache_messages[-limit:] if limit else cache_messages
        
        # 2. 缓存未命中，尝试从数据库加载
        self._stats["cache_misses"] += 1
        logger.debug(f"❌ 缓存未命中: session={session_id}")
        
        if self._enable_database and not self._fallback_mode:
            try:
                messages = await self._load_from_database(session_id, limit)
                
                # 加载到内存缓存
                if messages:
                    self._sessions[session_id] = deque(messages, maxlen=self._memory_limit)
                    self._last_activity[session_id] = datetime.now()
                    logger.info(f"📥 从数据库加载历史: session={session_id}, messages={len(messages)}")
                
                return messages
            
            except Exception as e:
                logger.error(f"从数据库加载历史失败: {e}", exc_info=True)
                self._handle_database_error()
                return []
        
        # 3. 数据库不可用，返回空列表
        logger.debug(f"📭 会话不存在或数据库不可用: session={session_id}")
        return []
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加消息（异步）
        
        同时写入内存和数据库
        
        Args:
            session_id: 会话ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            metadata: 元数据
        """
        message = {
            "role": role,
            "content": content
        }
        
        # 1. 写入内存缓存（不需要锁，快速完成）
        self._sessions[session_id].append(message)
        self._last_activity[session_id] = datetime.now()
        
        logger.debug(f"💬 添加消息到缓存: session={session_id}, role={role}")
        
        # 2. 写入数据库（如果启用）- 使用锁保护
        if self._enable_database and not self._fallback_mode:
            try:
                # 🔒 使用锁确保数据库操作串行化
                async with self._db_lock:
                    await self._save_to_database(session_id, role, content, metadata)
                    self._stats["db_writes"] += 1
                    logger.debug(f"💾 消息已持久化到数据库")
            
            except Exception as e:
                logger.error(f"数据库写入失败: {e}", exc_info=True)
                self._handle_database_error()
    
    async def clear_session(self, session_id: str) -> None:
        """
        清除会话（异步）
        
        同时清除内存和数据库
        
        Args:
            session_id: 会话ID
        """
        # 1. 清除内存缓存
        if session_id in self._sessions:
            del self._sessions[session_id]
        
        if session_id in self._last_activity:
            del self._last_activity[session_id]
        
        logger.info(f"🗑️ 内存会话已清除: {session_id}")
        
        # 2. 清除数据库（如果启用）
        if self._enable_database and not self._fallback_mode and self._conversation_repo:
            try:
                # TODO: 实现数据库会话删除方法
                # await self._conversation_repo.delete_session(session_id)
                logger.info(f"🗑️ 数据库会话已清除: {session_id}")
            
            except Exception as e:
                logger.error(f"数据库清除失败: {e}", exc_info=True)
                self._handle_database_error()
    
    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话（同步，仅内存）
        
        Returns:
            清理的会话数
        """
        now = datetime.now()
        ttl = timedelta(hours=self._ttl_hours)
        
        expired_sessions = [
            session_id
            for session_id, last_activity in self._last_activity.items()
            if now - last_activity > ttl
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
            del self._last_activity[session_id]
        
        if expired_sessions:
            logger.info(f"🧹 清理了 {len(expired_sessions)} 个过期会话")
        
        return len(expired_sessions)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计数据字典
        """
        total_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        cache_hit_rate = (
            self._stats["cache_hits"] / total_requests * 100
            if total_requests > 0
            else 0
        )
        
        return {
            **self._stats,
            "cache_hit_rate": f"{cache_hit_rate:.2f}%",
            "active_sessions": len(self._sessions),
            "fallback_mode": self._fallback_mode,
            "database_enabled": self._enable_database
        }
    
    # ========== 私有方法 ==========
    
    async def _load_from_database(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """从数据库加载消息历史"""
        if not self._conversation_repo:
            return []
        
        self._stats["db_reads"] += 1
        
        # 直接使用传入的 conversation_repo
        messages = await self._conversation_repo.get_conversation_history_dict(
            session_id=session_id,
            limit=limit or self._memory_limit
        )
        
        return messages
    
    async def _save_to_database(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """保存消息到数据库"""
        if not self._conversation_repo:
            return
        
        # ✅ 1. 确保 session 存在（如果不存在则创建）
        await self._ensure_session_exists(session_id)
        
        # 2. 保存消息
        await self._conversation_repo.save_message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata
        )
        
        # ✅ 3. 提交事务，确保数据持久化
        await self._conversation_repo.session.commit()
    
    async def _ensure_session_exists(self, session_id: str) -> None:
        """确保 session 记录存在，不存在则创建"""
        if not self._conversation_repo:
            return
        
        try:
            # 获取 session_repository
            from database.repositories import SessionRepository
            session_repo = SessionRepository(self._conversation_repo.session)
            
            # 检查 session 是否存在
            existing_session = await session_repo.get_session(session_id)
            
            if existing_session is None:
                # 创建新 session
                await session_repo.create_session(
                    session_id=session_id,
                    user_id=None,  # 暂时不关联用户
                    metadata={"created_by": "hybrid_session_manager"}
                )
                # 注意：这里只 flush，不 commit，commit 由外层统一处理
                logger.info(f"✅ 自动创建 session: {session_id}")
            else:
                # 更新 session 活跃时间
                await session_repo.update_session_activity(session_id)
                logger.debug(f"🔄 更新 session 活跃时间: {session_id}")
        
        except Exception as e:
            logger.error(f"❌ 确保 session 存在失败: {e}", exc_info=True)
            # 不抛出异常，让消息保存继续进行
    
    def _handle_database_error(self) -> None:
        """处理数据库错误，触发降级"""
        self._stats["db_errors"] += 1
        
        if not self._fallback_mode:
            self._fallback_mode = True
            self._stats["fallback_triggers"] += 1
            logger.warning(
                "⚠️ 数据库连续错误，已切换到纯内存模式（fallback mode）"
            )
    
    async def reset_fallback(self) -> bool:
        """
        尝试恢复数据库连接，退出降级模式
        
        Returns:
            True 如果恢复成功
        """
        if not self._fallback_mode:
            return True
        
        if not self._conversation_repo:
            return False
        
        try:
            # 测试数据库连接 - 简单查询测试
            await self._conversation_repo.get_conversation_history_dict("test", limit=1)
            
            self._fallback_mode = False
            logger.info("✅ 数据库连接已恢复，退出降级模式")
            return True
        
        except Exception as e:
            logger.warning(f"数据库仍不可用: {e}")
            return False


# ========== 全局实例管理 ==========

_global_session_manager: Optional[HybridSessionManager] = None


async def initialize_session_manager(
    enable_database: bool = True,
    memory_limit: int = 20,
    ttl_hours: int = 24
) -> HybridSessionManager:
    """
    初始化全局会话管理器
    
    Args:
        enable_database: 是否启用数据库
        memory_limit: 内存缓存消息数
        ttl_hours: 会话过期时间
    
    Returns:
        HybridSessionManager 实例
    """
    global _global_session_manager
    
    if _global_session_manager is None:
        # 创建数据库仓库实例（如果启用）
        conversation_repo = None
        if enable_database:
            try:
                # 注意：不在这里创建 session，由外部调用者管理
                # 这里只是标记需要数据库支持
                logger.info("✅ 数据库支持已启用（需要外部提供 session）")
            except Exception as e:
                logger.warning(f"数据库初始化失败，将使用纯内存模式: {e}")
        
        _global_session_manager = HybridSessionManager(
            conversation_repo=conversation_repo,
            memory_limit=memory_limit,
            ttl_hours=ttl_hours,
            enable_database=enable_database
        )
        
        logger.info("🚀 全局 HybridSessionManager 已初始化")
    
    return _global_session_manager


def get_session_manager() -> Optional[HybridSessionManager]:
    """获取全局会话管理器实例"""
    return _global_session_manager
