"""Narrative Forecasting Engine — predicts future narrative trajectories."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.narrative.forecasting.models import (
    ForecastBundle,
    ForecastHorizon,
    HorizonForecast,
    NarrativeForecast,
)

logger = logging.getLogger("sfc.narrative.forecasting")

_singleton: "NarrativeForecastingEngine | None" = None


def get_forecasting_engine() -> "NarrativeForecastingEngine":
    global _singleton
    if _singleton is None:
        _singleton = NarrativeForecastingEngine()
    return _singleton


class NarrativeForecastingEngine:
    """Predicts narrative trajectories across 5 time horizons."""

    def __init__(self) -> None:
        self._gateway = None
        self._forecasts: list[NarrativeForecast] = []
        self._max_history = 500

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def forecast(
        self,
        narrative_id: str,
        narrative_title: str = "",
        current_metrics: dict[str, Any] | None = None,
    ) -> NarrativeForecast:
        """Generate multi-horizon forecast for a narrative."""
        metrics = current_metrics or {}
        base_score = metrics.get("strength_score", random.uniform(40, 80))
        base_sentiment = metrics.get("sentiment_score", random.uniform(-20, 60))
        base_reach = metrics.get("reach", random.randint(10000, 500000))
        base_velocity = metrics.get("velocity", random.uniform(1, 6))

        horizons: dict[str, HorizonForecast] = {}
        decay_factors = {
            ForecastHorizon.H24: 1.15,
            ForecastHorizon.H72: 1.05,
            ForecastHorizon.D7: 0.90,
            ForecastHorizon.D30: 0.70,
            ForecastHorizon.D90: 0.45,
        }

        for horizon, decay in decay_factors.items():
            h_forecast = self._build_horizon_forecast(
                horizon, base_score, base_sentiment, base_reach, base_velocity, decay
            )
            horizons[horizon.value] = h_forecast

        overall_score = round(
            sum(h.forecast_score * w for h, w in zip(
                list(horizons.values()),
                [0.4, 0.25, 0.2, 0.1, 0.05]
            )),
            1,
        )
        confidence = round(random.uniform(0.55, 0.90), 2)

        key_signals = await self._get_key_signals(narrative_title, base_score)
        forecast_narrative = await self._get_forecast_narrative(
            narrative_title, base_score, horizons
        )

        risk_signals = []
        opportunity_signals = []
        if base_sentiment < -20:
            risk_signals.append("Negative sentiment may accelerate decline")
        if base_velocity > 5:
            opportunity_signals.append("High velocity — amplification window open")
        if horizons[ForecastHorizon.H24.value].expected_virality > 70:
            opportunity_signals.append("Viral potential in next 24 hours")

        forecast = NarrativeForecast(
            narrative_id=narrative_id,
            narrative_title=narrative_title,
            horizons=horizons,
            overall_forecast_score=overall_score,
            forecast_narrative=forecast_narrative,
            key_signals=key_signals,
            risk_signals=risk_signals,
            opportunity_signals=opportunity_signals,
            confidence=confidence,
        )

        if len(self._forecasts) < self._max_history:
            self._forecasts.append(forecast)

        return forecast

    async def forecast_bundle(
        self,
        narratives: list[Any],
    ) -> ForecastBundle:
        """Forecast multiple narratives and return a bundle."""
        forecasts = []
        for n in narratives[:15]:
            if isinstance(n, str):
                f = await self.forecast(narrative_id=n)
            else:
                f = await self.forecast(
                    narrative_id=n.get("profile_id", n.get("narrative_id", "")),
                    narrative_title=n.get("title", ""),
                    current_metrics=n,
                )
            forecasts.append(f)

        top = max(forecasts, key=lambda f: f.overall_forecast_score, default=None)
        highest_risk = max(forecasts, key=lambda f: len(f.risk_signals), default=None)
        highest_opp = max(forecasts, key=lambda f: len(f.opportunity_signals), default=None)
        avg_conf = sum(f.confidence for f in forecasts) / max(len(forecasts), 1)

        return ForecastBundle(
            forecasts=forecasts,
            top_forecast=top,
            highest_risk_forecast=highest_risk,
            highest_opportunity_forecast=highest_opp,
            avg_confidence=round(avg_conf, 2),
        )

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self._forecasts[-limit:]]

    def _build_horizon_forecast(
        self,
        horizon: ForecastHorizon,
        base_score: float,
        base_sentiment: float,
        base_reach: int,
        base_velocity: float,
        decay: float,
    ) -> HorizonForecast:
        noise = random.uniform(0.85, 1.15)
        growth = round((decay - 1) * 100, 1)
        expected_reach = int(base_reach * decay * noise)
        expected_sentiment = round(max(-1.0, min(1.0, base_sentiment / 100 * decay)), 2)
        expected_virality = round(min(base_score * decay * noise, 100), 1)
        forecast_score = round(min(base_score * decay * noise, 100), 1)

        return HorizonForecast(
            horizon=horizon,
            expected_growth=growth,
            expected_reach=expected_reach,
            expected_sentiment=expected_sentiment,
            expected_influence=round(min(base_velocity * decay * 12, 100), 1),
            expected_virality=expected_virality,
            peak_probability=round(min(expected_virality / 100, 0.95), 2),
            confidence=round(1.0 - (0.15 * list(ForecastHorizon).index(horizon)), 2),
            forecast_score=forecast_score,
        )

    async def _get_key_signals(self, title: str, score: float) -> list[str]:
        signals = []
        if score > 70:
            signals.append("High strength narrative — strong media interest")
        if score < 40:
            signals.append("Weakening narrative — intervention may be needed")
        signals.append(f"Saudi football context driving {title} narrative")
        return signals

    async def _get_forecast_narrative(
        self, title: str, score: float, horizons: dict
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"24h narrative forecast for '{title}' (score={score:.0f})",
                task_type="narrative_forecasting",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            h24 = horizons.get(ForecastHorizon.H24.value)
            direction = "grow" if score > 50 else "decline"
            reach = f"{h24.expected_reach:,}" if h24 else "unknown"
            return f"'{title}' is forecast to {direction} over the next 24 hours with expected reach of {reach}."
