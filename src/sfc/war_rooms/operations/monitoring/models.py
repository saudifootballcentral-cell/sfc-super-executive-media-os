"""Real-Time Monitoring Center — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MonitoringDomain(str, Enum):
    AGENTS = "agents"
    TOOLS = "tools"
    PLATFORMS = "platforms"
    WAR_ROOMS = "war_rooms"
    CAMPAIGNS = "campaigns"
    REVENUE = "revenue"
    AUDIENCE = "audience"
    PUBLISHING = "publishing"
    ANALYTICS = "analytics"
    TRENDS = "trends"


class MonitoringAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    domain: MonitoringDomain
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    metric_value: float
    threshold: float
    raised_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_notes: str = ""


class HealthReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    overall_health: float = 100.0
    domain_health: dict[str, float] = Field(default_factory=dict)
    active_alerts: list[MonitoringAlert] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class TrendReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    trending_topics: list[str] = Field(default_factory=list)
    sentiment_trend: str = "neutral"
    audience_growth_pct: float = 0.0
    engagement_rate: float = 0.0
    revenue_trend: str = "stable"
