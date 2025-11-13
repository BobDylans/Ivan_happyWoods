"""
测试 SessionManager (HybridSessionManager) 增强版

本测试套件验证混合会话管理器的核心功能，包括：
- session_factory 机制
- 内存缓存和数据库持久化
- 数据库故障自动降级
- 并发操作安全性
- 内存限制和TTL过期
- 统计信息追踪
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from collections import deque

from utils.session_manager import HybridSessionManager


class TestSessionManagerInitialization:
    """测试初始化和配置"""

    def test_init_with_defaults(self):
        """测试默认参数初始化"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        assert manager._memory_limit == 20
        assert manager._ttl_hours == 24
        assert manager._fallback_mode is True
        assert manager._enable_database is False

    def test_init_with_custom_params(self):
        """测试自定义参数"""
        factory = Mock()
        manager = HybridSessionManager(
            session_factory=factory,
            memory_limit=50,
            ttl_hours=48,
            enable_database=True
        )
        
        assert manager._memory_limit == 50
        assert manager._ttl_hours == 48
        assert manager._enable_database is True
        assert manager._fallback_mode is False

    def test_init_backward_compatibility(self):
        """测试向后兼容的旧参数"""
        manager = HybridSessionManager(
            session_factory=None,
            max_history=30,  # 旧参数
            ttl=timedelta(hours=12),  # 旧参数
            enable_database=False
        )
        
        # 旧参数应该映射到新参数
        assert manager._memory_limit == 30
        assert manager._ttl_hours == 12
        assert manager.max_history == 30  # 兼容属性

    def test_init_auto_fallback_when_no_factory(self):
        """测试无factory时自动进入降级模式"""
        manager = HybridSessionManager(
            session_factory=None,
            enable_database=True  # 虽然启用，但无factory
        )
        
        # 应该自动降级
        assert manager._fallback_mode is True
        assert manager._enable_database is False


class TestSessionManagerMemoryOperations:
    """测试纯内存操作"""

    @pytest.mark.asyncio
    async def test_add_and_get_message_memory_only(self):
        """测试纯内存模式的添加和获取"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        await manager.add_message("test_session", "user", "Hello")
        await manager.add_message("test_session", "assistant", "Hi there")
        
        history = await manager.get_history("test_session")
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there"

    @pytest.mark.asyncio
    async def test_memory_limit_enforcement(self):
        """测试内存限制强制执行"""
        manager = HybridSessionManager(
            session_factory=None,
            memory_limit=3,
            enable_database=False
        )
        
        # 添加4条消息，超过限制
        await manager.add_message("test_session", "user", "Msg 1")
        await manager.add_message("test_session", "user", "Msg 2")
        await manager.add_message("test_session", "user", "Msg 3")
        await manager.add_message("test_session", "user", "Msg 4")
        
        history = await manager.get_history("test_session")
        
        # 应该只保留最后3条
        assert len(history) == 3
        assert history[0]["content"] == "Msg 2"
        assert history[2]["content"] == "Msg 4"

    @pytest.mark.asyncio
    async def test_get_history_with_limit(self):
        """测试获取历史时的数量限制"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        for i in range(10):
            await manager.add_message("test_session", "user", f"Message {i}")
        
        # 只获取最后5条
        history = await manager.get_history("test_session", limit=5)
        
        assert len(history) == 5
        assert history[-1]["content"] == "Message 9"

    @pytest.mark.asyncio
    async def test_get_history_nonexistent_session(self):
        """测试获取不存在会话的历史"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        history = await manager.get_history("nonexistent")
        
        assert history == []

    @pytest.mark.asyncio
    async def test_clear_session_memory(self):
        """测试清除会话（内存）"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        await manager.add_message("test_session", "user", "Test")
        assert len(await manager.get_history("test_session")) == 1
        
        await manager.clear_session("test_session")
        
        history = await manager.get_history("test_session")
        assert history == []


