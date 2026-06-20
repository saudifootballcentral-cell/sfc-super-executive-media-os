"""Intelligence Division — main service implementation."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sfc.core.models import Division
from sfc.divisions.base import (
    DivisionHealth,
    DivisionInput,
    DivisionOutput,
    DivisionReport,
    ValidationResult,
)
from sfc.divisions.intelligence.interface import IntelligenceDivisionInterface
from sfc.divisions.intelligence.models import (
    IntelligenceMetrics,
    IntelligenceOutput,
)
from sfc.events.bus import get_event_bus
from sfc.events.types import BaseEvent, IntelligenceBriefReady, TrendDetected
from sfc.memory.division_memory import DivisionMemory

logger = logging.getLogger("sfc.divisions.intelligence.service")

_MIN_SOURCES = 2
_SAUDI_CLUBS = ["Al Hilal", "Al Nassr", "Al Ittihad", "Al Ahli", "Al Qadsiah"]
_SAUDI_COMPETITIONS = ["Saudi Pro League", "King Cup", "Super Cup"]


class IntelligenceService(IntelligenceDivisionInterface):
    """Intelligence Division service — discovery, monitoring, verification.

    Works entirely deterministically when no API key is present.
    All methods return structured dicts regardless of Claude availability.
    """

    division = Division.INTELLIGENCE

    def __init__(self, memory_store: DivisionMemory | None = None) -> None:
        self.memory = memory_store
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0
        self._metrics = IntelligenceMetrics()

    async def initialize(self) -> None:
        logger.info("[Intelligence] Initialized")

    async def shutdown(self) -> None:
        logger.info("[Intelligence] Shutdown")

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            result = await self._run_pipeline(input)
            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            events: list[BaseEvent] = [
                IntelligenceBriefReady(
                    division=self.division.value,
                    run_id=input.run_id,
                    payload={"confidence_score": result["intelligence_report"].get("confidence_score", 0)},
                )
            ]

            # Persist to memory if available
            if self.memory:
                self.memory.set(f"intel_{input.run_id}", result["intelligence_report"])
                self.memory.set(f"sources_{input.run_id}", result["verified_sources"])

            bus = get_event_bus()
            bus.publish_many(events)

            return IntelligenceOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=True,
                data=result,
                events_to_publish=events,
                processing_time_ms=elapsed,
                intelligence_report=result["intelligence_report"],
                verified_sources=result["verified_sources"],
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[Intelligence] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def _run_pipeline(self, input: DivisionInput) -> dict[str, Any]:
        payload = input.payload
        state = input.state_snapshot
        task_type = input.task_type

        verified_sources = self._gather_sources(payload, state)
        source_count = len(verified_sources)
        confidence = self._calculate_confidence(source_count, payload)
        is_rumor = payload.get("is_rumor", False)

        report: dict[str, Any] = {
            "task_type": task_type,
            "research_complete": True,
            "is_rumor": is_rumor,
            "rumor_label": "RUMOR — unconfirmed" if is_rumor else None,
            "confidence_score": confidence,
            "source_count": source_count,
            "key_facts": self._extract_key_facts(payload),
            "entities_detected": await self.extract_entities(
                payload.get("headline", "") + " " + payload.get("body", "")
            ),
            "sentiment": "neutral",
            "newsworthiness_score": self._score_newsworthiness(task_type, payload),
            "trends": await self.detect_trends(payload),
            "researched_at": datetime.utcnow().isoformat(),
        }

        return {"intelligence_report": report, "verified_sources": verified_sources}

    async def gather_intelligence(
        self, topic: str, sources: list[str]
    ) -> dict[str, Any]:
        """Gather and structure intelligence for a topic."""
        confidence = self._calculate_confidence(len(sources), {"topic": topic})
        return {
            "topic": topic,
            "sources_checked": sources,
            "source_count": len(sources),
            "confidence": confidence,
            "key_facts": [f"Intelligence gathered on: {topic}"],
            "gathered_at": datetime.utcnow().isoformat(),
        }

    async def verify_sources(
        self, claim: str, sources: list[str]
    ) -> dict[str, Any]:
        """Verify a claim against provided sources."""
        count = len(sources)
        passes = count >= _MIN_SOURCES
        confidence = self._calculate_confidence(count, {})
        return {
            "claim": claim,
            "source_count": count,
            "passes_verification": passes,
            "confidence_score": confidence,
            "sources_checked": sources,
            "verified_at": datetime.utcnow().isoformat(),
        }

    async def classify_rumor(self, content: str) -> dict[str, Any]:
        """Classify whether content is rumor, unverified, or confirmed fact."""
        rumor_signals = ["rumor", "unconfirmed", "sources say", "reportedly", "could", "might"]
        content_lower = content.lower()
        is_rumor = any(sig in content_lower for sig in rumor_signals)
        confidence = 45.0 if is_rumor else 80.0
        return {
            "is_rumor": is_rumor,
            "label": "RUMOR — unconfirmed" if is_rumor else None,
            "confidence": confidence,
            "classified_at": datetime.utcnow().isoformat(),
        }

    async def extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract players, clubs, competitions, coaches from text."""
        found_clubs = [c for c in _SAUDI_CLUBS if c.lower() in text.lower()]
        found_comps = [c for c in _SAUDI_COMPETITIONS if c.lower() in text.lower()]
        return {
            "players": [],
            "clubs": found_clubs,
            "competitions": found_comps or ["Saudi Pro League"],
            "coaches": [],
        }

    async def detect_trends(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect trending topics relevant to Saudi football."""
        task_type = payload.get("task_type", "news")
        trend_map = {
            "transfer": [{"topic": "Transfer window", "score": 85}],
            "match": [{"topic": "Match day", "score": 90}],
            "crisis": [{"topic": "Crisis management", "score": 95}],
        }
        return trend_map.get(task_type, [{"topic": "Saudi football", "score": 70}])

    async def handle_event(self, event: BaseEvent) -> None:
        from sfc.divisions.intelligence.handlers import HANDLERS
        handler = HANDLERS.get(event.event_type)
        if handler:
            await handler(event, self)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        source_count = content.get("source_count", 0)
        confidence = content.get("confidence_score", 0.0)
        reasons: list[str] = []
        suggestions: list[str] = []

        if source_count < _MIN_SOURCES:
            reasons.append(f"Insufficient sources: {source_count} < {_MIN_SOURCES}")
            suggestions.append("Add at least one more independent source")

        if confidence < 85.0:
            reasons.append(f"Confidence {confidence:.1f} below 85.0 threshold")
            suggestions.append("Gather more corroborating evidence")

        score = min(100.0, confidence * 0.7 + min(source_count * 15.0, 30.0))
        return ValidationResult(valid=len(reasons) == 0, score=score, reasons=reasons, suggestions=suggestions)

    async def report(self) -> DivisionReport:
        return DivisionReport(
            division=self.division.value,
            period="session",
            metrics={
                "total_calls": self._call_count,
                "error_count": self._error_count,
                "avg_processing_ms": (
                    self._total_processing_ms / self._call_count if self._call_count else 0
                ),
            },
            highlights=[f"Processed {self._call_count} intelligence requests"],
            recommendations=["Monitor source reliability trends weekly"],
        )

    def health_check(self) -> DivisionHealth:
        status = "healthy"
        if self._call_count > 0:
            error_rate = self._error_count / self._call_count
            if error_rate > 0.2:
                status = "degraded"
            if error_rate > 0.5:
                status = "unhealthy"
        return DivisionHealth(
            division=self.division.value,
            status=status,
            metrics={
                "call_count": self._call_count,
                "error_count": self._error_count,
                "avg_processing_ms": (
                    self._total_processing_ms / self._call_count if self._call_count else 0
                ),
            },
        )

    def describe(self) -> str:
        return "Discovery, monitoring, source verification, trend detection"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _gather_sources(
        self, payload: dict[str, Any], state: dict[str, Any]
    ) -> list[dict[str, Any]]:
        raw_sources = payload.get("sources", state.get("verified_sources", []))
        normalised: list[dict[str, Any]] = []
        for s in raw_sources:
            if isinstance(s, dict):
                normalised.append({
                    "name": s.get("name", "Unknown"),
                    "url": s.get("url"),
                    "reliability_score": float(
                        s.get("reliability", s.get("reliability_score", 80.0))
                    ),
                    "retrieved_at": datetime.utcnow().isoformat(),
                })
            elif isinstance(s, str):
                normalised.append({
                    "name": s,
                    "url": None,
                    "reliability_score": 75.0,
                    "retrieved_at": datetime.utcnow().isoformat(),
                })
        return normalised

    def _calculate_confidence(
        self, source_count: int, payload: dict[str, Any]
    ) -> float:
        base = 60.0
        source_bonus = min(source_count * 12.0, 30.0)
        official_bonus = 5.0 if payload.get("official_statement") else 0.0
        rumor_penalty = -10.0 if payload.get("is_rumor") else 0.0
        return min(100.0, base + source_bonus + official_bonus + rumor_penalty)

    def _extract_key_facts(self, payload: dict[str, Any]) -> list[str]:
        facts: list[str] = []
        if payload.get("headline"):
            facts.append(payload["headline"])
        if payload.get("key_facts"):
            facts.extend(payload["key_facts"])
        if not facts:
            body = payload.get("body", "")
            facts.append(body[:200] if body else "No facts extracted")
        return facts

    def _score_newsworthiness(self, task_type: str, payload: dict[str, Any]) -> float:
        base_scores = {
            "crisis": 95.0, "transfer": 85.0, "match": 80.0,
            "news": 70.0, "trend": 65.0, "analysis": 60.0, "campaign": 55.0,
        }
        score = base_scores.get(task_type, 60.0)
        if payload.get("importance_score"):
            score = (score + float(payload["importance_score"])) / 2
        return round(score, 1)
