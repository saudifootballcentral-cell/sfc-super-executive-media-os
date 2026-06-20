"""Tests for BreakingNewsCommandCenter."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.breaking_news.models import (
    BreakingNewsAlert,
    NewsPackage,
    NewsUrgency,
    VerificationStatus,
)
from sfc.war_rooms.operations.breaking_news.service import BreakingNewsCommandCenter


def _sources(n: int = 2) -> list[dict]:
    return [{"name": f"Source{i}", "reliability_score": 85.0} for i in range(n)]


class TestBreakingNewsCommandCenter:
    def setup_method(self) -> None:
        get_event_bus().reset()
        self.service = BreakingNewsCommandCenter()

    async def test_detect_returns_alert(self) -> None:
        alert = await self.service.detect("Al-Hilal wins title", _sources(2))
        assert isinstance(alert, BreakingNewsAlert)
        assert alert.headline == "Al-Hilal wins title"
        assert alert.alert_id

    async def test_detect_with_two_sources_partial_verified(self) -> None:
        alert = await self.service.detect("Transfer news", _sources(2))
        assert alert.verification_status == VerificationStatus.PARTIAL
        assert alert.confidence_score > 0

    async def test_detect_with_three_sources_verified(self) -> None:
        alert = await self.service.detect("World cup bid", _sources(3))
        assert alert.verification_status == VerificationStatus.VERIFIED

    async def test_detect_with_one_source_unverified(self) -> None:
        alert = await self.service.detect("Unconfirmed rumour", _sources(1))
        assert alert.verification_status == VerificationStatus.UNVERIFIED

    async def test_detect_publishes_event(self) -> None:
        await self.service.detect("Big match result", _sources(2))
        history = get_event_bus().get_history("breaking_news_detected")
        assert len(history) == 1
        assert history[0].payload["headline"] == "Big match result"

    async def test_urgency_critical_for_high_confidence(self) -> None:
        # High reliability sources -> high confidence -> CRITICAL
        sources = [{"name": f"S{i}", "reliability_score": 95.0} for i in range(4)]
        alert = await self.service.detect("Title", sources)
        assert alert.urgency == NewsUrgency.CRITICAL

    async def test_package_news_returns_package(self) -> None:
        alert = await self.service.detect("Big story", _sources(2))
        package = await self.service.package_news(alert)
        assert isinstance(package, NewsPackage)
        assert package.alert_id == alert.alert_id
        assert len(package.thread_package) > 0
        assert package.article_draft
        assert package.executive_brief

    async def test_coordinate_coverage_returns_dict(self) -> None:
        alert = await self.service.detect("Match result", _sources(2))
        plan = await self.service.coordinate_coverage(alert)
        assert "lead_division" in plan
        assert plan["governance_required"] is True

    async def test_get_active_alerts(self) -> None:
        await self.service.detect("Story 1", _sources(2))
        await self.service.detect("Story 2", _sources(3))
        alerts = self.service.get_active_alerts()
        assert len(alerts) == 2

    async def test_health_check(self) -> None:
        hc = self.service.health_check()
        assert hc["status"] == "healthy"
        assert hc["component"] == "breaking_news_command_center"
