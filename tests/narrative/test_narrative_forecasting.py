"""Tests for Narrative Forecasting Engine."""

import pytest

from sfc.narrative.forecasting.models import (
    ForecastBundle,
    ForecastHorizon,
    HorizonForecast,
    NarrativeForecast,
)
from sfc.narrative.forecasting.service import NarrativeForecastingEngine, get_forecasting_engine


class TestForecastHorizon:
    def test_horizon_values(self):
        assert ForecastHorizon.H24 == "24h"
        assert ForecastHorizon.H72 == "72h"
        assert ForecastHorizon.D7 == "7d"
        assert ForecastHorizon.D30 == "30d"
        assert ForecastHorizon.D90 == "90d"


class TestHorizonForecast:
    def test_create(self):
        h = HorizonForecast(
            horizon=ForecastHorizon.H24,
            expected_growth=15.0,
            expected_reach=500000,
            expected_sentiment=70.0,
            expected_influence=65.0,
            expected_virality=40.0,
            peak_probability=0.8,
            confidence=0.85,
            forecast_score=75.0,
        )
        assert h.horizon == ForecastHorizon.H24
        assert h.confidence == 0.85

    def test_to_dict(self):
        h = HorizonForecast(
            horizon=ForecastHorizon.D7,
            expected_growth=5.0,
            expected_reach=200000,
            expected_sentiment=60.0,
            expected_influence=55.0,
            expected_virality=30.0,
            peak_probability=0.5,
            confidence=0.7,
            forecast_score=60.0,
        )
        d = h.to_dict()
        assert isinstance(d, dict)
        assert d["horizon"] == ForecastHorizon.D7


class TestNarrativeForecast:
    def _make_horizons(self):
        return {
            ForecastHorizon.H24: HorizonForecast(
                horizon=ForecastHorizon.H24,
                expected_growth=20.0,
                expected_reach=600000,
                expected_sentiment=70.0,
                expected_influence=65.0,
                expected_virality=50.0,
                peak_probability=0.9,
                confidence=0.85,
                forecast_score=80.0,
            )
        }

    def test_create(self):
        f = NarrativeForecast(
            narrative_id="n_001",
            narrative_title="Test Forecast",
            horizons=self._make_horizons(),
            overall_forecast_score=75.0,
            confidence=0.8,
        )
        assert f.narrative_id == "n_001"
        assert f.forecast_id != ""

    def test_to_dict(self):
        f = NarrativeForecast(
            narrative_id="n_001",
            narrative_title="Test",
            horizons=self._make_horizons(),
            overall_forecast_score=70.0,
            confidence=0.8,
        )
        d = f.to_dict()
        assert isinstance(d, dict)
        assert "forecast_id" in d

    def test_to_summary(self):
        f = NarrativeForecast(
            narrative_id="n_001",
            narrative_title="Summary",
            horizons=self._make_horizons(),
            overall_forecast_score=80.0,
            confidence=0.85,
        )
        s = f.to_summary()
        assert isinstance(s, str)
        assert len(s) > 0


class TestNarrativeForecastingEngine:
    @pytest.fixture
    def engine(self):
        return NarrativeForecastingEngine()

    @pytest.mark.asyncio
    async def test_forecast(self, engine):
        forecast = await engine.forecast("narrative_001")
        assert isinstance(forecast, NarrativeForecast)
        assert forecast.narrative_id == "narrative_001"

    @pytest.mark.asyncio
    async def test_forecast_has_horizons(self, engine):
        forecast = await engine.forecast("n_test")
        assert isinstance(forecast.horizons, dict)
        assert len(forecast.horizons) > 0

    @pytest.mark.asyncio
    async def test_forecast_confidence(self, engine):
        forecast = await engine.forecast("n_confidence")
        assert 0 <= forecast.confidence <= 1

    @pytest.mark.asyncio
    async def test_forecast_overall_score(self, engine):
        forecast = await engine.forecast("n_score")
        assert 0 <= forecast.overall_forecast_score <= 100

    @pytest.mark.asyncio
    async def test_forecast_bundle(self, engine):
        ids = ["n1", "n2", "n3"]
        bundle = await engine.forecast_bundle(ids)
        assert isinstance(bundle, ForecastBundle)
        assert len(bundle.forecasts) == 3

    @pytest.mark.asyncio
    async def test_bundle_to_dict(self, engine):
        bundle = await engine.forecast_bundle(["a", "b"])
        d = bundle.to_dict()
        assert isinstance(d, dict)
        assert "forecasts" in d

    @pytest.mark.asyncio
    async def test_bundle_avg_confidence(self, engine):
        bundle = await engine.forecast_bundle(["x", "y"])
        assert 0 <= bundle.avg_confidence <= 1

    @pytest.mark.asyncio
    async def test_horizon_decay(self, engine):
        forecast = await engine.forecast("n_decay")
        horizons = forecast.horizons
        if ForecastHorizon.H24 in horizons and ForecastHorizon.D90 in horizons:
            assert horizons[ForecastHorizon.H24].expected_growth >= horizons[ForecastHorizon.D90].expected_growth

    def test_singleton(self):
        a = get_forecasting_engine()
        b = get_forecasting_engine()
        assert a is b

    @pytest.mark.asyncio
    async def test_key_signals_list(self, engine):
        forecast = await engine.forecast("n_signals")
        assert isinstance(forecast.key_signals, list)
