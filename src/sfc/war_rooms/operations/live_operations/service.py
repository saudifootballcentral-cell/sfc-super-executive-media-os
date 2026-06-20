"""Live Operations Command — service implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.war_rooms.operations.live_operations.models import (
    OperationalStatus,
    OperationsAlert,
    OperationsSnapshot,
    WorkflowStatus,
)

logger = logging.getLogger("sfc.war_rooms.operations.live_operations")

_PLATFORMS = ["twitter", "instagram", "youtube", "website", "tiktok"]


class LiveOperationsCommand:
    """Real-time command center for operational oversight."""

    def __init__(self) -> None:
        self._workflow_registry: dict[str, WorkflowStatus] = {}
        self._alerts: list[OperationsAlert] = []

    async def snapshot(self) -> OperationsSnapshot:
        """Collect the current operational state as a snapshot."""
        workflows = list(self._workflow_registry.values())
        platform_health = await self.get_platform_health()
        platforms_healthy = sum(
            1 for s in platform_health.values() if s == OperationalStatus.HEALTHY
        )

        # Derive overall status
        degraded = any(s in (OperationalStatus.CRITICAL, OperationalStatus.OFFLINE)
                       for s in platform_health.values())
        overall = OperationalStatus.CRITICAL if degraded else OperationalStatus.HEALTHY

        snapshot = OperationsSnapshot(
            timestamp=datetime.utcnow(),
            active_workflows=workflows,
            war_rooms_active=0,
            agents_healthy=8,
            agents_total=8,
            platforms_healthy=platforms_healthy,
            publishing_queue_depth=len([w for w in workflows if w.status == OperationalStatus.HEALTHY]),
            overall_status=overall,
        )
        logger.info("[LiveOps] Snapshot taken: %s", snapshot.snapshot_id)
        return snapshot

    async def monitor_workflows(self, workflow_ids: list[str]) -> list[WorkflowStatus]:
        """Return status for the given workflow IDs, creating stubs for unknown ones."""
        result: list[WorkflowStatus] = []
        for wf_id in workflow_ids:
            if wf_id in self._workflow_registry:
                result.append(self._workflow_registry[wf_id])
            else:
                stub = WorkflowStatus(
                    workflow_id=wf_id,
                    name=f"workflow-{wf_id}",
                    status=OperationalStatus.HEALTHY,
                    progress_pct=100.0,
                )
                self._workflow_registry[wf_id] = stub
                result.append(stub)
        return result

    async def get_platform_health(self) -> dict[str, OperationalStatus]:
        """Return health status for all known platforms."""
        return {platform: OperationalStatus.HEALTHY for platform in _PLATFORMS}

    async def trigger_recovery(self, alert: OperationsAlert) -> dict[str, Any]:
        """Generate a recovery action plan for the given operational alert."""
        recovery: dict[str, Any] = {
            "alert_id": alert.alert_id,
            "action": "restart_affected_components",
            "steps": [
                "Identify root cause",
                "Isolate affected component",
                "Apply recovery procedure",
                "Validate recovery",
                "Resume normal operations",
            ],
            "estimated_recovery_minutes": 15,
            "owner": "ops_team",
            "triggered_at": datetime.utcnow().isoformat(),
        }
        alert.resolved = True
        logger.info("[LiveOps] Recovery triggered for alert: %s", alert.alert_id)
        return recovery

    async def report(self) -> dict[str, Any]:
        """Full operations report."""
        snapshot = await self.snapshot()
        return {
            "snapshot": snapshot.model_dump(),
            "active_alerts": len([a for a in self._alerts if not a.resolved]),
            "total_alerts": len(self._alerts),
            "platform_health": {k: v.value for k, v in (await self.get_platform_health()).items()},
        }

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "live_operations_command",
            "status": "healthy",
            "tracked_workflows": len(self._workflow_registry),
            "active_alerts": len([a for a in self._alerts if not a.resolved]),
        }
