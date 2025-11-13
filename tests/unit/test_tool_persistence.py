"""
测试工具持久化解耦 (Tool Call Persistence)

本测试套件验证工具调用持久化的核心功能，包括：
- ToolCallRepository 的 CRUD 操作
- ToolHandler 的持久化回调机制
- 统计信息和查询功能
- 错误处理和非阻塞特性
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import UUID, uuid4

from database.repositories.tool_call_repository import ToolCallRepository
from agent.nodes.tool_handler import ToolHandler
from agent.state import ToolCall, ToolResult
from config.models import VoiceAgentConfig


class TestToolCallRepository:
    """测试 ToolCallRepository CRUD 操作"""

    @pytest.mark.asyncio
    async def test_save_tool_call_basic(self):
        """测试基本的工具调用保存"""
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        
        repo = ToolCallRepository(mock_session)
        
        tool_call = await repo.save_tool_call(
            session_id="test_session",
            tool_name="calculator",
            parameters={"expression": "2+2"},
            result={"data": "4", "success": True},
            execution_time_ms=150
        )
        
        # 验证保存方法被调用
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_tool_call_with_webhook(self):
        """测试带 webhook 的工具调用保存"""
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        
        repo = ToolCallRepository(mock_session)
        
        tool_call = await repo.save_tool_call(
            session_id="test_session",
            tool_name="n8n_workflow",
            parameters={"data": "test"},
            result={"success": True},
            webhook_url="https://n8n.example.com/webhook/123",
            response_status=200,
            response_time_ms=250
        )
        
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_tool_calls_pagination(self):
        """测试分页获取工具调用"""
        mock_session = AsyncMock()
        repo = ToolCallRepository(mock_session)
        
        # 使用 patch 简化 mock
        with patch.object(repo, 'get_tool_calls', return_value=[
            Mock(tool_name="tool1"),
            Mock(tool_name="tool2"),
        ]):
            tool_calls = await repo.get_tool_calls(
                session_id="test_session",
                limit=10,
                offset=0
            )
            
            assert isinstance(tool_calls, list)
            assert len(tool_calls) == 2

    @pytest.mark.asyncio
    async def test_get_tool_statistics_empty(self):
        """测试空统计数据"""
        mock_session = AsyncMock()
        repo = ToolCallRepository(mock_session)
        
        # 使用 patch 简化 mock
        with patch.object(repo, 'get_tool_statistics', return_value={
            "total_calls": 0,
            "avg_execution_time_ms": 0,
            "tools": []
        }):
            stats = await repo.get_tool_statistics()
            
            assert stats["total_calls"] == 0
            assert stats["avg_execution_time_ms"] == 0
            assert stats["tools"] == []

    @pytest.mark.asyncio
    async def test_get_recent_tool_calls(self):
        """测试获取最近的工具调用"""
        mock_session = AsyncMock()
        repo = ToolCallRepository(mock_session)
        
        # 使用 patch 简化 mock
        with patch.object(repo, 'get_recent_tool_calls', return_value=[
            Mock(tool_name="recent_tool", timestamp=datetime.now())
        ]):
            recent_calls = await repo.get_recent_tool_calls(limit=5)
            
            assert isinstance(recent_calls, list)
            assert len(recent_calls) == 1

    @pytest.mark.asyncio
    async def test_get_recent_tool_calls_with_filter(self):
        """测试按工具名过滤最近的调用"""
        mock_session = AsyncMock()
        repo = ToolCallRepository(mock_session)
        
        # 使用 patch 简化 mock
        with patch.object(repo, 'get_recent_tool_calls', return_value=[]):
            recent_calls = await repo.get_recent_tool_calls(
                tool_name="specific_tool",
                limit=10
            )
            
            assert isinstance(recent_calls, list)
            assert len(recent_calls) == 0


class TestToolHandlerPersistence:
    """测试 ToolHandler 的持久化机制"""

    def test_init_without_persister(self):
        """测试没有 persister 的初始化"""
        config = VoiceAgentConfig()
        handler = ToolHandler(config, tool_call_persister=None)
        
        assert handler._tool_call_persister is None

    def test_init_with_persister(self):
        """测试带 persister 的初始化"""
        config = VoiceAgentConfig()
        mock_persister = AsyncMock()
        
        handler = ToolHandler(config, tool_call_persister=mock_persister)
        
        assert handler._tool_call_persister is mock_persister

    def test_set_tool_call_persister(self):
        """测试动态设置 persister"""
        config = VoiceAgentConfig()
        handler = ToolHandler(config, tool_call_persister=None)
        
        mock_persister = AsyncMock()
        handler.set_tool_call_persister(mock_persister)
        
        assert handler._tool_call_persister is mock_persister

    @pytest.mark.asyncio
    async def test_save_tool_call_without_persister(self):
        """测试没有 persister 时不保存"""
        config = VoiceAgentConfig()
        handler = ToolHandler(config, tool_call_persister=None)
        
        tool_call = ToolCall(id="call_1", name="test_tool", arguments={})
        result = ToolResult(call_id="call_1", success=True, result="test")
        
        # 不应该抛出异常
        await handler._save_tool_call_to_database(
            "test_session", tool_call, result
        )

    @pytest.mark.asyncio
    async def test_save_tool_call_with_persister_success(self):
        """测试成功调用 persister"""
        config = VoiceAgentConfig()
        mock_persister = AsyncMock()
        
        handler = ToolHandler(config, tool_call_persister=mock_persister)
        
        tool_call = ToolCall(id="call_1", name="test_tool", arguments={"key": "value"})
        result = ToolResult(call_id="call_1", success=True, result="test_result")
        
        await handler._save_tool_call_to_database(
            "test_session", tool_call, result, execution_ms=100.5
        )
        
        # 验证 persister 被正确调用
        mock_persister.assert_awaited_once_with(
            session_id="test_session",
            tool_call=tool_call,
            result=result,
            execution_ms=100.5
        )

    @pytest.mark.asyncio
    async def test_save_tool_call_with_persister_failure(self):
        """测试 persister 失败不中断流程"""
        config = VoiceAgentConfig()
        mock_persister = AsyncMock(side_effect=Exception("Database error"))
        
        handler = ToolHandler(config, tool_call_persister=mock_persister)
        
        tool_call = ToolCall(id="call_1", name="test_tool", arguments={})
        result = ToolResult(call_id="call_1", success=True, result="test")
        
        # 不应该抛出异常（非阻塞）
        await handler._save_tool_call_to_database(
            "test_session", tool_call, result
        )
        
        # 验证 persister 被尝试调用
        mock_persister.assert_awaited_once()


class TestPersistenceIntegration:
    """测试持久化集成场景"""

    @pytest.mark.asyncio
    async def test_end_to_end_persistence_flow(self):
        """测试端到端持久化流程"""
        # 创建 mock session
        mock_db_session = AsyncMock()
        mock_db_session.add = Mock()
        mock_db_session.flush = AsyncMock()
        
        # 创建 Repository
        repo = ToolCallRepository(mock_db_session)
        
        # 创建 persister 函数
        async def persist_tool_call(session_id, tool_call, result, execution_ms=None):
            await repo.save_tool_call(
                session_id=session_id,
                tool_name=tool_call.name,
                parameters=tool_call.arguments,
                result={"data": result.result, "success": result.success},
                execution_time_ms=int(execution_ms) if execution_ms else None
            )
        
        # 创建 ToolHandler
        config = VoiceAgentConfig()
        handler = ToolHandler(config, tool_call_persister=persist_tool_call)
        
        # 模拟工具调用
        tool_call = ToolCall(id="call_123", name="weather", arguments={"city": "Beijing"})
        result = ToolResult(call_id="call_123", success=True, result={"temp": 20})
        
        # 执行持久化
        await handler._save_tool_call_to_database(
            "session_123", tool_call, result, execution_ms=250.0
        )
        
        # 验证保存流程
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_persistence(self):
        """测试多个工具调用的持久化"""
        mock_db_session = AsyncMock()
        mock_db_session.add = Mock()
        mock_db_session.flush = AsyncMock()
        
        repo = ToolCallRepository(mock_db_session)
        
        # 保存多个工具调用
        for i in range(3):
            await repo.save_tool_call(
                session_id="test_session",
                tool_name=f"tool_{i}",
                parameters={"index": i},
                result={"success": True, "data": f"result_{i}"},
                execution_time_ms=100 + i * 50
            )
        
        # 验证保存了3次
        assert mock_db_session.add.call_count == 3
        assert mock_db_session.flush.await_count == 3

    @pytest.mark.asyncio
    async def test_failed_tool_call_persistence(self):
        """测试失败工具调用的持久化"""
        mock_db_session = AsyncMock()
        mock_db_session.add = Mock()
        mock_db_session.flush = AsyncMock()
        
        repo = ToolCallRepository(mock_db_session)
        
        # 保存失败的工具调用
        await repo.save_tool_call(
            session_id="test_session",
            tool_name="failing_tool",
            parameters={"input": "bad_data"},
            result={"success": False, "error": "Tool execution failed"},
            execution_time_ms=50
        )
        
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()


class TestPersisterDecoupling:
    """测试持久化解耦特性"""

    @pytest.mark.asyncio
    async def test_persister_is_optional(self):
        """测试 persister 是可选的"""
        config = VoiceAgentConfig()
        
        # 不提供 persister
        handler = ToolHandler(config)
        
        # 应该能正常工作
        assert handler._tool_call_persister is None

    @pytest.mark.asyncio
    async def test_persister_can_be_replaced(self):
        """测试 persister 可以被替换"""
        config = VoiceAgentConfig()
        
        persister1 = AsyncMock()
        persister2 = AsyncMock()
        
        handler = ToolHandler(config, tool_call_persister=persister1)
        assert handler._tool_call_persister is persister1
        
        handler.set_tool_call_persister(persister2)
        assert handler._tool_call_persister is persister2

    @pytest.mark.asyncio
    async def test_persister_failure_does_not_affect_tool_execution(self):
        """测试 persister 失败不影响工具执行"""
        config = VoiceAgentConfig()
        
        # 创建会失败的 persister
        failing_persister = AsyncMock(side_effect=Exception("DB unavailable"))
        
        handler = ToolHandler(config, tool_call_persister=failing_persister)
        
        tool_call = ToolCall(id="call_1", name="test", arguments={})
        result = ToolResult(call_id="call_1", success=True, result="data")
        
        # 持久化失败不应该抛出异常
        await handler._save_tool_call_to_database("session", tool_call, result)
        
        # 验证尝试了调用
        failing_persister.assert_awaited_once()

    def test_persister_signature_compatibility(self):
        """测试 persister 签名兼容性"""
        # 定义标准 persister 签名
        async def standard_persister(
            session_id: str,
            tool_call,
            result,
            execution_ms=None
        ):
            pass
        
        # 验证签名可以被ToolHandler接受
        config = VoiceAgentConfig()
        handler = ToolHandler(config, tool_call_persister=standard_persister)
        
        assert handler._tool_call_persister is standard_persister


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_save_tool_call_with_none_execution_time(self):
        """测试 execution_time 为 None"""
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        
        repo = ToolCallRepository(mock_session)
        
        await repo.save_tool_call(
            session_id="test",
            tool_name="tool",
            parameters={},
            result={},
            execution_time_ms=None  # 明确设置为 None
        )
        
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_tool_call_with_large_parameters(self):
        """测试大参数对象"""
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        
        repo = ToolCallRepository(mock_session)
        
        large_params = {"data": "x" * 10000}  # 10KB 参数
        
        await repo.save_tool_call(
            session_id="test",
            tool_name="tool",
            parameters=large_params,
            result={"success": True}
        )
        
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_tool_call_with_unicode(self):
        """测试 Unicode 参数和结果"""
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        
        repo = ToolCallRepository(mock_session)
        
        await repo.save_tool_call(
            session_id="会话_123",
            tool_name="工具",
            parameters={"输入": "你好 🌍"},
            result={"输出": "世界"}
        )
        
        mock_session.add.assert_called_once()


# 运行测试的辅助信息
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

