"""Models for the Memory Manager infrastructure service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryQuery(BaseModel):
    """Query object for retrieving memory entries."""

    namespace: str
    key: str | None = None
    query: str | None = None
    division: str | None = None
    limit: int = 10


class MemoryEntry(BaseModel):
    """A single entry in the memory system."""

    namespace: str
    key: str
    value: Any
    division: str | None = None
    stored_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
