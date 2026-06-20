"""Episodic Memory — structured record of decisions and lessons learned."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from core.models import Division, Episode

logger = logging.getLogger("sfc.memory.episodic")


class EpisodicMemory:
    """Persistent log of events, decisions, results, and lessons.

    Every completed task must generate at least one Episode.
    """

    def __init__(self) -> None:
        self._episodes: list[Episode] = []

    def record(
        self,
        event: str,
        decision: str,
        result: str,
        lesson: str,
        division: Division | None = None,
    ) -> Episode:
        episode = Episode(
            event=event,
            decision=decision,
            result=result,
            lesson=lesson,
            division=division,
        )
        self._episodes.append(episode)
        logger.info("[EpisodicMemory] Recorded episode %s — %s", episode.episode_id, event)
        return episode

    def get_all(self) -> list[Episode]:
        return list(self._episodes)

    def get_by_division(self, division: Division) -> list[Episode]:
        return [e for e in self._episodes if e.division == division]

    def get_recent(self, n: int = 10) -> list[Episode]:
        return sorted(self._episodes, key=lambda e: e.timestamp, reverse=True)[:n]

    def get_lessons(self, division: Division | None = None) -> list[str]:
        episodes = self.get_by_division(division) if division else self._episodes
        return [e.lesson for e in episodes]

    @property
    def total_count(self) -> int:
        return len(self._episodes)
