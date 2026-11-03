"""Lightweight distributed tracing and latency instrumentation."""

from contextlib import contextmanager
import functools
import time
from typing import Any, Callable, Dict, Generator, Optional
from backend.app.observability.metrics import get_metrics_collector


@contextmanager
def trace_span(operation_name: str, **attributes) -> Generator[Dict[str, Any], None, None]:
    """Context manager measuring execution time and recording to metrics collector."""
    metrics = get_metrics_collector()
    span_data: Dict[str, Any] = {"operation": operation_name, "start_time": time.perf_counter(), **attributes}
    try:
        yield span_data
    finally:
        elapsed = time.perf_counter() - span_data["start_time"]
        span_data["duration_sec"] = elapsed
        span_data["duration_ms"] = elapsed * 1000

        # Feed specific operation categories into metrics registry
        if operation_name == "rag_retrieval":
            metrics.record_rag_retrieval(elapsed)
        elif operation_name == "llm_inference":
            metrics.record_llm_response(elapsed)
        elif operation_name.startswith("tool_"):
            tool_name = operation_name.replace("tool_", "", 1)
            metrics.record_tool_execution(tool_name, elapsed)


def trace_operation(operation_name: Optional[str] = None):
    """Decorator for tracing function latency."""
    def decorator(func: Callable):
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_span(op_name):
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_span(op_name):
                return await func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
