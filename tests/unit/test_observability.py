"""
测试 Observability 模块

本测试套件验证可观测性模块的核心功能，包括：
- 计数器（Counter）
- 观测值（Gauge/Observation）
- 同步和异步计时追踪
- 标签处理
- 快照生成
"""

import asyncio
import logging
import pytest
import time
from unittest.mock import Mock, patch

from core.observability import Observability


class TestObservabilityCounters:
    """测试计数器功能"""

    def test_increment_basic(self):
        """测试基础计数功能"""
        obs = Observability()
        
        obs.increment("http_requests")
        obs.increment("http_requests")
        obs.increment("http_requests")
        
        snapshot = obs.counters_snapshot()
        assert snapshot["http_requests"] == 3

    def test_increment_with_value(self):
        """测试指定增量的计数"""
        obs = Observability()
        
        obs.increment("tokens_used", value=100)
        obs.increment("tokens_used", value=250)
        
        snapshot = obs.counters_snapshot()
        assert snapshot["tokens_used"] == 350

    def test_increment_with_labels(self):
        """测试带标签的计数"""
        obs = Observability()
        
        obs.increment("http_requests", method="GET", endpoint="/api/chat")
        obs.increment("http_requests", method="POST", endpoint="/api/chat")
        obs.increment("http_requests", method="GET", endpoint="/api/chat")
        
        snapshot = obs.counters_snapshot()
        assert snapshot["http_requests[endpoint=/api/chat,method=GET]"] == 2
        assert snapshot["http_requests[endpoint=/api/chat,method=POST]"] == 1

    def test_increment_multiple_metrics(self):
        """测试多个不同的计数器"""
        obs = Observability()
        
        obs.increment("http_requests")
        obs.increment("llm_calls")
        obs.increment("tool_executions")
        obs.increment("http_requests")
        
        snapshot = obs.counters_snapshot()
        assert snapshot["http_requests"] == 2
        assert snapshot["llm_calls"] == 1
        assert snapshot["tool_executions"] == 1

    def test_increment_zero_value(self):
        """测试零值增量"""
        obs = Observability()
        
        obs.increment("test_counter", value=0)
        
        snapshot = obs.counters_snapshot()
        assert snapshot.get("test_counter", 0) == 0

    def test_increment_negative_value(self):
        """测试负值增量（用于递减）"""
        obs = Observability()
        
        obs.increment("active_connections", value=5)
        obs.increment("active_connections", value=-2)
        
        snapshot = obs.counters_snapshot()
        assert snapshot["active_connections"] == 3


class TestObservabilitySnapshot:
    """测试快照生成功能"""

    def test_empty_snapshot(self):
        """测试空快照"""
        obs = Observability()
        snapshot = obs.counters_snapshot()
        assert snapshot == {}

    def test_snapshot_format(self):
        """测试快照格式正确性"""
        obs = Observability()
        
        obs.increment("metric_a", x="1", y="2")
        snapshot = obs.counters_snapshot()
        
        # 标签应该按字母顺序排列
        assert "metric_a[x=1,y=2]" in snapshot

    def test_snapshot_immutability(self):
        """测试快照是独立的副本"""
        obs = Observability()
        
        obs.increment("counter")
        snapshot1 = obs.counters_snapshot()
        
        obs.increment("counter")
        snapshot2 = obs.counters_snapshot()
        
        # 第一个快照不应该变化
        assert snapshot1["counter"] == 1
        assert snapshot2["counter"] == 2


class TestObservabilityObservations:
    """测试观测值记录功能"""

    def test_observe_basic(self, caplog):
        """测试基础观测值记录"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            obs.observe("response_time", 123.45)
        
        # 检查日志输出
        assert any("METRIC" in record.message for record in caplog.records)
        assert any("response_time" in record.message for record in caplog.records)

    def test_observe_with_labels(self, caplog):
        """测试带标签的观测值"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            obs.observe("latency", 50.5, endpoint="/api/chat", status="success")
        
        # 验证标签被记录
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        assert len(metric_logs) > 0
        assert "endpoint" in metric_logs[0]
        assert "status" in metric_logs[0]

    def test_observe_various_value_types(self, caplog):
        """测试不同类型的观测值"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            obs.observe("int_metric", 100)
            obs.observe("float_metric", 123.456)
            obs.observe("zero_metric", 0)
        
        assert len([r for r in caplog.records if "METRIC" in r.message]) == 3


class TestObservabilityTracking:
    """测试同步计时追踪功能"""

    def test_track_successful_execution(self, caplog):
        """测试成功执行的计时"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            with obs.track("operation_duration"):
                time.sleep(0.01)  # 模拟耗时操作
        
        # 检查记录了 success 状态
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        assert any("success" in log for log in metric_logs)
        
        # 检查记录的时间 > 10ms
        import json
        for log in metric_logs:
            if "METRIC" in log:
                data = json.loads(log.split("METRIC ")[1])
                if data.get("metric") == "operation_duration":
                    assert data["value"] >= 10.0

    def test_track_failed_execution(self, caplog):
        """测试失败执行的计时"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            with pytest.raises(ValueError):
                with obs.track("failed_operation"):
                    raise ValueError("Test error")
        
        # 检查记录了 error 状态
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        assert any("error" in log for log in metric_logs)

    def test_track_with_labels(self, caplog):
        """测试带标签的计时"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            with obs.track("api_call", endpoint="/test", method="GET"):
                time.sleep(0.001)
        
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        assert any("endpoint" in log for log in metric_logs)
        assert any("method" in log for log in metric_logs)


