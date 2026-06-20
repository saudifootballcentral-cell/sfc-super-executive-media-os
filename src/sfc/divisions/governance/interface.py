"""Governance Division — abstract interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from sfc.divisions.base import DivisionInterface


class GovernanceDivisionInterface(DivisionInterface):
    @abstractmethod
    async def review_content(self, draft: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def check_constitutional_compliance(self, draft: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def escalate(self, draft: dict[str, Any], reasons: list[str]) -> str: ...
