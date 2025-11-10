"""
Observability utilities for lightweight metrics and structured logging.

This module provides a small helper that can be injected into services to
record counters and durations without introducing heavy dependencies. The goal
is to surface key operational signals (HTTP latency, tool execution time, RAG
retrieval counts, etc.) while keeping the integration minimal.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, Iterable, Optional, Tuple


class Observability:
    """Lightweight metrics recorder with structured logging output."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("observability")
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], int] = defaultdict(int)

    # --------------------------------------------------------------------- #
    # Counter helpers
    # --------------------------------------------------------------------- #
    def increment(self, metric: str, value: int = 1, **labels: Any) -> None:
        """Increment a counter metric."""
        key = (metric, self._label_tuple(labels))
        self._counters[key] += value
        self._log_metric(metric, "counter", value, labels)

    def counters_snapshot(self) -> Dict[str, int]:
        """Return a flattened snapshot of counters for diagnostics."""
        snapshot: Dict[str, int] = {}
        for (metric, label_tuple), value in self._counters.items():
            label_repr = ",".join(f"{key}={val}" for key, val in label_tuple)
            full_key = f"{metric}[{label_repr}]" if label_tuple else metric
            snapshot[full_key] = value
        return snapshot

    # --------------------------------------------------------------------- #
    # Timing helpers
    # --------------------------------------------------------------------- #
    def observe(self, metric: str, value: float, **labels: Any) -> None:
        """Record a gauge/observation metric."""
        self._log_metric(metric, "observation", value, labels)

    @contextmanager
    def track(self, metric: str, **labels: Any) -> Iterable[None]:
        """Context manager to record synchronous duration in milliseconds."""
        start = time.perf_counter()
        try:
            yield
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            self.observe(metric, elapsed, status="error", **labels)
            raise
        else:
            elapsed = (time.perf_counter() - start) * 1000
            self.observe(metric, elapsed, status="success", **labels)

    @asynccontextmanager
    async def track_async(self, metric: str, **labels: Any) -> Iterable[None]:
        """Async context manager to record duration in milliseconds."""
        start = time.perf_counter()
        try:
            yield
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            self.observe(metric, elapsed, status="error", **labels)
            raise
        else:
            elapsed = (time.perf_counter() - start) * 1000
            self.observe(metric, elapsed, status="success", **labels)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _label_tuple(self, labels: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
        return tuple(sorted(labels.items()))

    def _log_metric(self, metric: str, kind: str, value: Any, labels: Dict[str, Any]) -> None:
        event = {
            "metric": metric,
            "kind": kind,
            "value": value,
            "labels": labels,
        }
        self.logger.info("METRIC %s", json.dumps(event, ensure_ascii=False))


__all__ = ["Observability"]