class TestObservabilityAsyncTracking:
    """测试异步计时追踪功能"""

    @pytest.mark.asyncio
    async def test_track_async_successful(self, caplog):
        """测试异步成功执行的计时"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            async with obs.track_async("async_operation"):
                await asyncio.sleep(0.01)
        
        # 检查记录了 success 状态
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        assert any("success" in log for log in metric_logs)

    @pytest.mark.asyncio
    async def test_track_async_failed(self, caplog):
        """测试异步失败执行的计时"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            with pytest.raises(RuntimeError):
                async with obs.track_async("async_failed"):
                    raise RuntimeError("Async error")
        
        # 检查记录了 error 状态
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        assert any("error" in log for log in metric_logs)

    @pytest.mark.asyncio
    async def test_track_async_with_labels(self, caplog):
        """测试带标签的异步计时"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            async with obs.track_async("db_query", table="users", operation="select"):
                await asyncio.sleep(0.001)
        
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        assert any("table" in log for log in metric_logs)
        assert any("operation" in log for log in metric_logs)


class TestObservabilityInternals:
    """测试内部辅助方法"""

    def test_label_tuple_ordering(self):
        """测试标签元组排序"""
        obs = Observability()
        
        # 标签应该按字母顺序排序
        tuple1 = obs._label_tuple({"z": "3", "a": "1", "m": "2"})
        assert tuple1 == (("a", "1"), ("m", "2"), ("z", "3"))

    def test_label_tuple_empty(self):
        """测试空标签"""
        obs = Observability()
        
        tuple1 = obs._label_tuple({})
        assert tuple1 == ()

    def test_label_tuple_consistency(self):
        """测试相同标签生成相同元组"""
        obs = Observability()
        
        tuple1 = obs._label_tuple({"x": "1", "y": "2"})
        tuple2 = obs._label_tuple({"y": "2", "x": "1"})
        
        # 不同顺序应该生成相同的元组
        assert tuple1 == tuple2


class TestObservabilityLogging:
    """测试日志记录功能"""

    def test_custom_logger(self, caplog):
        """测试使用自定义日志记录器"""
        custom_logger = logging.getLogger("custom_obs")
        obs = Observability(logger=custom_logger)
        
        with caplog.at_level(logging.INFO, logger="custom_obs"):
            obs.increment("test_metric")
        
        # 验证使用了自定义 logger
        assert any(r.name == "custom_obs" for r in caplog.records)

    def test_default_logger(self, caplog):
        """测试默认日志记录器"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            obs.increment("test_metric")
        
        # 验证使用了默认 logger
        assert any("observability" in r.name for r in caplog.records)

    def test_log_metric_json_format(self, caplog):
        """测试日志输出为有效的JSON格式"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            obs.observe("test_value", 42.5, tag="test")
        
        import json
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        
        # 解析JSON应该成功
        for log in metric_logs:
            json_str = log.split("METRIC ")[1]
            data = json.loads(json_str)
            assert "metric" in data
            assert "kind" in data
            assert "value" in data
            assert "labels" in data


class TestObservabilityEdgeCases:
    """测试边界情况和特殊场景"""

    def test_large_counter_value(self):
        """测试大数值计数"""
        obs = Observability()
        
        large_value = 10**9
        obs.increment("big_counter", value=large_value)
        
        snapshot = obs.counters_snapshot()
        assert snapshot["big_counter"] == large_value

    def test_many_labels(self, caplog):
        """测试大量标签"""
        obs = Observability()
        
        labels = {f"label_{i}": f"value_{i}" for i in range(20)}
        
        with caplog.at_level(logging.INFO):
            obs.increment("multi_label_metric", **labels)
        
        # 应该成功记录
        assert any("METRIC" in r.message for r in caplog.records)

    def test_special_characters_in_labels(self):
        """测试标签中的特殊字符"""
        obs = Observability()
        
        obs.increment("metric", path="/api/v1/users/{id}", method="GET")
        
        snapshot = obs.counters_snapshot()
        # 应该能正常处理特殊字符
        assert any("{id}" in key for key in snapshot.keys())

    def test_unicode_in_labels(self, caplog):
        """测试Unicode字符处理"""
        obs = Observability()
        
        with caplog.at_level(logging.INFO):
            obs.increment("requests", user="用户123", endpoint="/聊天")
        
        # 应该能正确记录中文
        metric_logs = [r.message for r in caplog.records if "METRIC" in r.message]
        assert any("用户" in log for log in metric_logs)

    def test_concurrent_increments(self):
        """测试并发计数（基础测试，非线程安全保证）"""
        obs = Observability()
        
        # 模拟多次增量
        for _ in range(100):
            obs.increment("concurrent_counter")
        
        snapshot = obs.counters_snapshot()
        assert snapshot["concurrent_counter"] == 100


# 运行测试的辅助信息
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

