"""
分布式追踪配置模块

集成 OpenTelemetry 和 Jaeger，提供请求跟踪和性能监控能力。

使用方式：
    from src.core.tracing import setup_tracing

    @app.on_event("startup")
    async def startup():
        setup_tracing()
"""

import os
import logging
from typing import Optional
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

logger = logging.getLogger(__name__)


class TracingConfig:
    """追踪配置"""

    # Jaeger 配置
    JAEGER_HOST = os.getenv("JAEGER_HOST", "localhost")
    JAEGER_PORT = int(os.getenv("JAEGER_PORT", 6831))
    SERVICE_NAME = os.getenv("SERVICE_NAME", "voice-agent")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    # 采样率（0.0-1.0）
    SAMPLE_RATE = float(os.getenv("TRACE_SAMPLE_RATE", "1.0"))

    # 批处理配置
    BATCH_SIZE = int(os.getenv("TRACE_BATCH_SIZE", "512"))
    MAX_QUEUE_SIZE = int(os.getenv("TRACE_MAX_QUEUE_SIZE", "2048"))
    SCHEDULE_DELAY_MILLIS = int(os.getenv("TRACE_SCHEDULE_DELAY_MILLIS", "5000"))


def setup_tracing() -> None:
    """
    设置分布式追踪

    配置 OpenTelemetry 和 Jaeger 导出器，启用对 FastAPI、SQLAlchemy
    和 HTTP 请求的自动插桩。
    """
    logger.info("🔍 Setting up distributed tracing with Jaeger...")

    try:
        # 1. 创建资源
        resource = Resource(
            attributes={
                SERVICE_NAME: TracingConfig.SERVICE_NAME,
                "environment": TracingConfig.ENVIRONMENT,
                "version": "0.4.0",
            }
        )

        # 2. 配置 Jaeger 导出器
        jaeger_exporter = JaegerExporter(
            agent_host_name=TracingConfig.JAEGER_HOST,
            agent_port=TracingConfig.JAEGER_PORT,
        )

        # 3. 创建 TracerProvider
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                jaeger_exporter,
                max_queue_size=TracingConfig.MAX_QUEUE_SIZE,
                max_export_batch_size=TracingConfig.BATCH_SIZE,
                schedule_delay_millis=TracingConfig.SCHEDULE_DELAY_MILLIS,
            )
        )

        # 4. 设置全局 TracerProvider
        trace.set_tracer_provider(tracer_provider)

        # 5. 启用自动插桩
        # FastAPI 自动插桩
        FastAPIInstrumentor().instrument()

        # SQLAlchemy 自动插桩
        SQLAlchemyInstrumentor().instrument()

        # HTTP Requests 自动插桩
        RequestsInstrumentor().instrument()

        logger.info(f"✅ Tracing initialized successfully")
        logger.info(f"   Service: {TracingConfig.SERVICE_NAME}")
        logger.info(f"   Jaeger: {TracingConfig.JAEGER_HOST}:{TracingConfig.JAEGER_PORT}")
        logger.info(f"   Environment: {TracingConfig.ENVIRONMENT}")
        logger.info(f"   Jaeger UI: http://{TracingConfig.JAEGER_HOST}:16686")

    except Exception as e:
        logger.error(f"❌ Failed to setup tracing: {e}")
        logger.warning("Continuing without distributed tracing...")


def get_tracer(name: str) -> trace.Tracer:
    """获取 Tracer 实例"""
    return trace.get_tracer(name)


@contextmanager
def trace_span(name: str, attributes: Optional[dict] = None):
    """
    Context manager for creating a span.

    使用示例：
        with trace_span("process_message", {"user_id": "123"}):
            # 业务逻辑代码
            pass
    """
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


class SpanHelper:
    """Span 辅助类"""

    @staticmethod
    def set_status(span, success: bool, error_msg: Optional[str] = None):
        """设置 Span 状态"""
        if success:
            span.set_attribute("status", "success")
        else:
            span.set_attribute("status", "error")
            if error_msg:
                span.set_attribute("error", error_msg)

    @staticmethod
    def set_user_context(span, user_id: str, session_id: str):
        """设置用户上下文"""
        span.set_attribute("user_id", user_id)
        span.set_attribute("session_id", session_id)

    @staticmethod
    def set_llm_context(span, model: str, tokens: int):
        """设置 LLM 上下文"""
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.tokens_used", tokens)

    @staticmethod
    def set_tool_context(span, tool_name: str, success: bool):
        """设置工具上下文"""
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.success", success)


# 预定义的 Span 名称常量
class SpanNames:
    """Span 名称常量"""

    # API 层
    SEND_MESSAGE = "api.send_message"
    PROCESS_MESSAGE = "agent.process_message"

    # Agent 层
    BUILD_MESSAGES = "agent.build_messages"
    CALL_LLM = "agent.call_llm"
    STREAM_LLM = "agent.stream_llm"
    HANDLE_TOOLS = "agent.handle_tools"
    FORMAT_RESPONSE = "agent.format_response"

    # 工具层
    EXECUTE_TOOL = "tool.execute"
    WEB_SEARCH = "tool.web_search"

    # RAG 层
    RAG_RETRIEVE = "rag.retrieve"
    RAG_INGEST = "rag.ingest"

    # 数据库层
    DB_QUERY = "db.query"
    DB_SAVE = "db.save"
