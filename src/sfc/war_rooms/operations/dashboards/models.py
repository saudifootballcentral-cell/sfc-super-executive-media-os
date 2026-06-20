"""Operational Dashboard Layer — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DashboardType(str, Enum):
    EXECUTIVE = "executive"
    OPERATIONS = "operations"
    WAR_ROOM = "war_room"
    PUBLISHING = "publishing"
    ANALYTICS = "analytics"
    REVENUE = "revenue"
    AGENTOPS = "agentops"
    MONITORING = "monitoring"


class WidgetData(BaseModel):
    widget_id: str
    title: str
    value: Any
    unit: str = ""
    status: str = "ok"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Dashboard(BaseModel):
    dashboard_id: str = Field(default_factory=lambda: str(uuid4()))
    dashboard_type: DashboardType
    title: str
    widgets: list[WidgetData] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    refresh_interval_seconds: int = 30
