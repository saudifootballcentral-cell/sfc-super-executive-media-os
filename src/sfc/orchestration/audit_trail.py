"""AuditTrail — structured, immutable log of every orchestration action."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


class AuditEntry:
    __slots__ = ("entry_id", "timestamp", "run_id", "stage", "action", "actor", "details", "severity")

    def __init__(
        self,
        run_id: str,
        stage: str,
        action: str,
        actor: str = "system",
        details: dict[str, Any] | None = None,
        severity: str = "info",
    ) -> None:
        self.entry_id = str(uuid4())
        self.timestamp = datetime.utcnow()
        self.run_id = run_id
        self.stage = stage
        self.action = action
        self.actor = actor
        self.details: dict[str, Any] = details or {}
        self.severity = severity  # info | warning | error | critical

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "run_id": self.run_id,
            "stage": self.stage,
            "action": self.action,
            "actor": self.actor,
            "details": self.details,
            "severity": self.severity,
        }


class AuditTrail:
    """Append-only, in-process audit trail for a single orchestration run."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._entries: list[AuditEntry] = []

    def log(
        self,
        stage: str,
        action: str,
        actor: str = "system",
        details: dict[str, Any] | None = None,
        severity: str = "info",
    ) -> AuditEntry:
        entry = AuditEntry(
            run_id=self._run_id,
            stage=stage,
            action=action,
            actor=actor,
            details=details,
            severity=severity,
        )
        self._entries.append(entry)
        return entry

    def log_stage_start(self, stage: str) -> None:
        self.log(stage=stage, action=f"stage_started:{stage}")

    def log_stage_complete(self, stage: str, duration_ms: float = 0.0) -> None:
        self.log(stage=stage, action=f"stage_completed:{stage}", details={"duration_ms": duration_ms})

    def log_stage_fail(self, stage: str, error: str) -> None:
        self.log(stage=stage, action=f"stage_failed:{stage}", details={"error": error}, severity="error")

    def log_stage_skip(self, stage: str, reason: str = "") -> None:
        self.log(stage=stage, action=f"stage_skipped:{stage}", details={"reason": reason}, severity="warning")

    def log_approval(self, stage: str, approved: bool, actor: str = "system", reason: str = "") -> None:
        action = "approval_granted" if approved else "approval_denied"
        self.log(stage=stage, action=action, actor=actor, details={"reason": reason})

    def log_recovery(self, stage: str, strategy: str, attempt: int) -> None:
        self.log(
            stage=stage,
            action="recovery_attempted",
            details={"strategy": strategy, "attempt": attempt},
            severity="warning",
        )

    def log_governance(self, decision: str, content_count: int, rejected_count: int) -> None:
        self.log(
            stage="governance",
            action=f"governance_{decision}",
            details={"content_count": content_count, "rejected_count": rejected_count},
        )

    def entries(self, severity: str | None = None) -> list[AuditEntry]:
        if severity is None:
            return list(self._entries)
        return [e for e in self._entries if e.severity == severity]

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._entries]

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def has_errors(self) -> bool:
        return any(e.severity in ("error", "critical") for e in self._entries)
