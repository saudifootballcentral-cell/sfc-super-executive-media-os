"""Publishing Division — event handlers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.divisions.publishing.handlers")


async def handle_governance_approved(event: BaseEvent, service: Any) -> None:
    logger.debug("[Publishing] Governance approved — content queued for distribution")


HANDLERS: dict[str, Callable[..., Any]] = {
    "governance_approved": handle_governance_approved,
}
