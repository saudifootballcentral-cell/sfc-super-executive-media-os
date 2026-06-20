"""Revenue Division — event handlers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.divisions.revenue.handlers")


async def handle_intelligence_brief_ready(event: BaseEvent, service: Any) -> None:
    logger.debug("[Revenue] Intelligence brief ready — scanning for sponsor opportunities")


async def handle_content_draft_created(event: BaseEvent, service: Any) -> None:
    logger.debug("[Revenue] Content draft created — evaluating monetization potential")


HANDLERS: dict[str, Callable[..., Any]] = {
    "intelligence_brief_ready": handle_intelligence_brief_ready,
    "content_draft_created": handle_content_draft_created,
}
