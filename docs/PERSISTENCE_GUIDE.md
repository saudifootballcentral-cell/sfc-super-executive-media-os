# Persistence — MasterState Snapshots

## Purpose

`PersistenceProvider` saves and loads `MasterState` snapshots so that long-running workflows can survive process restarts and be inspected after completion.

## Providers

### InMemoryPersistence (default)

```python
from sfc.orchestration.persistence import InMemoryPersistence
p = InMemoryPersistence()
```

- In-process dict; lost on restart
- Zero configuration; used in tests and local development
- Thread-safe for single-process use

### JSONLAuditPersistence

```python
from sfc.orchestration.persistence import JSONLAuditPersistence
p = JSONLAuditPersistence(audit_dir="/var/log/sfc/orchestration")
```

- Append-only JSONL: every `save()` appends a new line
- Each run gets its own file: `{run_id}.jsonl`
- `load()` returns the last snapshot (most recent save)
- Full checkpoint history is preserved for post-mortem analysis
- Human-readable; compatible with `jq`, `grep`, log aggregators

### FuturePostgresPersistence

```python
from sfc.orchestration.persistence import FuturePostgresPersistence
```

- Stub — raises `NotImplementedError`
- Wire up SQLAlchemy + asyncpg when `POSTGRES_DSN` is available

## API

All providers implement the same interface:

```python
await provider.save(state: MasterState)                    # upsert
await provider.load(run_id: str) -> MasterState | None     # latest snapshot
await provider.list_runs(limit: int = 50) -> list[dict]    # recent summaries
await provider.delete(run_id: str)                         # remove
```

## Checkpointing

`RunContext.checkpoint()` calls `persistence.save(state)` after each stage completes. This ensures that a process restart can resume from the last completed stage rather than restarting from scratch.
