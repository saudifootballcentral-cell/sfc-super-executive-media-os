"""Governance Division — event handlers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.divisions.governance.handlers")


async def handle_content_draft_created(event: BaseEvent, service: Any) -> None:
    logger.debug("[Governance] Draft created — queued for review")


async def handle_story_created(event: BaseEvent, service: Any) -> None:
    logger.debug("[Governance] Story created — queued for compliance check")


HANDLERS: dict[str, Callable[..., Any]] = {
    "content_draft_created": handle_content_draft_created,
    "story_created": handle_story_created,
}
