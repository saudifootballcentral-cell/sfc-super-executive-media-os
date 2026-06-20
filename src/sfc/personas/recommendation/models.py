from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    task_type: str
    content_type: str = ""
    audience: str = ""
    platform: str = ""
    war_room_type: str = ""
    campaign_type: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class PersonaRecommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: f"REC-{uuid4().hex[:6].upper()}")
    request: RecommendationRequest
    recommended_persona_ids: list[str]
    recommended_team: list[str]
    confidence_score: float
    expected_impact: dict[str, float]
    rationale: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
