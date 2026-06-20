"""Persona Memory — dedicated memory for specialist content personas."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.memory.persona")

CORE_PERSONAS = ["tiktok", "world_cup", "transfer", "tactical"]


class PersonaMemory:
    def __init__(self, persona_name: str) -> None:
        self.persona_name = persona_name
        self._store: dict[str, Any] = {}
        self._style_guide: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def set_style(self, key: str, value: Any) -> None:
        self._style_guide[key] = value

    def get_style(self, key: str, default: Any = None) -> Any:
        return self._style_guide.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        return {"store": dict(self._store), "style_guide": dict(self._style_guide)}


class PersonaMemoryStore:
    def __init__(self) -> None:
        self._memories: dict[str, PersonaMemory] = {
            name: PersonaMemory(name) for name in CORE_PERSONAS
        }

    def for_persona(self, persona_name: str) -> PersonaMemory:
        if persona_name not in self._memories:
            self._memories[persona_name] = PersonaMemory(persona_name)
        return self._memories[persona_name]

    def list_personas(self) -> list[str]:
        return list(self._memories.keys())
