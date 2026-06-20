"""Editorial Division — event handlers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.divisions.editorial.handlers")


async def handle_intelligence_brief_ready(event: BaseEvent, service: Any) -> None:
    """Trigger draft generation when intelligence is ready."""
    logger.debug("[Editorial] Intelligence brief ready — drafts queued")


async def handle_planning_cycle_started(event: BaseEvent, service: Any) -> None:
    """Reset draft state on new planning cycle."""
    logger.debug("[Editorial] Planning cycle started — resetting draft state")


HANDLERS: dict[str, Callable[..., Any]] = {
    "intelligence_brief_ready": handle_intelligence_brief_ready,
    "planning_cycle_started": handle_planning_cycle_started,
}
