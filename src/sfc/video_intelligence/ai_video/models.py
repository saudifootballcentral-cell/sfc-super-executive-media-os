"""AI video generation result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class AIVideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AIVideoResult:
    """Result from one AI video generation task."""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    provider: str = ""
    scene_id: str = ""
    status: AIVideoStatus = AIVideoStatus.PENDING
    public_url: str = ""
    local_path: str = ""
    duration_seconds: float = 0.0
    error_message: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == AIVideoStatus.COMPLETED and bool(self.public_url or self.local_path)
