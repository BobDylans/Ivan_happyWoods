"""
Prometheus Metrics Exporter

将 Observability 指标导出到 Prometheus 格式。

特性：
- 自动从 Observability 收集指标
- 支持 Counter 和 Gauge 类型
- 支持标签 (labels)
- 与现有 Observability 无缝集成
"""

import logging
from typing import Dict, Any, Optional
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


class PrometheusExporter:
    """
    Prometheus 指标导出器
    
    将 Observability 收集的指标导出为 Prometheus 格式
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None, namespace: str = "voice_agent"):
        """
        初始化 Prometheus 导出器
        
        Args:
            registry: Prometheus 注册表 (None = 使用默认)
            namespace: 指标命名空间前缀
        """
        self.registry = registry or CollectorRegistry()
        self.namespace = namespace
        
        # 存储已创建的 Prometheus 指标
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        
        logger.info(f"✅ PrometheusExporter 初始化: namespace={namespace}")
    
    def register_counter(self, name: str, description: str, labels: Optional[list] = None) -> Counter:
        """
        注册一个 Counter 指标
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
        
        Returns:
            Counter 对象
        """
        full_name = f"{self.namespace}_{name}"
        
        if full_name in self._counters:
            return self._counters[full_name]
        
        counter = Counter(
            full_name,
            description,
            labelnames=labels or [],
            registry=self.registry
        )
        
        self._counters[full_name] = counter
        logger.debug(f"📊 注册 Counter: {full_name}")
        
        return counter
    
    def register_gauge(self, name: str, description: str, labels: Optional[list] = None) -> Gauge:
        """
        注册一个 Gauge 指标
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
        
        Returns:
            Gauge 对象
        """
        full_name = f"{self.namespace}_{name}"
        
        if full_name in self._gauges:
            return self._gauges[full_name]
        
        gauge = Gauge(
            full_name,
            description,
            labelnames=labels or [],
            registry=self.registry
        )
        
        self._gauges[full_name] = gauge
        logger.debug(f"📊 注册 Gauge: {full_name}")
        
        return gauge
    
    def register_histogram(self, name: str, description: str, labels: Optional[list] = None, buckets: Optional[tuple] = None) -> Histogram:
        """
        注册一个 Histogram 指标
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            buckets: 直方图桶边界
        
        Returns:
            Histogram 对象
        """
        full_name = f"{self.namespace}_{name}"
        
        if full_name in self._histograms:
            return self._histograms[full_name]
        
        histogram = Histogram(
            full_name,
            description,
            labelnames=labels or [],
            buckets=buckets or (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        self._histograms[full_name] = histogram
        logger.debug(f"📊 注册 Histogram: {full_name}")
        
        return histogram
    
    def update_from_observability(self, observability) -> None:
        """
        从 Observability 更新 Prometheus 指标
        
        Args:
            observability: Observability 实例
        """
        if not observability:
            return
        
        # 获取计数器快照
        counters_snapshot = observability.counters_snapshot()
        
        # 处理计数器数据
        # 格式: {"metric[label1=value1,label2=value2]": count} 或 {"metric": count}
        for key, value in counters_snapshot.items():
            if '[' in key and ']' in key:
                # 有标签的计数器: "metric[label1=value1,label2=value2]"
                metric_name, labels_str = key.split('[', 1)
                labels_str = labels_str.rstrip(']')
                self._update_counter_with_labels_str(metric_name, labels_str, value)
            else:
                # 无标签的计数器
                self._update_counter(metric_name, value)
    
    def _update_counter(self, name: str, value: float) -> None:
        """更新无标签的计数器"""
        counter = self.register_counter(name, f"Counter for {name}")
        
        # Prometheus Counter 只能递增，计算差值
        current = counter._value.get()
        if value > current:
            counter.inc(value - current)
    
    def _update_counter_with_labels_str(self, name: str, labels_str: str, value: float) -> None:
        """更新有标签的计数器（从字符串格式标签）
        
        Args:
            name: 指标名称
            labels_str: 标签字符串，格式 "label1=value1,label2=value2"
            value: 计数器值
        """
        # 解析标签字符串
        label_names = []
        label_values = []
        
        if labels_str:
            for label_pair in labels_str.split(','):
                if '=' in label_pair:
                    k, v = label_pair.split('=', 1)
                    label_names.append(k.strip())
                    label_values.append(v.strip())
        
        if not label_names:
            # 没有标签，当作普通计数器
            self._update_counter(name, value)
            return
        
        # 注册或获取计数器
        counter = self.register_counter(name, f"Counter for {name}", label_names)
        
        # 更新带标签的计数器
        labeled_counter = counter.labels(*label_values)
        current = labeled_counter._value.get()
        if value > current:
            labeled_counter.inc(value - current)
    
    
    def export_metrics(self) -> bytes:
        """
        导出 Prometheus 格式的指标
        
        Returns:
            Prometheus 文本格式的指标数据
        """
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """
        获取 Prometheus 指标的 Content-Type
        
        Returns:
            Content-Type 字符串
        """
        return CONTENT_TYPE_LATEST


# 全局实例 (可选)
_default_exporter: Optional[PrometheusExporter] = None


def get_default_exporter() -> PrometheusExporter:
    """获取默认的 PrometheusExporter 实例"""
    global _default_exporter
    if _default_exporter is None:
        _default_exporter = PrometheusExporter()
    return _default_exporter


def reset_default_exporter() -> None:
    """重置默认的 PrometheusExporter 实例 (主要用于测试)"""
    global _default_exporter
    _default_exporter = None

