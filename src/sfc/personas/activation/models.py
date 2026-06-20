from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from sfc.personas.shared.types import PersonaActivation


class ActivationTrigger(str, Enum):
    CONTENT_REQUEST = "content_request"
    CAMPAIGN_REQUEST = "campaign_request"
    MATCH_DAY = "match_day"
    WORLD_CUP = "world_cup"
    TRANSFER_WINDOW = "transfer_window"
    BREAKING_NEWS = "breaking_news"
    SPONSOR_OPPORTUNITY = "sponsor_opportunity"
    GROWTH_INITIATIVE = "growth_initiative"
    EXECUTIVE_REQUEST = "executive_request"


class ActivationPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"APLAN-{uuid4().hex[:6].upper()}")
    trigger: ActivationTrigger
    selected_personas: list[str]
    dependency_order: list[str]
    conflicts_detected: list[str]
    warnings: list[str]
    estimated_cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ActivationDecision(BaseModel):
    approved: bool
    plan: ActivationPlan
    rationale: str
    activated_personas: list[PersonaActivation]
