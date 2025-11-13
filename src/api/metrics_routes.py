"""
Prometheus Metrics API Routes

提供 /metrics 端点供 Prometheus 抓取指标数据。
"""

import logging
from fastapi import APIRouter, Response, Depends
from typing import Optional

from core.prometheus_exporter import PrometheusExporter
from core.observability import Observability
from core.dependencies import get_observability

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metrics"])

# 全局 Prometheus 导出器实例
_prometheus_exporter: Optional[PrometheusExporter] = None


def get_prometheus_exporter() -> PrometheusExporter:
    """获取 Prometheus 导出器实例"""
    global _prometheus_exporter
    if _prometheus_exporter is None:
        _prometheus_exporter = PrometheusExporter(namespace="voice_agent")
        logger.info("✅ Prometheus Exporter 已初始化")
    return _prometheus_exporter


def set_prometheus_exporter(exporter: PrometheusExporter) -> None:
    """设置 Prometheus 导出器实例 (用于依赖注入)"""
    global _prometheus_exporter
    _prometheus_exporter = exporter


@router.get("/metrics")
async def metrics_endpoint(
    observability: Observability = Depends(get_observability)
) -> Response:
    """
    Prometheus 指标端点
    
    返回 Prometheus 文本格式的指标数据
    
    Returns:
        Response: Prometheus 格式的指标数据
    """
    try:
        exporter = get_prometheus_exporter()
        
        # 从 Observability 更新指标
        if observability:
            exporter.update_from_observability(observability)
        
        # 导出指标
        metrics_data = exporter.export_metrics()
        
        return Response(
            content=metrics_data,
            media_type=exporter.get_content_type()
        )
    
    except Exception as e:
        logger.error(f"❌ 导出 Prometheus 指标失败: {e}", exc_info=True)
        return Response(
            content=f"# Error exporting metrics: {str(e)}\n",
            media_type="text/plain",
            status_code=500
        )


@router.get("/health/prometheus")
async def prometheus_health() -> dict:
    """
    Prometheus 集成健康检查
    
    Returns:
        dict: 健康状态
    """
    try:
        exporter = get_prometheus_exporter()
        return {
            "status": "healthy",
            "prometheus_enabled": True,
            "namespace": exporter.namespace,
            "registered_metrics": {
                "counters": len(exporter._counters),
                "gauges": len(exporter._gauges),
                "histograms": len(exporter._histograms)
            }
        }
    except Exception as e:
        logger.error(f"❌ Prometheus 健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "prometheus_enabled": False,
            "error": str(e)
        }