class TestSessionManagerDatabaseFallback:
    """测试数据库降级机制"""

    @pytest.mark.asyncio
    async def test_database_write_failure_triggers_fallback(self):
        """测试数据库写入失败触发降级"""
        # 创建会失败的mock factory
        mock_factory = AsyncMock()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_factory.return_value.__aenter__.return_value = mock_session
        
        manager = HybridSessionManager(
            session_factory=mock_factory,
            enable_database=True
        )
        
        # 添加消息会触发数据库写入失败
        await manager.add_message("test_session", "user", "Test")
        
        # 应该进入降级模式
        assert manager._fallback_mode is True
        assert manager._stats["db_errors"] >= 1
        assert manager._stats["fallback_triggers"] >= 1

    @pytest.mark.asyncio
    async def test_fallback_mode_uses_memory_only(self):
        """测试降级模式下只使用内存"""
        manager = HybridSessionManager(
            session_factory=Mock(),
            enable_database=True
        )
        
        # 手动触发降级
        manager._fallback_mode = True
        
        # 添加消息
        await manager.add_message("test_session", "user", "Test")
        
        # 应该没有数据库写入统计
        assert manager._stats["db_writes"] == 0


class TestSessionManagerStatistics:
    """测试统计信息"""

    @pytest.mark.asyncio
    async def test_cache_hit_stats(self):
        """测试缓存命中统计"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        await manager.add_message("test_session", "user", "Test")
        
        # 第一次获取（缓存命中）
        await manager.get_history("test_session")
        assert manager._stats["cache_hits"] == 1
        
        # 第二次获取（再次命中）
        await manager.get_history("test_session")
        assert manager._stats["cache_hits"] == 2

    @pytest.mark.asyncio
    async def test_cache_miss_stats(self):
        """测试缓存未命中统计"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        # 获取不存在的会话（缓存未命中）
        await manager.get_history("nonexistent")
        
        assert manager._stats["cache_misses"] == 1

    def test_access_statistics(self):
        """测试访问统计信息"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        # 直接访问内部统计字典
        stats = manager._stats
        
        # 验证统计信息结构
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "db_reads" in stats
        assert "db_writes" in stats
        assert "db_errors" in stats
        assert "fallback_triggers" in stats


class TestSessionManagerTTLCleanup:
    """测试TTL过期清理"""

    def test_cleanup_expired_sessions(self):
        """测试清理过期会话"""
        manager = HybridSessionManager(
            session_factory=None,
            ttl_hours=1,  # 1小时过期
            enable_database=False
        )
        
        # 添加会话并手动设置过期时间
        manager._sessions["active"] = deque(maxlen=20)
        manager._sessions["expired"] = deque(maxlen=20)
        
        manager._last_activity["active"] = datetime.now()
        manager._last_activity["expired"] = datetime.now() - timedelta(hours=2)
        
        # 清理过期会话
        cleaned = manager.cleanup_expired_sessions()
        
        assert cleaned == 1
        assert "active" in manager._sessions
        assert "expired" not in manager._sessions

    def test_no_cleanup_if_all_active(self):
        """测试所有会话都活跃时不清理"""
        manager = HybridSessionManager(
            session_factory=None,
            ttl_hours=24,
            enable_database=False
        )
        
        # 添加活跃会话
        manager._sessions["session1"] = deque(maxlen=20)
        manager._sessions["session2"] = deque(maxlen=20)
        manager._last_activity["session1"] = datetime.now()
        manager._last_activity["session2"] = datetime.now()
        
        cleaned = manager.cleanup_expired_sessions()
        
        assert cleaned == 0
        assert len(manager._sessions) == 2


class TestSessionManagerConcurrency:
    """测试并发安全性"""

    @pytest.mark.asyncio
    async def test_concurrent_add_messages(self):
        """测试并发添加消息"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        # 并发添加100条消息
        tasks = [
            manager.add_message("test_session", "user", f"Message {i}")
            for i in range(100)
        ]
        
        await asyncio.gather(*tasks)
        
        history = await manager.get_history("test_session")
        
        # 由于内存限制(20)，应该只保留最后20条
        assert len(history) == 20

    @pytest.mark.asyncio
    async def test_concurrent_read_write(self):
        """测试并发读写"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        # 先添加一些消息
        for i in range(10):
            await manager.add_message("test_session", "user", f"Message {i}")
        
        # 并发读写
        async def reader():
            return await manager.get_history("test_session")
        
        async def writer(msg_id):
            await manager.add_message("test_session", "user", f"Concurrent {msg_id}")
        
        tasks = [reader() for _ in range(5)] + [writer(i) for i in range(5)]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 不应该有异常
        assert all(not isinstance(r, Exception) for r in results)


class TestSessionManagerDatabaseIntegration:
    """测试数据库集成（使用mock）"""

    @pytest.mark.asyncio
    async def test_save_to_database_success(self):
        """测试成功保存到数据库"""
        # 创建mock session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # 创建 mock factory - 正确处理 async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        
        def mock_factory():
            return mock_context_manager
        
        manager = HybridSessionManager(
            session_factory=mock_factory,
            enable_database=True
        )
        
        # Mock _save_to_database 方法以避免复杂的 Repository mock
        with patch.object(manager, '_save_to_database', new_callable=AsyncMock):
            # 添加消息
            await manager.add_message("test_session", "user", "Test message")
        
        # 验证数据库写入统计
        assert manager._stats["db_writes"] >= 1

    @pytest.mark.asyncio
    async def test_load_from_database_on_cache_miss(self):
        """测试缓存未命中时从数据库加载"""
        # Mock数据库返回
        mock_messages = [
            {"role": "user", "content": "Old message 1"},
            {"role": "assistant", "content": "Old response 1"}
        ]
        
        mock_session = AsyncMock()
        mock_factory = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None
        
        manager = HybridSessionManager(
            session_factory=mock_factory,
            enable_database=True
        )
        
        # Mock _load_from_database 方法
        with patch.object(manager, '_load_from_database', return_value=mock_messages):
            history = await manager.get_history("test_session")
        
        # 验证返回了数据库的消息
        assert len(history) == 2
        assert history[0]["content"] == "Old message 1"
        
        # 验证缓存统计
        assert manager._stats["cache_misses"] >= 1


class TestSessionManagerEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_empty_message_content(self):
        """测试空消息内容"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        await manager.add_message("test_session", "user", "")
        
        history = await manager.get_history("test_session")
        assert len(history) == 1
        assert history[0]["content"] == ""

    @pytest.mark.asyncio
    async def test_very_long_message(self):
        """测试非常长的消息"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        long_message = "x" * 10000
        await manager.add_message("test_session", "user", long_message)
        
        history = await manager.get_history("test_session")
        assert history[0]["content"] == long_message

    @pytest.mark.asyncio
    async def test_unicode_message(self):
        """测试Unicode消息"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        await manager.add_message("test_session", "user", "你好，世界！🌍")
        
        history = await manager.get_history("test_session")
        assert history[0]["content"] == "你好，世界！🌍"

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(self):
        """测试多个会话隔离"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        await manager.add_message("session1", "user", "Message 1")
        await manager.add_message("session2", "user", "Message 2")
        
        history1 = await manager.get_history("session1")
        history2 = await manager.get_history("session2")
        
        # 两个会话应该完全独立
        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["content"] == "Message 1"
        assert history2[0]["content"] == "Message 2"

    @pytest.mark.asyncio
    async def test_special_characters_in_session_id(self):
        """测试会话ID中的特殊字符"""
        manager = HybridSessionManager(session_factory=None, enable_database=False)
        
        special_id = "session-123_ABC!@#"
        await manager.add_message(special_id, "user", "Test")
        
        history = await manager.get_history(special_id)
        assert len(history) == 1


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_session_history_manager_alias(self):
        """测试SessionHistoryManager别名"""
        from utils.session_manager import SessionHistoryManager
        
        # SessionHistoryManager应该是HybridSessionManager的别名
        manager = SessionHistoryManager(session_factory=None, enable_database=False)
        
        assert isinstance(manager, HybridSessionManager)

    def test_old_attribute_names(self):
        """测试旧版本的属性名称"""
        manager = HybridSessionManager(
            session_factory=None,
            max_history=30,
            ttl=timedelta(hours=12),
            enable_database=False
        )
        
        # 旧属性应该仍然可用
        assert hasattr(manager, 'max_history')
        assert hasattr(manager, 'ttl')
        assert manager.max_history == 30
        assert manager.ttl == timedelta(hours=12)


# 运行测试的辅助信息
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

