"""Persistence providers for orchestration run state."""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from sfc.orchestration.master_state import MasterState

logger = logging.getLogger("sfc.orchestration.persistence")


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
        self._learning_records: list[dict] = []

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

    async def save_learning(self, run_id: str, data: dict) -> None:
        self._learning_records.append({"run_id": run_id, **data})
        # Keep only last 100
        if len(self._learning_records) > 100:
            self._learning_records = self._learning_records[-100:]

    async def get_recent_learning(self, task_type: str = "", limit: int = 5) -> list[dict]:
        records = self._learning_records
        if task_type:
            records = [r for r in records if r.get("task_type") == task_type]
        return records[-limit:]

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


class PostgresPersistence(PersistenceProvider):
    """PostgreSQL-backed persistence using asyncpg connection pool.

    Falls back gracefully if asyncpg is not installed or connection fails.
    Tables are auto-created on first use.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or os.environ.get("POSTGRES_DSN", "")
        self._pool: Any = None  # asyncpg pool, set in initialize()

    async def initialize(self) -> None:
        """Create connection pool and ensure tables exist."""
        try:
            import asyncpg  # type: ignore[import-untyped]
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
            await self._create_tables()
            logger.info("[PostgresPersistence] Pool connected and tables ready")
        except ImportError:
            logger.warning(
                "[PostgresPersistence] asyncpg not installed — persistence unavailable. "
                "Install with: pip install asyncpg"
            )
        except Exception as exc:
            logger.error("[PostgresPersistence] Connection failed: %s", exc)

    async def _create_tables(self) -> None:
        """CREATE TABLE IF NOT EXISTS for all required tables."""
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sfc_runs (
                    run_id        TEXT PRIMARY KEY,
                    workflow_type TEXT NOT NULL DEFAULT '',
                    status        TEXT NOT NULL DEFAULT 'pending',
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                    completed_at  TIMESTAMPTZ,
                    artifacts     JSONB NOT NULL DEFAULT '{}',
                    errors        JSONB NOT NULL DEFAULT '[]',
                    state_json    JSONB NOT NULL DEFAULT '{}'
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sfc_memory (
                    id         BIGSERIAL PRIMARY KEY,
                    run_id     TEXT NOT NULL,
                    key        TEXT NOT NULL,
                    value      JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sfc_learning (
                    id        BIGSERIAL PRIMARY KEY,
                    run_id    TEXT NOT NULL,
                    task_type TEXT NOT NULL DEFAULT '',
                    lessons   JSONB NOT NULL DEFAULT '[]',
                    pass_rate DOUBLE PRECISION,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
                    data      JSONB NOT NULL DEFAULT '{}'
                )
            """)
            # Indices for common queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sfc_runs_created_at
                ON sfc_runs (created_at DESC)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sfc_learning_task_type
                ON sfc_learning (task_type, timestamp DESC)
            """)

    async def save(self, state: MasterState) -> None:
        if self._pool is None:
            logger.debug("[PostgresPersistence] Pool not available — skipping save")
            return
        data = state.model_dump(mode="json")
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sfc_runs (run_id, workflow_type, status, created_at, completed_at,
                                      artifacts, errors, state_json)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (run_id) DO UPDATE SET
                    status       = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at,
                    artifacts    = EXCLUDED.artifacts,
                    errors       = EXCLUDED.errors,
                    state_json   = EXCLUDED.state_json
                """,
                state.run_id,
                str(data.get("workflow_type", "")),
                str(data.get("status", "pending")),
                datetime.utcnow(),
                None,  # completed_at — set by caller when done
                json.dumps(data.get("graph_states", {})),
                json.dumps(data.get("errors", [])),
                json.dumps(data),
            )

    async def load(self, run_id: str) -> MasterState | None:
        if self._pool is None:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT state_json FROM sfc_runs WHERE run_id = $1", run_id
            )
        if row is None:
            return None
        try:
            raw = row["state_json"]
            data = raw if isinstance(raw, dict) else json.loads(raw)
            return MasterState.model_validate(data)
        except Exception as exc:
            logger.warning("[PostgresPersistence] load parse error for run_id=%s: %s", run_id, exc)
            return None

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        if self._pool is None:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT run_id, workflow_type, status, created_at, completed_at "
                "FROM sfc_runs ORDER BY created_at DESC LIMIT $1",
                limit,
            )
        return [dict(r) for r in rows]

    async def delete(self, run_id: str) -> None:
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM sfc_runs WHERE run_id = $1", run_id)

    async def save_learning(self, run_id: str, data: dict) -> None:
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sfc_learning (run_id, task_type, lessons, pass_rate, timestamp, data)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                run_id,
                data.get("task_type", ""),
                json.dumps(data.get("lessons", [])),
                float(data.get("pass_rate", 0.0)),
                datetime.utcnow(),
                json.dumps(data),
            )

    async def get_recent_learning(self, task_type: str = "", limit: int = 5) -> list[dict]:
        if self._pool is None:
            return []
        if task_type:
            rows = await self._pool.fetch(
                "SELECT data FROM sfc_learning WHERE task_type = $1 "
                "ORDER BY timestamp DESC LIMIT $2",
                task_type, limit,
            )
        else:
            rows = await self._pool.fetch(
                "SELECT data FROM sfc_learning ORDER BY timestamp DESC LIMIT $1",
                limit,
            )
        results = []
        for row in rows:
            raw = row["data"]
            try:
                results.append(raw if isinstance(raw, dict) else json.loads(raw))
            except Exception:
                pass
        return results


# ---------------------------------------------------------------------------
# Module-level singleton provider
# ---------------------------------------------------------------------------

_provider: PersistenceProvider | None = None


def get_persistence_provider() -> PersistenceProvider:
    """Return the singleton persistence provider.

    - If POSTGRES_DSN env var is set → PostgresPersistence (call .initialize() to connect)
    - Otherwise → InMemoryPersistence
    """
    global _provider
    if _provider is None:
        dsn = os.environ.get("POSTGRES_DSN", "")
        _provider = PostgresPersistence(dsn) if dsn else InMemoryPersistence()
    return _provider
