"""In-memory metrics collector for infrastructure services."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from sfc.infrastructure.shared.types import MetricPoint


class MetricsCollector:
    """Simple thread-safe in-memory metrics collector."""

    def __init__(self) -> None:
        self._points: list[MetricPoint] = []
        self._lock = threading.RLock()

    def record(
        self,
        name: str,
        value: float,
        unit: str = "count",
        component: str = "",
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a metric data point."""
        point = MetricPoint(
            name=name,
            value=value,
            unit=unit,
            component=component,
            timestamp=datetime.utcnow(),
            labels=labels or {},
        )
        with self._lock:
            self._points.append(point)

    def get_metrics(self, component: str | None = None) -> list[MetricPoint]:
        """Return all metrics, optionally filtered by component."""
        with self._lock:
            if component is None:
                return list(self._points)
            return [p for p in self._points if p.component == component]

    def get_summary(self) -> dict[str, Any]:
        """Return aggregated summary by metric name."""
        with self._lock:
            summary: dict[str, dict[str, Any]] = {}
            for point in self._points:
                if point.name not in summary:
                    summary[point.name] = {
                        "count": 0,
                        "total": 0.0,
                        "min": float("inf"),
                        "max": float("-inf"),
                        "unit": point.unit,
                        "component": point.component,
                    }
                s = summary[point.name]
                s["count"] += 1
                s["total"] += point.value
                s["min"] = min(s["min"], point.value)
                s["max"] = max(s["max"], point.value)

            # Compute averages
            for name, s in summary.items():
                s["avg"] = s["total"] / s["count"] if s["count"] > 0 else 0.0
                if s["min"] == float("inf"):
                    s["min"] = 0.0
                if s["max"] == float("-inf"):
                    s["max"] = 0.0

            return summary

    def reset(self) -> None:
        """Clear all recorded metrics."""
        with self._lock:
            self._points.clear()


_collector: MetricsCollector | None = None
_collector_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Return the process-wide singleton MetricsCollector."""
    global _collector
    if _collector is None:
        with _collector_lock:
            if _collector is None:
                _collector = MetricsCollector()
    return _collector
