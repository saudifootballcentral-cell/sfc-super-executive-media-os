"""World Cup War Room models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorldCupPhase(str, Enum):
    PRE_TOURNAMENT = "pre_tournament"
    GROUP_STAGE = "group_stage"
    KNOCKOUT = "knockout"
    FINAL_WEEK = "final_week"
    POST_TOURNAMENT = "post_tournament"


class NationalTeamMonitor(BaseModel):
    team: str = "Saudi Arabia"
    group: str | None = None
    current_phase: WorldCupPhase = WorldCupPhase.PRE_TOURNAMENT
    results: list[dict[str, Any]] = []
    next_match: dict[str, Any] = {}
    squad: list[str] = []
    key_narratives: list[str] = []


class WorldCupBrief(BaseModel):
    phase: WorldCupPhase
    national_team: NationalTeamMonitor
    opponent_report: dict[str, Any] = {}
    narrative_opportunities: list[str] = []
    sponsor_activations: list[dict[str, Any]] = []
    daily_content_plan: list[dict[str, Any]] = []
    executive_report: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
