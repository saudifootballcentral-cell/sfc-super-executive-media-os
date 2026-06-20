"""Intelligence Division — event handlers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.divisions.intelligence.handlers")


async def handle_planning_cycle_started(event: BaseEvent, service: Any) -> None:
    """React to a new planning cycle by triggering a fresh intelligence sweep."""
    logger.info("[Intelligence] New planning cycle started — clearing trend cache")
    if service.memory:
        service.memory.delete("trend_snapshot")


async def handle_performance_updated(event: BaseEvent, service: Any) -> None:
    """Use performance signals to adjust source weighting."""
    logger.debug("[Intelligence] Performance updated — adjusting source weights")


HANDLERS: dict[str, Callable[..., Any]] = {
    "planning_cycle_started": handle_planning_cycle_started,
    "performance_updated": handle_performance_updated,
}
