"""Analytics Division — event handlers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.divisions.analytics.handlers")


async def handle_publishing_completed(event: BaseEvent, service: Any) -> None:
    logger.debug("[Analytics] Publishing completed — performance tracking queued")


HANDLERS: dict[str, Callable[..., Any]] = {
    "publishing_completed": handle_publishing_completed,
}
