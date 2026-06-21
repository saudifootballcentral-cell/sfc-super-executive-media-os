"""Operational reporting models — war room, platform, persona, analytics, revenue, governance."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class OperationalReportType(str, Enum):
    WAR_ROOM = "war_room"
    PLATFORM = "platform"
    PERSONA = "persona"
    ANALYTICS = "analytics"
    REVENUE = "revenue"
    GOVERNANCE = "governance"
    INFRASTRUCTURE = "infrastructure"


class OperationalReport(BaseModel):
    """Operational report — machine-readable with multi-format export."""

    report_id: str = Field(default_factory=lambda: str(uuid4()))
    report_type: OperationalReportType
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    title: str = ""
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    alerts: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    status: str = "ok"  # ok / warning / critical

    model_config = {"frozen": False}

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            f"**Type:** {self.report_type.value} | **Status:** {self.status}",
            f"**Generated:** {self.generated_at.isoformat()}",
            "",
            f"## Summary",
            self.summary or "_No summary._",
            "",
        ]
        if self.metrics:
            lines += ["## Metrics"]
            for k, v in self.metrics.items():
                lines.append(f"- **{k}:** {v:.2f}")
            lines.append("")
        if self.alerts:
            lines += ["## Alerts"] + [f"- ⚠️ {a}" for a in self.alerts] + [""]
        if self.recommendations:
            lines += ["## Recommendations"] + [f"- {r}" for r in self.recommendations] + [""]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_dashboard_data(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "type": self.report_type.value,
            "status": self.status,
            "title": self.title,
            "summary": self.summary,
            "metrics": self.metrics,
            "alerts": self.alerts,
            "generated_at": self.generated_at.isoformat(),
        }
