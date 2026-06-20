from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryNamespace(str, Enum):
    GLOBAL = "global"
    DIVISION = "division"
    WORKING = "working"
    EPISODIC = "episodic"


class KnowledgeSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: f"SNAP-{uuid4().hex[:6].upper()}")
    persona_id: str
    namespace: MemoryNamespace
    content: dict[str, Any]
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LearningRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: f"LEARN-{uuid4().hex[:6].upper()}")
    persona_id: str
    lesson: str
    context: dict[str, Any] = Field(default_factory=dict)
    quality_score: float = 0.8
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class ContextPackage(BaseModel):
    package_id: str = Field(default_factory=lambda: f"CTX-{uuid4().hex[:6].upper()}")
    persona_id: str
    task_type: str
    snapshots: list[KnowledgeSnapshot] = Field(default_factory=list)
    active_learnings: list[LearningRecord] = Field(default_factory=list)
    assembled_at: datetime = Field(default_factory=datetime.utcnow)
