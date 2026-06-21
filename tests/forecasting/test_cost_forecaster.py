"""Tests for the cost forecasting service and models."""

from __future__ import annotations

import pytest

from sfc.forecasting.cost.models import CostForecast, ForecastPeriod, ProviderForecast
from sfc.forecasting.cost.service import CostForecastService


class TestForecastPeriod:
    def test_all_periods(self):
        expected = {"daily", "weekly", "monthly", "quarterly", "annual"}
        assert {p.value for p in ForecastPeriod} == expected


class TestProviderForecast:
    def test_creation(self):
        pf = ProviderForecast(
            provider="anthropic",
            model="claude-sonnet",
            current_daily_usd=0.10,
            forecast_usd=3.0,
            forecast_period=ForecastPeriod.MONTHLY,
            calls_per_day=100.0,
            tokens_per_call=1000.0,
        )
        assert pf.provider == "anthropic"
        assert pf.forecast_usd == 3.0


class TestCostForecast:
    def _make_forecast(self, period=ForecastPeriod.MONTHLY) -> CostForecast:
        return CostForecast(
            period=period,
            run_rate_usd_per_day=0.5,
            forecast_total_usd=15.0,
            budget_limit_usd=100.0,
            budget_utilization_pct=15.0,
            within_budget=True,
            by_provider={"anthropic": 15.0},
            by_model={"claude-sonnet": 15.0},
            by_task_type={},
            budget_alerts=[],
            optimization_recommendations=["Cost within optimal range"],
            total_calls_this_session=50,
            fallback_rate_pct=100.0,
        )

    def test_creation(self):
        f = self._make_forecast()
        assert f.period == ForecastPeriod.MONTHLY
        assert f.within_budget is True
        assert f.forecast_id

    def test_to_dict_serializable(self):
        f = self._make_forecast()
        d = f.to_dict()
        assert isinstance(d, dict)
        assert d["period"] == "monthly"
        assert "forecast_id" in d
        assert "forecast_total_usd" in d

    def test_to_markdown_contains_key_info(self):
        f = self._make_forecast()
        md = f.to_markdown()
        assert "Cost Forecast" in md
        assert "monthly" in md.lower() or "Monthly" in md

    def test_budget_alert_when_exceeded(self):
        f = CostForecast(
            period=ForecastPeriod.DAILY,
            run_rate_usd_per_day=200.0,
            forecast_total_usd=200.0,
            budget_limit_usd=100.0,
            budget_utilization_pct=200.0,
            within_budget=False,
            budget_alerts=["BUDGET EXCEEDED"],
            optimization_recommendations=[],
            total_calls_this_session=1000,
            fallback_rate_pct=0.0,
        )
        assert f.within_budget is False
        assert len(f.budget_alerts) > 0


class TestCostForecastService:
    def test_forecast_returns_cost_forecast(self):
        service = CostForecastService()
        f = service.forecast()
        assert isinstance(f, CostForecast)
        assert f.period == ForecastPeriod.MONTHLY  # default

    def test_forecast_daily(self):
        service = CostForecastService()
        f = service.forecast(ForecastPeriod.DAILY)
        assert f.period == ForecastPeriod.DAILY

    def test_forecast_weekly(self):
        service = CostForecastService()
        f = service.forecast(ForecastPeriod.WEEKLY)
        assert f.period == ForecastPeriod.WEEKLY

    def test_forecast_quarterly(self):
        service = CostForecastService()
        f = service.forecast(ForecastPeriod.QUARTERLY)
        assert f.period == ForecastPeriod.QUARTERLY

    def test_forecast_annual(self):
        service = CostForecastService()
        f = service.forecast(ForecastPeriod.ANNUAL)
        assert f.period == ForecastPeriod.ANNUAL

    def test_forecast_all_periods(self):
        service = CostForecastService()
        results = service.forecast_all_periods()
        assert set(results.keys()) == {p.value for p in ForecastPeriod}
        for period_key, data in results.items():
            assert "forecast_usd" in data
            assert "within_budget" in data
            assert "utilization_pct" in data

    def test_history_accumulates(self):
        service = CostForecastService()
        service.forecast(ForecastPeriod.DAILY)
        service.forecast(ForecastPeriod.WEEKLY)
        service.forecast(ForecastPeriod.MONTHLY)
        history = service.get_history()
        assert len(history) == 3

    def test_history_returns_dicts(self):
        service = CostForecastService()
        service.forecast()
        history = service.get_history()
        assert isinstance(history[0], dict)
        assert "period" in history[0]

    def test_budget_limit_from_env(self, monkeypatch):
        monkeypatch.setenv("MAX_DAILY_AI_COST", "200")
        service = CostForecastService()
        f = service.forecast(ForecastPeriod.DAILY)
        assert f.budget_limit_usd == 200.0

    def test_within_budget_zero_cost(self):
        service = CostForecastService()
        f = service.forecast()
        # With no real API calls, cost tracker is zero → within budget
        assert f.within_budget is True

    def test_forecast_has_recommendations(self):
        service = CostForecastService()
        f = service.forecast()
        assert isinstance(f.optimization_recommendations, list)
        assert len(f.optimization_recommendations) >= 1

    def test_forecast_has_provider_forecasts(self):
        service = CostForecastService()
        f = service.forecast()
        assert isinstance(f.provider_forecasts, list)

    def test_fallback_rate_in_test_env(self):
        service = CostForecastService()
        f = service.forecast()
        # In test env with no API calls made, rate is 0 (0 fallback / 0 total)
        assert f.fallback_rate_pct >= 0.0
        assert f.fallback_rate_pct <= 100.0

    def test_multiple_forecasts_same_period(self):
        service = CostForecastService()
        f1 = service.forecast(ForecastPeriod.DAILY)
        f2 = service.forecast(ForecastPeriod.DAILY)
        assert f1.forecast_id != f2.forecast_id

    def test_forecast_total_weekly_gt_daily(self):
        service = CostForecastService()
        daily = service.forecast(ForecastPeriod.DAILY)
        weekly = service.forecast(ForecastPeriod.WEEKLY)
        # Weekly should be >= daily (7x)
        assert weekly.forecast_total_usd >= daily.forecast_total_usd
