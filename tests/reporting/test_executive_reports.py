"""Tests for executive reporting models and service."""

from __future__ import annotations

import pytest

from sfc.reporting.executive.models import (
    ExecutiveKPI,
    ExecutiveReport,
    ReportPeriod,
    ReportSection,
)
from sfc.reporting.executive.service import ExecutiveReportService


class TestReportPeriod:
    def test_all_periods_defined(self):
        expected = {"daily", "weekly", "monthly", "quarterly", "annual", "dashboard"}
        assert {p.value for p in ReportPeriod} == expected


class TestExecutiveKPI:
    def test_defaults(self):
        kpi = ExecutiveKPI(name="Reach", current_value=50000)
        assert kpi.trend == "stable"
        assert kpi.change_pct == 0.0
        assert kpi.on_track is True
        assert kpi.unit == ""

    def test_with_all_fields(self):
        kpi = ExecutiveKPI(
            name="Revenue",
            current_value=10000.0,
            previous_value=8000.0,
            unit="USD",
            trend="up",
            change_pct=25.0,
            target=12000.0,
            on_track=True,
        )
        assert kpi.name == "Revenue"
        assert kpi.change_pct == 25.0


class TestExecutiveReport:
    def _make_report(self, period=ReportPeriod.DAILY) -> ExecutiveReport:
        return ExecutiveReport(
            period=period,
            executive_summary="Strong performance this period.",
            key_wins=["Match coverage up 20%", "New sponsorship secured"],
            key_risks=["Transfer window volatility"],
            opportunities=["World Cup 2026 coverage"],
            recommendations=["Expand persona team"],
        )

    def test_report_creation(self):
        report = self._make_report()
        assert report.period == ReportPeriod.DAILY
        assert report.report_id  # generated

    def test_mandatory_sections_populated(self):
        report = self._make_report()
        assert len(report.key_wins) == 2
        assert len(report.key_risks) == 1
        assert len(report.opportunities) == 1
        assert len(report.recommendations) == 1

    def test_to_markdown_contains_sections(self):
        report = self._make_report()
        md = report.to_markdown()
        assert "# SFC Executive Report" in md
        assert "## Executive Summary" in md
        assert "## Key Wins" in md
        assert "## Key Risks" in md
        assert "## Opportunities" in md
        assert "## Recommendations" in md
        assert "## KPIs" in md

    def test_to_markdown_with_kpis(self):
        report = self._make_report()
        report.kpis = [
            ExecutiveKPI(name="Reach", current_value=50000, trend="up", change_pct=10.0)
        ]
        md = report.to_markdown()
        assert "Reach" in md
        assert "↑" in md

    def test_to_dict_is_serializable(self):
        report = self._make_report()
        d = report.to_dict()
        assert isinstance(d, dict)
        assert d["period"] == "daily"
        assert "report_id" in d
        assert "generated_at" in d

    def test_to_markdown_with_ai_insights(self):
        report = self._make_report()
        report.ai_insights = "AI recommends focusing on match-day content."
        md = report.to_markdown()
        assert "AI Insights" in md
        assert "match-day" in md

    def test_all_periods_can_be_created(self):
        for period in ReportPeriod:
            r = ExecutiveReport(period=period)
            assert r.period == period

    def test_content_stats_defaults(self):
        report = ExecutiveReport(period=ReportPeriod.WEEKLY)
        assert report.content_published == 0
        assert report.content_rejected == 0
        assert report.total_reach == 0
        assert report.total_revenue_opportunity_usd == 0.0


class TestExecutiveReportService:
    @pytest.mark.asyncio
    async def test_generate_daily_brief(self):
        service = ExecutiveReportService()
        report = await service.generate_daily_brief({})
        assert report.period == ReportPeriod.DAILY
        assert report.executive_summary
        assert isinstance(report.key_wins, list)

    @pytest.mark.asyncio
    async def test_generate_weekly_report(self):
        service = ExecutiveReportService()
        report = await service.generate_weekly_report({})
        assert report.period == ReportPeriod.WEEKLY
        assert report.executive_summary

    @pytest.mark.asyncio
    async def test_generate_monthly_review(self):
        service = ExecutiveReportService()
        report = await service.generate_monthly_review({})
        assert report.period == ReportPeriod.MONTHLY

    @pytest.mark.asyncio
    async def test_generate_quarterly_review(self):
        service = ExecutiveReportService()
        report = await service.generate_quarterly_review({})
        assert report.period == ReportPeriod.QUARTERLY

    @pytest.mark.asyncio
    async def test_generate_annual_summary(self):
        service = ExecutiveReportService()
        report = await service.generate_annual_summary({})
        assert report.period == ReportPeriod.ANNUAL

    @pytest.mark.asyncio
    async def test_generate_dashboard_pack(self):
        service = ExecutiveReportService()
        report = await service.generate_dashboard_pack({})
        assert report.period == ReportPeriod.DASHBOARD

    @pytest.mark.asyncio
    async def test_history_tracking(self):
        service = ExecutiveReportService()
        await service.generate_daily_brief({})
        await service.generate_weekly_report({})
        history = service.get_history()
        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_history_filtered_by_period(self):
        service = ExecutiveReportService()
        await service.generate_daily_brief({})
        await service.generate_weekly_report({})
        daily_history = service.get_history(period=ReportPeriod.DAILY)
        assert all(h["period"] == "daily" for h in daily_history)

    @pytest.mark.asyncio
    async def test_report_has_recommendations(self):
        service = ExecutiveReportService()
        report = await service.generate_daily_brief({"content_published": 5})
        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) >= 1

    @pytest.mark.asyncio
    async def test_report_has_kpis(self):
        service = ExecutiveReportService()
        report = await service.generate_daily_brief({})
        assert isinstance(report.kpis, list)
