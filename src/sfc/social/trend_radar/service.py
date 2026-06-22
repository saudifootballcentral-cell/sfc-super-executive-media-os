"""Trend Radar Service — detects and tracks social media trends."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.ai.model_gateway import AIGateway
from sfc.social.trend_radar.models import (
    SocialSource,
    TrendForecast,
    TrendMetrics,
    TrendRadarSnapshot,
    TrendReport,
    TrendState,
)

logger = logging.getLogger("sfc.social.trend_radar")

_singleton: "TrendRadarService | None" = None


def get_trend_radar() -> "TrendRadarService":
    global _singleton
    if _singleton is None:
        _singleton = TrendRadarService()
    return _singleton


class TrendRadarService:
    """Monitors and classifies social media trends across all platforms."""

    def __init__(self) -> None:
        self._gateway: AIGateway | None = None
        self._trends: dict[str, TrendReport] = {}
        self._history: list[TrendReport] = []
        self._max_history = 500

    @property
    def gateway(self) -> AIGateway:
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def scan(self, topics: list[str] | None = None) -> TrendRadarSnapshot:
        """Scan all platforms for trending topics and return a snapshot."""
        topics = topics or self._get_default_topics()
        trend_reports: list[TrendReport] = []

        for topic in topics[:10]:
            report = await self._analyze_topic(topic)
            self._trends[report.trend_id] = report
            trend_reports.append(report)
            if len(self._history) < self._max_history:
                self._history.append(report)

        breaking = [r for r in trend_reports if r.state == TrendState.BREAKING]
        emerging = [r for r in trend_reports if r.state == TrendState.EMERGING]
        hot = [r for r in trend_reports if r.state in (TrendState.HOT, TrendState.RISING)]

        top = max(trend_reports, key=lambda r: r.score, default=None)
        alerts = [
            f"BREAKING: {r.topic} — velocity {r.metrics.velocity:.1f}"
            for r in breaking
        ]

        return TrendRadarSnapshot(
            breaking_trends=[r.to_dict() for r in breaking],
            emerging_trends=[r.to_dict() for r in emerging],
            hot_trends=[r.to_dict() for r in hot],
            total_tracked=len(trend_reports),
            top_topic=top.topic if top else "",
            top_score=top.score if top else 0.0,
            alerts=alerts,
        )

    async def get_snapshot(self) -> TrendRadarSnapshot:
        """Return latest snapshot from cached trends."""
        if not self._trends:
            return await self.scan()
        trends = list(self._trends.values())
        breaking = [r for r in trends if r.state == TrendState.BREAKING]
        emerging = [r for r in trends if r.state == TrendState.EMERGING]
        hot = [r for r in trends if r.state in (TrendState.HOT, TrendState.RISING)]
        top = max(trends, key=lambda r: r.score, default=None)
        return TrendRadarSnapshot(
            breaking_trends=[r.to_dict() for r in breaking],
            emerging_trends=[r.to_dict() for r in emerging],
            hot_trends=[r.to_dict() for r in hot],
            total_tracked=len(trends),
            top_topic=top.topic if top else "",
            top_score=top.score if top else 0.0,
            alerts=[],
        )

    def get_trend(self, trend_id: str) -> TrendReport | None:
        return self._trends.get(trend_id)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    async def _analyze_topic(self, topic: str) -> TrendReport:
        """Analyze trend for a topic using fixture data (no random values)."""
        from sfc.data.fixtures.loader import get_fixture_loader
        loader = get_fixture_loader()
        topic_scores = loader.get_topic_scores()

        data = topic_scores.get(topic, {})
        if not data:
            # fallback: search partial match in fixture trends
            for key, val in topic_scores.items():
                if any(w in key.lower() for w in topic.lower().split()):
                    data = val
                    break

        score: float = float(data.get("score", 55.0))
        velocity: float = float(data.get("velocity", 3.0))
        volume: int = int(data.get("volume", 25000))
        acceleration: float = float(data.get("acceleration", 0.5))
        reach: int = int(data.get("reach", 200000))
        engagement: float = float(data.get("engagement", 0.05))
        peak_estimate_hours: float = float(data.get("peak_estimate_hours", 12.0))
        confidence: float = float(data.get("confidence", 0.75))

        state = TrendState.EMERGING
        if velocity > 8:
            state = TrendState.BREAKING
        elif velocity > 6:
            state = TrendState.HOT
        elif velocity > 4:
            state = TrendState.RISING
        elif score < 30:
            state = TrendState.DECLINING

        metrics = TrendMetrics(
            velocity=velocity,
            volume=volume,
            acceleration=acceleration,
            reach=reach,
            engagement=engagement,
        )

        forecast = TrendForecast(
            expected_state_in_1h=state.value,
            expected_state_in_6h=TrendState.HOT.value if score > 60 else TrendState.DECLINING.value,
            expected_state_in_24h=TrendState.DECLINING.value,
            peak_estimate_hours=peak_estimate_hours,
            confidence=confidence,
            narrative=f"{topic} is gaining traction across social platforms.",
        )

        ai_insights = await self._get_ai_insights(topic, state, metrics)

        return TrendReport(
            topic=topic,
            state=state,
            metrics=metrics,
            score=round(score, 1),
            platforms=[SocialSource.X, SocialSource.INSTAGRAM, SocialSource.TIKTOK],
            hashtags=[f"#{topic.replace(' ', '')}", "#SaudiFootball", "#SPL"],
            related_topics=self._get_related_topics(topic),
            key_accounts=["@SPL_EN", "@SFCNews", "@ArabFootball"],
            forecast=forecast,
            recommendations=[
                f"Cover {topic} immediately with breaking news format",
                "Deploy short-form video within 2 hours",
                "Engage key influencers on X",
            ],
        )

    async def _get_ai_insights(
        self, topic: str, state: TrendState, metrics: TrendMetrics
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Analyze Saudi football trend: {topic} (state={state.value}, velocity={metrics.velocity:.1f})",
                task_type="trend_analysis",
                max_tokens=150,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            return f"{topic} trending at {state.value} state with velocity {metrics.velocity:.1f}."

    def _get_default_topics(self) -> list[str]:
        return [
            "Al Hilal Champions League run",
            "Saudi Pro League quality debate",
            "Green Falcons World Cup qualification",
            "Foreign star player signing",
            "Saudi football academy development",
            "SPL broadcast rights expansion",
            "National team coach criticism",
            "Transfer window activity Saudi",
            "VAR controversy SPL",
            "Saudi national team coach",
        ]

    def _get_related_topics(self, topic: str) -> list[str]:
        base = ["Saudi Pro League", "Arabic Football", "خليجي"]
        return base[:2]
