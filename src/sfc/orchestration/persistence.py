"""Persistence providers for orchestration run state."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from sfc.orchestration.master_state import MasterState


class PersistenceProvider(ABC):
    """Abstract base for storing and retrieving MasterState snapshots."""

    @abstractmethod
    async def save(self, state: MasterState) -> None: ...

    @abstractmethod
    async def load(self, run_id: str) -> MasterState | None: ...

    @abstractmethod
    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def delete(self, run_id: str) -> None: ...


class InMemoryPersistence(PersistenceProvider):
    """In-process store — default; lost on restart."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []

    async def save(self, state: MasterState) -> None:
        data = state.model_dump(mode="json")
        self._store[state.run_id] = data
        if state.run_id not in self._order:
            self._order.append(state.run_id)

    async def load(self, run_id: str) -> MasterState | None:
        data = self._store.get(run_id)
        if data is None:
            return None
        return MasterState.model_validate(data)

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        recent = self._order[-limit:]
        return [self._store[rid] for rid in reversed(recent) if rid in self._store]

    async def delete(self, run_id: str) -> None:
        self._store.pop(run_id, None)
        try:
            self._order.remove(run_id)
        except ValueError:
            pass

    @property
    def run_count(self) -> int:
        return len(self._store)


class JSONLAuditPersistence(PersistenceProvider):
    """Append-only JSONL file — survives restarts, human-readable audit log."""

    def __init__(self, audit_dir: str | Path = "audit_logs") -> None:
        self._dir = Path(audit_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, Path] = {}
        self._load_index()

    def _run_path(self, run_id: str) -> Path:
        return self._dir / f"{run_id}.jsonl"

    def _load_index(self) -> None:
        for p in self._dir.glob("*.jsonl"):
            self._index[p.stem] = p

    async def save(self, state: MasterState) -> None:
        path = self._run_path(state.run_id)
        data = state.model_dump(mode="json")
        data["_saved_at"] = datetime.utcnow().isoformat()
        with path.open("a") as f:
            f.write(json.dumps(data) + "\n")
        self._index[state.run_id] = path

    async def load(self, run_id: str) -> MasterState | None:
        path = self._index.get(run_id) or self._run_path(run_id)
        if not path.exists():
            return None
        last_line = ""
        with path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    last_line = line
        if not last_line:
            return None
        data = json.loads(last_line)
        data.pop("_saved_at", None)
        return MasterState.model_validate(data)

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        files = sorted(self._dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        results = []
        for p in files[:limit]:
            last_line = ""
            with p.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
            if last_line:
                data = json.loads(last_line)
                data.pop("_saved_at", None)
                try:
                    ms = MasterState.model_validate(data)
                    results.append(ms.to_summary())
                except Exception:
                    pass
        return results

    async def delete(self, run_id: str) -> None:
        path = self._index.pop(run_id, None) or self._run_path(run_id)
        if path.exists():
            path.unlink()


class FuturePostgresPersistence(PersistenceProvider):
    """Stub — wire up SQLAlchemy async when a real Postgres DSN is available."""

    async def save(self, state: MasterState) -> None:
        raise NotImplementedError("Configure POSTGRES_DSN env var and install asyncpg")

    async def load(self, run_id: str) -> MasterState | None:
        raise NotImplementedError("Configure POSTGRES_DSN env var and install asyncpg")

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError("Configure POSTGRES_DSN env var and install asyncpg")

    async def delete(self, run_id: str) -> None:
        raise NotImplementedError("Configure POSTGRES_DSN env var and install asyncpg")
