"""Working Memory — temporary task-scoped memory that expires on completion."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator
from uuid import UUID, uuid4

logger = logging.getLogger("sfc.memory.working")


class TaskContext:
    """Isolated memory context for a single active task."""

    def __init__(self, task_id: UUID, task_name: str) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.created_at = datetime.utcnow()
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        return dict(self._store)


class WorkingMemory:
    """Registry of active task contexts. Contexts are removed on completion."""

    def __init__(self) -> None:
        self._contexts: dict[UUID, TaskContext] = {}

    def create_task(self, task_name: str) -> TaskContext:
        task_id = uuid4()
        ctx = TaskContext(task_id=task_id, task_name=task_name)
        self._contexts[task_id] = ctx
        logger.debug("[WorkingMemory] Created task %s (%s)", task_name, task_id)
        return ctx

    def get_task(self, task_id: UUID) -> TaskContext | None:
        return self._contexts.get(task_id)

    def complete_task(self, task_id: UUID) -> TaskContext | None:
        ctx = self._contexts.pop(task_id, None)
        if ctx:
            logger.debug("[WorkingMemory] Completed task %s — memory released", task_id)
        return ctx

    @contextmanager
    def task_scope(self, task_name: str) -> Generator[TaskContext, None, None]:
        ctx = self.create_task(task_name)
        try:
            yield ctx
        finally:
            self.complete_task(ctx.task_id)

    @property
    def active_task_count(self) -> int:
        return len(self._contexts)
