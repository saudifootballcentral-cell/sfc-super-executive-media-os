from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class RoutingIntent(str, Enum):
    CONTENT_CREATION = "content_creation"
    DATA_ANALYSIS = "data_analysis"
    GOVERNANCE_REVIEW = "governance_review"
    REVENUE_OPPORTUNITY = "revenue_opportunity"
    STRATEGIC_PLANNING = "strategic_planning"
    BREAKING_NEWS = "breaking_news"
    CAMPAIGN_EXECUTION = "campaign_execution"
    COLLABORATION = "collaboration"


class RoutingDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"ROUTE-{uuid4().hex[:6].upper()}")
    intent: RoutingIntent
    primary_persona_id: str
    supporting_persona_ids: list[str]
    priority: str = "medium"
    rationale: str
    confidence: float
    decided_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"EXEC-{uuid4().hex[:6].upper()}")
    routing_decision: RoutingDecision
    steps: list[dict]
    estimated_duration_ms: int = 500
    created_at: datetime = Field(default_factory=datetime.utcnow)
