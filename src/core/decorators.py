"""
装饰器模块

提供用于追踪、性能监测等的装饰器。
"""

import functools
import logging
import time
from typing import Callable, Any, Optional, Dict

logger = logging.getLogger(__name__)


def traced(span_name: Optional[str] = None):
    """
    为异步函数添加分布式追踪

    使用示例：
        @traced("send_message")
        async def send_text_message(request: ConversationRequest):
            # 函数体
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            from core.tracing import get_tracer, SpanNames

            # 确定span名称
            name = span_name or f"{func.__module__}.{func.__name__}"
            tracer = get_tracer(__name__)

            with tracer.start_as_current_span(name) as span:
                try:
                    # 记录函数参数（敏感信息需要过滤）
                    if kwargs:
                        # 只记录关键参数，避免泄露敏感信息
                        safe_kwargs = {
                            k: v for k, v in kwargs.items()
                            if k not in ['password', 'token', 'secret']
                        }
                        span.set_attribute("kwargs", str(safe_kwargs))

                    # 执行函数
                    result = await func(*args, **kwargs)

                    # 标记为成功
                    span.set_attribute("status", "success")
                    return result

                except Exception as e:
                    # 记录错误
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    logger.error(f"Error in {name}: {e}")
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            from core.tracing import get_tracer

            # 确定span名称
            name = span_name or f"{func.__module__}.{func.__name__}"
            tracer = get_tracer(__name__)

            with tracer.start_as_current_span(name) as span:
                try:
                    # 记录函数参数
                    if kwargs:
                        safe_kwargs = {
                            k: v for k, v in kwargs.items()
                            if k not in ['password', 'token', 'secret']
                        }
                        span.set_attribute("kwargs", str(safe_kwargs))

                    # 执行函数
                    result = func(*args, **kwargs)

                    # 标记为成功
                    span.set_attribute("status", "success")
                    return result

                except Exception as e:
                    # 记录错误
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    logger.error(f"Error in {name}: {e}")
                    raise

        # 根据函数类型选择合适的wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def monitor_performance(func: Callable) -> Callable:
    """
    监测函数性能（耗时）

    使用示例：
        @monitor_performance
        async def call_llm(message: str):
            # 函数体
            pass
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        from core.tracing import get_tracer

        start_time = time.time()
        tracer = get_tracer(__name__)

        name = f"{func.__module__}.{func.__name__}"
        with tracer.start_as_current_span(name) as span:
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", elapsed_ms)
                span.set_attribute("status", "success")

                if elapsed_ms > 1000:  # 超过1秒时警告
                    logger.warning(f"{name} took {elapsed_ms:.2f}ms")

                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", elapsed_ms)
                span.set_attribute("status", "error")
                span.set_attribute("error", str(e))
                raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        from core.tracing import get_tracer

        start_time = time.time()
        tracer = get_tracer(__name__)

        name = f"{func.__module__}.{func.__name__}"
        with tracer.start_as_current_span(name) as span:
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", elapsed_ms)
                span.set_attribute("status", "success")
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", elapsed_ms)
                span.set_attribute("status", "error")
                raise

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    on_retry: Optional[Callable] = None
):
    """
    带重试逻辑的装饰器

    使用示例：
        @retry_on_error(max_retries=3, delay=1.0)
        async def call_llm(message: str):
            # 函数体
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            from core.tracing import get_tracer

            tracer = get_tracer(__name__)
            last_error = None
            current_delay = delay

            for attempt in range(1, max_retries + 1):
                try:
                    with tracer.start_as_current_span(
                        f"{func.__name__}:attempt_{attempt}"
                    ) as span:
                        span.set_attribute("attempt", attempt)
                        return await func(*args, **kwargs)

                except Exception as e:
                    last_error = e
                    span.set_attribute("error", str(e))

                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )

                        if on_retry:
                            on_retry(attempt, e, current_delay)

                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed for {func.__name__}: {e}"
                        )

            raise last_error

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            import time
            from core.tracing import get_tracer

            tracer = get_tracer(__name__)
            last_error = None
            current_delay = delay

            for attempt in range(1, max_retries + 1):
                try:
                    with tracer.start_as_current_span(
                        f"{func.__name__}:attempt_{attempt}"
                    ) as span:
                        span.set_attribute("attempt", attempt)
                        return func(*args, **kwargs)

                except Exception as e:
                    last_error = e
                    span.set_attribute("error", str(e))

                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )

                        if on_retry:
                            on_retry(attempt, e, current_delay)

                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed for {func.__name__}: {e}"
                        )

            raise last_error

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
