"""Creative Division — event handlers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.divisions.creative.handlers")


async def handle_content_draft_created(event: BaseEvent, service: Any) -> None:
    logger.debug("[Creative] Content draft created — asset brief queued")


async def handle_story_created(event: BaseEvent, service: Any) -> None:
    logger.debug("[Creative] Story created — scheduling asset production")


HANDLERS: dict[str, Callable[..., Any]] = {
    "content_draft_created": handle_content_draft_created,
    "story_created": handle_story_created,
}
