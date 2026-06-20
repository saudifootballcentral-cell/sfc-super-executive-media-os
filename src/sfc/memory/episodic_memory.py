"""Episodic Memory — structured record of every pipeline run: event, decision, result, lesson."""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

from sfc.core.models import Division, Episode

logger = logging.getLogger("sfc.memory.episodic")


class EpisodicMemory:
    """Persistent log of pipeline runs with structured lessons.

    Constitutional rule: Every completed task must generate lessons learned.
    """

    def __init__(self) -> None:
        self._episodes: list[Episode] = []
        self._lock = threading.RLock()

    def record(
        self,
        run_id: str,
        event: str,
        decision: str,
        result: str,
        lesson: str,
        division: Division | None = None,
    ) -> Episode:
        episode = Episode(
            run_id=run_id,
            event=event,
            decision=decision,
            result=result,
            lesson=lesson,
            division=division,
        )
        with self._lock:
            self._episodes.append(episode)
        logger.info("[EpisodicMemory] Recorded episode for run %s", run_id)
        return episode

    def record_from_state(self, state: dict[str, Any]) -> list[Episode]:
        """Bulk-record lessons from a completed SFCState."""
        episodes: list[Episode] = []
        run_id = state.get("run_id", "unknown")
        task_type = state.get("task_type", "unknown")
        lessons = state.get("lessons_learned", [])
        analytics = state.get("analytics_report", {})

        result = (
            f"Published {len(state.get('approved_content', []))} items. "
            f"Reach est: {analytics.get('estimated_reach', 0):,}"
        )
        decision = state.get("execution_plan", {}).get("content_strategy", "Standard pipeline")

        for lesson in lessons:
            ep = self.record(
                run_id=run_id,
                event=f"{task_type} task processed",
                decision=decision,
                result=result,
                lesson=lesson,
            )
            episodes.append(ep)

        return episodes

    def get_all(self) -> list[Episode]:
        with self._lock:
            return list(self._episodes)

    def get_by_run(self, run_id: str) -> list[Episode]:
        with self._lock:
            return [e for e in self._episodes if e.run_id == run_id]

    def get_recent(self, n: int = 20) -> list[Episode]:
        with self._lock:
            return sorted(self._episodes, key=lambda e: e.timestamp, reverse=True)[:n]

    def get_lessons(self, division: Division | None = None) -> list[str]:
        with self._lock:
            episodes = (
                [e for e in self._episodes if e.division == division]
                if division
                else self._episodes
            )
            return [e.lesson for e in episodes]

    @property
    def total_count(self) -> int:
        with self._lock:
            return len(self._episodes)
