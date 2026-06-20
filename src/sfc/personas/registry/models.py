from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from sfc.personas.shared.types import PersonaCategory, PersonaStatus


class PersonaFilter(BaseModel):
    category: PersonaCategory | None = None
    status: PersonaStatus | None = None
    min_performance_score: float = 0.0
    capabilities: list[str] = Field(default_factory=list)


class RegistryReport(BaseModel):
    total_personas: int
    by_category: dict[str, int]
    by_status: dict[str, int]
    avg_performance_score: float
    generated_at: datetime
