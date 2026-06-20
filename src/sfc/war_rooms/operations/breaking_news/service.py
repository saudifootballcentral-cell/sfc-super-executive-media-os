"""Breaking News Command Center — service implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.breaking_news.models import (
    BreakingNewsAlert,
    NewsPackage,
    NewsUrgency,
    SourceValidation,
    VerificationStatus,
)
from sfc.war_rooms.shared.events import BreakingNewsDetected

logger = logging.getLogger("sfc.war_rooms.operations.breaking_news")


class BreakingNewsCommandCenter:
    """Command center for detecting, validating and packaging breaking news."""

    MIN_SOURCES = 2

    def __init__(self) -> None:
        self._active_alerts: dict[str, BreakingNewsAlert] = {}

    async def detect(
        self,
        headline: str,
        sources: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> BreakingNewsAlert:
        """Detect a breaking news event, validate sources, and set urgency."""
        metadata = metadata or {}
        validated = await self.validate_sources(sources)
        confidence = self._calculate_confidence(validated)
        urgency = self._assign_urgency(confidence)
        source_count = len(validated)

        if source_count < self.MIN_SOURCES:
            verification_status = VerificationStatus.UNVERIFIED
            logger.warning(
                "[BreakingNews] Only %d source(s) — minimum %d required",
                source_count,
                self.MIN_SOURCES,
            )
        elif source_count == self.MIN_SOURCES:
            verification_status = VerificationStatus.PARTIAL
        else:
            verification_status = VerificationStatus.VERIFIED

        alert = BreakingNewsAlert(
            headline=headline,
            urgency=urgency,
            sources=validated,
            verification_status=verification_status,
            confidence_score=confidence,
            detected_at=datetime.utcnow(),
            metadata=metadata,
        )
        self._active_alerts[alert.alert_id] = alert

        get_event_bus().publish(
            BreakingNewsDetected(
                division="operations",
                run_id=alert.alert_id,
                payload={
                    "alert_id": alert.alert_id,
                    "headline": headline,
                    "urgency": urgency.value,
                    "confidence_score": confidence,
                    "source_count": source_count,
                },
            )
        )
        logger.info(
            "[BreakingNews] Alert detected: %s | urgency=%s confidence=%.1f",
            alert.alert_id,
            urgency.value,
            confidence,
        )
        return alert

    async def validate_sources(self, sources: list[dict[str, Any]]) -> list[SourceValidation]:
        """Score and validate each source."""
        validated: list[SourceValidation] = []
        for s in sources:
            name = s.get("name", s.get("source_name", "Unknown"))
            reliability = float(s.get("reliability_score", s.get("reliability", 75.0)))
            verified = reliability >= 70.0
            validated.append(
                SourceValidation(
                    source_name=name,
                    reliability_score=reliability,
                    verified=verified,
                    validated_at=datetime.utcnow(),
                )
            )
        return validated

    async def package_news(self, alert: BreakingNewsAlert) -> NewsPackage:
        """Assemble a full content package for a breaking news alert."""
        thread_package = [
            f"BREAKING: {alert.headline}",
            f"Confidence: {alert.confidence_score:.0f}% | Sources: {len(alert.sources)}",
            f"Status: {alert.verification_status.value.upper()}",
        ]
        article_draft = (
            f"# {alert.headline}\n\n"
            f"*Detected: {alert.detected_at.strftime('%Y-%m-%d %H:%M UTC')}*\n\n"
            f"Breaking news with {len(alert.sources)} verified source(s). "
            f"Confidence: {alert.confidence_score:.1f}%."
        )
        video_brief = (
            f"VIDEO BRIEF — {alert.urgency.value.upper()}: {alert.headline}. "
            f"Confidence {alert.confidence_score:.0f}%."
        )
        distribution_plan: dict[str, Any] = {
            "twitter": alert.urgency in (NewsUrgency.CRITICAL, NewsUrgency.HIGH),
            "instagram": True,
            "website": True,
            "push_notification": alert.urgency == NewsUrgency.CRITICAL,
        }
        executive_brief = (
            f"EXECUTIVE BRIEF [{alert.urgency.value.upper()}]: {alert.headline}. "
            f"Sources: {len(alert.sources)}. Confidence: {alert.confidence_score:.0f}%. "
            f"Status: {alert.verification_status.value}."
        )
        return NewsPackage(
            alert_id=alert.alert_id,
            thread_package=thread_package,
            article_draft=article_draft,
            video_brief=video_brief,
            distribution_plan=distribution_plan,
            executive_brief=executive_brief,
        )

    async def coordinate_coverage(self, alert: BreakingNewsAlert) -> dict[str, Any]:
        """Return a coverage coordination plan for all divisions."""
        return {
            "alert_id": alert.alert_id,
            "urgency": alert.urgency.value,
            "lead_division": "editorial",
            "supporting_divisions": ["creative", "publishing", "analytics"],
            "governance_required": True,
            "publish_immediately": alert.urgency == NewsUrgency.CRITICAL
            and alert.verification_status == VerificationStatus.VERIFIED,
            "coordination_notes": f"Breaking news coverage for: {alert.headline}",
        }

    def get_active_alerts(self) -> list[BreakingNewsAlert]:
        """Return all currently active alerts."""
        return list(self._active_alerts.values())

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "breaking_news_command_center",
            "status": "healthy",
            "active_alerts": len(self._active_alerts),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_confidence(self, sources: list[SourceValidation]) -> float:
        if not sources:
            return 0.0
        avg_reliability = sum(s.reliability_score for s in sources) / len(sources)
        source_bonus = min(len(sources) * 5.0, 20.0)
        return min(100.0, avg_reliability + source_bonus)

    def _assign_urgency(self, confidence: float) -> NewsUrgency:
        if confidence >= 90:
            return NewsUrgency.CRITICAL
        if confidence >= 75:
            return NewsUrgency.HIGH
        if confidence >= 60:
            return NewsUrgency.MEDIUM
        return NewsUrgency.LOW
