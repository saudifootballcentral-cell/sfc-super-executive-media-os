"""Executive reporting models — typed report structures for all time periods."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ReportPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    DASHBOARD = "dashboard"


class ReportSection(BaseModel):
    """A named section in an executive report."""

    title: str
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"


class ExecutiveKPI(BaseModel):
    """A single executive KPI with comparison."""

    name: str
    current_value: float
    previous_value: float | None = None
    unit: str = ""
    trend: str = "stable"  # up / down / stable
    change_pct: float = 0.0
    target: float | None = None
    on_track: bool = True


class ExecutiveReport(BaseModel):
    """Full executive report structure — renderable to markdown, JSON, or PDF."""

    report_id: str = Field(default_factory=lambda: str(uuid4()))
    period: ReportPeriod
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    period_start: datetime | None = None
    period_end: datetime | None = None

    # Mandatory sections (spec requirement)
    executive_summary: str = ""
    key_wins: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # AI and cost
    ai_usage: dict[str, Any] = Field(default_factory=dict)
    cost_summary: dict[str, Any] = Field(default_factory=dict)

    # Operational summaries
    war_room_summary: dict[str, Any] = Field(default_factory=dict)
    persona_summary: dict[str, Any] = Field(default_factory=dict)
    revenue_summary: dict[str, Any] = Field(default_factory=dict)
    governance_summary: dict[str, Any] = Field(default_factory=dict)

    # KPIs
    kpis: list[ExecutiveKPI] = Field(default_factory=list)

    # Additional sections
    sections: list[ReportSection] = Field(default_factory=list)

    # Content stats
    content_published: int = 0
    content_rejected: int = 0
    total_reach: int = 0
    total_revenue_opportunity_usd: float = 0.0

    # AI-generated insight
    ai_insights: str = ""

    model_config = {"frozen": False}

    def to_markdown(self) -> str:
        lines = [
            f"# SFC Executive Report — {self.period.value.capitalize()}",
            f"**Generated:** {self.generated_at.isoformat()}",
            f"**Report ID:** {self.report_id}",
            "",
            "## Executive Summary",
            self.executive_summary or "_No summary generated._",
            "",
            "## Key Wins",
            *[f"- {w}" for w in self.key_wins],
            "",
            "## Key Risks",
            *[f"- {r}" for r in self.key_risks],
            "",
            "## Opportunities",
            *[f"- {o}" for o in self.opportunities],
            "",
            "## Recommendations",
            *[f"- {r}" for r in self.recommendations],
            "",
            "## KPIs",
        ]
        for kpi in self.kpis:
            trend_sym = "↑" if kpi.trend == "up" else ("↓" if kpi.trend == "down" else "→")
            lines.append(
                f"- **{kpi.name}:** {kpi.current_value:.1f}{kpi.unit} {trend_sym} "
                f"({kpi.change_pct:+.1f}%)"
            )
        lines += [
            "",
            "## AI Usage",
            f"- Total cost: ${self.cost_summary.get('session_total_usd', 0):.4f}",
            f"- Calls: {self.ai_usage.get('total_calls', 0)}",
            f"- Fallback rate: {self.ai_usage.get('fallback_rate_pct', 0):.1f}%",
            "",
            "## Revenue Summary",
            f"- Total opportunity: ${self.total_revenue_opportunity_usd:,.0f}",
            "",
        ]
        if self.ai_insights:
            lines += ["## AI Insights", self.ai_insights, ""]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
