"""SFC Super Executive Media OS — entry point."""

from __future__ import annotations

import asyncio
import logging
import sys

from core.executive import SFCExecutive
from core.models import EventType, Division

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)


async def demo() -> None:
    """Quick demonstration of the OS booting and processing a news event."""
    executive = SFCExecutive()

    print(executive.executive_brief())

    # Simulate a breaking transfer news event
    event = await executive.dispatch(
        event_type=EventType.NEWS_DETECTED,
        source="sfc_intelligence",
        payload={
            "headline": "Al Hilal break Saudi Pro League transfer record",
            "body": "Al Hilal have confirmed the signing of a world-class striker in a record deal.",
            "importance_score": 95,
            "sources": [
                {"name": "Saudi Football Federation", "url": "https://saff.com.sa", "reliability": 95},
                {"name": "Al Hilal FC Official", "url": "https://alhilal.com", "reliability": 98},
            ],
        },
        owner=Division.INTELLIGENCE,
    )

    print(f"\nEvent processed: {event.event_id} | Status: {event.status}")
    print(executive.executive_brief())


if __name__ == "__main__":
    asyncio.run(demo())
