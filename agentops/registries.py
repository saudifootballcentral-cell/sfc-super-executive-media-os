"""AgentOps Registries — Agent, Prompt, Capability, and Tool registries."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from core.models import AgentRecord, CapabilityRecord, PromptRecord, ToolRecord

logger = logging.getLogger("sfc.agentops.registries")


class AgentRegistry:
    """Central registry of all agents in the operating system."""

    def __init__(self) -> None:
        self._agents: dict[UUID, AgentRecord] = {}

    def register(self, agent: AgentRecord) -> AgentRecord:
        self._agents[agent.agent_id] = agent
        logger.info("[AgentRegistry] Registered agent: %s (%s)", agent.name, agent.agent_id)
        return agent

    def get(self, agent_id: UUID) -> AgentRecord | None:
        return self._agents.get(agent_id)

    def find_by_name(self, name: str) -> AgentRecord | None:
        return next((a for a in self._agents.values() if a.name == name), None)

    def list_active(self) -> list[AgentRecord]:
        return [a for a in self._agents.values() if a.status == "active"]

    def all(self) -> list[AgentRecord]:
        return list(self._agents.values())

    def update_health(self, agent_id: UUID, health_score: float) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.health_score = health_score

    @property
    def count(self) -> int:
        return len(self._agents)


class PromptRegistry:
    """Registry of versioned, approved prompts."""

    def __init__(self) -> None:
        self._prompts: dict[UUID, PromptRecord] = {}
        self._name_index: dict[str, UUID] = {}

    def register(self, prompt: PromptRecord) -> PromptRecord:
        self._prompts[prompt.prompt_id] = prompt
        self._name_index[prompt.name] = prompt.prompt_id
        logger.info("[PromptRegistry] Registered prompt: %s v%s", prompt.name, prompt.version)
        return prompt

    def get(self, prompt_id: UUID) -> PromptRecord | None:
        return self._prompts.get(prompt_id)

    def get_by_name(self, name: str) -> PromptRecord | None:
        pid = self._name_index.get(name)
        return self._prompts.get(pid) if pid else None

    def rollback(self, prompt_id: UUID) -> PromptRecord | None:
        prompt = self._prompts.get(prompt_id)
        if prompt and prompt.rollback_version:
            logger.info("[PromptRegistry] Rolling back %s to v%s", prompt.name, prompt.rollback_version)
        return prompt

    def list_approved(self) -> list[PromptRecord]:
        return [p for p in self._prompts.values() if p.approval_status == "approved"]


class CapabilityRegistry:
    """Registry of AI capabilities with provider and fallback tracking."""

    def __init__(self) -> None:
        self._capabilities: dict[UUID, CapabilityRecord] = {}
        self._name_index: dict[str, UUID] = {}

    def register(self, capability: CapabilityRecord) -> CapabilityRecord:
        self._capabilities[capability.capability_id] = capability
        self._name_index[capability.name] = capability.capability_id
        logger.info("[CapabilityRegistry] Registered: %s via %s", capability.name, capability.provider)
        return capability

    def get(self, capability_id: UUID) -> CapabilityRecord | None:
        return self._capabilities.get(capability_id)

    def get_by_name(self, name: str) -> CapabilityRecord | None:
        cid = self._name_index.get(name)
        return self._capabilities.get(cid) if cid else None

    def get_fallback(self, capability_id: UUID) -> CapabilityRecord | None:
        cap = self._capabilities.get(capability_id)
        if cap and cap.fallback_provider:
            return next(
                (c for c in self._capabilities.values() if c.provider == cap.fallback_provider),
                None,
            )
        return None

    def all(self) -> list[CapabilityRecord]:
        return list(self._capabilities.values())


class ToolRegistry:
    """Registry of external tools, APIs, and integrations."""

    def __init__(self) -> None:
        self._tools: dict[UUID, ToolRecord] = {}
        self._name_index: dict[str, UUID] = {}

    def register(self, tool: ToolRecord) -> ToolRecord:
        self._tools[tool.tool_id] = tool
        self._name_index[tool.name] = tool.tool_id
        logger.info("[ToolRegistry] Registered tool: %s (%s)", tool.name, tool.provider)
        return tool

    def get(self, tool_id: UUID) -> ToolRecord | None:
        return self._tools.get(tool_id)

    def get_by_name(self, name: str) -> ToolRecord | None:
        tid = self._name_index.get(name)
        return self._tools.get(tid) if tid else None

    def list_active(self) -> list[ToolRecord]:
        return [t for t in self._tools.values() if t.status == "active"]

    def all(self) -> list[ToolRecord]:
        return list(self._tools.values())
