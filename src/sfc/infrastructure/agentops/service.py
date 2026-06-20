"""AgentOps Infrastructure Service — unified agent lifecycle and observability."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any

from sfc.agentops.registries import AgentRegistry, PromptRegistry, ToolRegistry
from sfc.agentops.registries import CapabilityRegistry as AgentOpsCapabilityRegistry
from sfc.agentops.monitors import HealthMonitor, CostMonitor, QualityMonitor
from sfc.infrastructure.shared.types import (
    AuditEntry,
    ComponentHealth,
    HealthStatus,
)

logger = logging.getLogger("sfc.infrastructure.agentops")


class AgentOpsService:
    """Unified agent lifecycle and observability service.

    Wraps the existing sfc.agentops.* registries and monitors into a
    single cohesive service accessible through InfrastructureContext.
    """

    def __init__(self) -> None:
        # Registries
        self.agent_registry: AgentRegistry = AgentRegistry()
        self.prompt_registry: PromptRegistry = PromptRegistry()
        self.capability_registry: AgentOpsCapabilityRegistry = AgentOpsCapabilityRegistry()
        self.tool_registry: ToolRegistry = ToolRegistry()
        self.memory_registry: dict[str, Any] = {}
        self.event_registry: dict[str, Any] = {}
        self.audit_registry: list[AuditEntry] = []

        # Monitors
        self.health_monitor: HealthMonitor = HealthMonitor()
        self.cost_monitor: CostMonitor = CostMonitor()
        self.quality_monitor: QualityMonitor = QualityMonitor()

        # Internal tracking
        self._call_counts: dict[str, int] = defaultdict(int)
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.RLock()

    async def initialize(self) -> None:
        """Initialize the AgentOps service."""
        logger.info("[AgentOpsService] Initialized")

    def record_call(
        self,
        component: str,
        success: bool,
        latency_ms: float,
        cost_usd: float = 0.0,
    ) -> None:
        """Record a component call for health + cost tracking."""
        with self._lock:
            self._call_counts[component] += 1
            self._latencies[component].append(latency_ms)

        self.health_monitor.record_call(component, latency_ms, success)
        if cost_usd > 0:
            self.cost_monitor.record_cost(component, cost_usd)

        logger.debug(
            "[AgentOpsService] Call recorded: %s success=%s latency=%.1fms cost=$%.4f",
            component,
            success,
            latency_ms,
            cost_usd,
        )

    def audit(
        self,
        component: str,
        action: str,
        run_id: str,
        payload: dict[str, Any] | None = None,
        success: bool = True,
    ) -> AuditEntry:
        """Append an audit entry to the registry."""
        entry = AuditEntry(
            component=component,
            action=action,
            run_id=run_id,
            payload=payload or {},
            success=success,
            timestamp=datetime.utcnow(),
        )
        with self._lock:
            self.audit_registry.append(entry)
        logger.debug("[AgentOpsService] Audit: %s/%s run=%s", component, action, run_id)
        return entry

    def health_report(self) -> dict[str, ComponentHealth]:
        """System-wide health from all monitors."""
        report: dict[str, ComponentHealth] = {}
        with self._lock:
            components = list(self._call_counts.keys()) or ["agentops"]

        for component in components:
            score = self.health_monitor.health_score(component)
            avg_latency = self.health_monitor.avg_latency_ms(component)

            if score >= 90:
                status = HealthStatus.HEALTHY
            elif score >= 70:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            report[component] = ComponentHealth(
                component=component,
                status=status,
                last_check=datetime.utcnow(),
                metrics={
                    "health_score": score,
                    "avg_latency_ms": avg_latency,
                    "total_calls": self._call_counts.get(component, 0),
                },
            )

        if not report:
            report["agentops"] = ComponentHealth(
                component="agentops",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow(),
                metrics={"health_score": 100.0, "total_calls": 0},
            )

        return report

    def cost_report(self) -> dict[str, Any]:
        """Aggregated cost breakdown by provider."""
        return self.cost_monitor.report()

    def optimization_report(self) -> list[str]:
        """Recommendations to reduce cost / improve reliability."""
        recommendations: list[str] = []
        cost_data = self.cost_monitor.report()
        total_cost = cost_data.get("total_cost_usd", 0.0)

        if total_cost > 0.10:
            recommendations.append(
                f"Cost per run ${total_cost:.3f} exceeds $0.10 target. "
                "Consider switching LLM calls to claude_haiku for non-critical tasks."
            )

        with self._lock:
            for component, latencies in self._latencies.items():
                if latencies:
                    avg_lat = sum(latencies) / len(latencies)
                    if avg_lat > 5000:
                        recommendations.append(
                            f"Component '{component}' avg latency {avg_lat:.0f}ms exceeds 5s SLO. "
                            "Investigate bottlenecks or add caching."
                        )

        quality_data = self.quality_monitor.report()
        if quality_data.get("hallucination_rate", 0) > 0.05:
            recommendations.append(
                "Hallucination rate >5%. Review prompt templates and add fact-check steps."
            )

        if not recommendations:
            recommendations.append("All metrics within SLO bounds. No immediate optimizations needed.")

        return recommendations

    def health_check(self) -> ComponentHealth:
        """Return health of the AgentOps service itself."""
        try:
            audit_count = len(self.audit_registry)
            agent_count = self.agent_registry.count
            return ComponentHealth(
                component="agentops",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow(),
                metrics={
                    "audit_entries": audit_count,
                    "registered_agents": agent_count,
                    "total_cost_usd": self.cost_monitor.total_cost(),
                },
            )
        except Exception as exc:  # noqa: BLE001
            return ComponentHealth(
                component="agentops",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                metrics={},
                errors=[str(exc)],
            )
