"""AgentOps Registries — Agent, Prompt, Capability, and Tool registries."""

from __future__ import annotations

import logging
import threading
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from uuid import uuid4

logger = logging.getLogger("sfc.agentops.registries")


class AgentRecord(BaseModel):
    agent_id: UUID = Field(default_factory=uuid4)
    name: str
    division: str
    version: str = "1.0.0"
    status: str = "idle"
    owner: str = "agentops"
    capabilities: list[str] = Field(default_factory=list)
    health_score: float = Field(default=100.0, ge=0.0, le=100.0)
    cost_profile: dict[str, float] = Field(default_factory=dict)


class PromptRecord(BaseModel):
    prompt_id: UUID = Field(default_factory=uuid4)
    name: str
    version: str = "1.0.0"
    author: str
    approval_status: str = "pending"
    content: str
    rollback_version: str | None = None


class CapabilityRecord(BaseModel):
    capability_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    provider: str
    cost: float = 0.0
    quality: float = Field(default=100.0, ge=0.0, le=100.0)
    fallback_provider: str | None = None


class ToolRecord(BaseModel):
    tool_id: UUID = Field(default_factory=uuid4)
    name: str
    provider: str
    quota: int | None = None
    permissions: list[str] = Field(default_factory=list)
    cost_profile: dict[str, float] = Field(default_factory=dict)
    status: str = "active"


class _BaseRegistry:
    def __init__(self) -> None:
        self._store: dict[UUID, Any] = {}
        self._name_index: dict[str, UUID] = {}
        self._lock = threading.RLock()


class AgentRegistry(_BaseRegistry):
    def register(self, agent: AgentRecord) -> AgentRecord:
        with self._lock:
            self._store[agent.agent_id] = agent
            self._name_index[agent.name] = agent.agent_id
        logger.info("[AgentRegistry] Registered: %s", agent.name)
        return agent

    def get(self, agent_id: UUID) -> AgentRecord | None:
        return self._store.get(agent_id)

    def find_by_name(self, name: str) -> AgentRecord | None:
        with self._lock:
            aid = self._name_index.get(name)
            return self._store.get(aid) if aid else None

    def all(self) -> list[AgentRecord]:
        return list(self._store.values())

    @property
    def count(self) -> int:
        return len(self._store)


class PromptRegistry(_BaseRegistry):
    def register(self, prompt: PromptRecord) -> PromptRecord:
        with self._lock:
            self._store[prompt.prompt_id] = prompt
            self._name_index[prompt.name] = prompt.prompt_id
        return prompt

    def get_by_name(self, name: str) -> PromptRecord | None:
        with self._lock:
            pid = self._name_index.get(name)
            return self._store.get(pid) if pid else None

    def list_approved(self) -> list[PromptRecord]:
        return [p for p in self._store.values() if p.approval_status == "approved"]


class CapabilityRegistry(_BaseRegistry):
    def register(self, cap: CapabilityRecord) -> CapabilityRecord:
        with self._lock:
            self._store[cap.capability_id] = cap
            self._name_index[cap.name] = cap.capability_id
        return cap

    def get_by_name(self, name: str) -> CapabilityRecord | None:
        with self._lock:
            cid = self._name_index.get(name)
            return self._store.get(cid) if cid else None

    def all(self) -> list[CapabilityRecord]:
        return list(self._store.values())


class ToolRegistry(_BaseRegistry):
    def register(self, tool: ToolRecord) -> ToolRecord:
        with self._lock:
            self._store[tool.tool_id] = tool
            self._name_index[tool.name] = tool.tool_id
        return tool

    def get_by_name(self, name: str) -> ToolRecord | None:
        with self._lock:
            tid = self._name_index.get(name)
            return self._store.get(tid) if tid else None

    def list_active(self) -> list[ToolRecord]:
        return [t for t in self._store.values() if t.status == "active"]
