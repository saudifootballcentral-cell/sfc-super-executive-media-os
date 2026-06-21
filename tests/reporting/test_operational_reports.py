"""Tests for operational reporting models and service."""

from __future__ import annotations

import pytest

from sfc.reporting.operational.models import OperationalReport, OperationalReportType
from sfc.reporting.operational.service import OperationalReportService


class TestOperationalReportType:
    def test_all_types_defined(self):
        expected = {"war_room", "platform", "persona", "analytics", "revenue", "governance", "infrastructure"}
        assert {t.value for t in OperationalReportType} == expected


class TestOperationalReport:
    def _make_report(self, report_type=OperationalReportType.ANALYTICS) -> OperationalReport:
        return OperationalReport(
            report_type=report_type,
            title="Test Report",
            summary="Test summary.",
            data={"key": "value"},
            metrics={"score": 95.0},
        )

    def test_report_creation(self):
        report = self._make_report()
        assert report.report_id
        assert report.report_type == OperationalReportType.ANALYTICS
        assert report.status == "ok"

    def test_to_markdown_contains_title(self):
        report = self._make_report()
        md = report.to_markdown()
        assert "Test Report" in md

    def test_to_dict_serializable(self):
        report = self._make_report()
        d = report.to_dict()
        assert isinstance(d, dict)
        assert d["report_type"] == "analytics"
        assert "report_id" in d

    def test_to_dashboard_data_structure(self):
        report = self._make_report()
        dash = report.to_dashboard_data()
        assert isinstance(dash, dict)
        assert "type" in dash  # dashboard uses "type" key
        assert dash["type"] == "analytics"

    def test_status_values(self):
        for status in ["ok", "warning", "critical"]:
            report = OperationalReport(
                report_type=OperationalReportType.INFRASTRUCTURE,
                title="x",
                summary="y",
                status=status,
            )
            assert report.status == status

    def test_alerts_and_recommendations(self):
        report = OperationalReport(
            report_type=OperationalReportType.GOVERNANCE,
            title="Gov",
            summary="Gov check",
            alerts=["Alert A"],
            recommendations=["Rec 1"],
        )
        assert len(report.alerts) == 1
        assert len(report.recommendations) == 1


class TestOperationalReportService:
    @pytest.mark.asyncio
    async def test_war_room_report_inactive(self):
        service = OperationalReportService()
        report = await service.generate_war_room_report({})
        assert report.report_type == OperationalReportType.WAR_ROOM
        assert report.status == "ok"
        assert "INACTIVE" in report.summary

    @pytest.mark.asyncio
    async def test_war_room_report_active(self):
        service = OperationalReportService()
        state = {"war_room_state": {"activated": True, "war_room_type": "match_day"}}
        report = await service.generate_war_room_report(state)
        assert "ACTIVE" in report.summary
        assert report.status == "warning"

    @pytest.mark.asyncio
    async def test_platform_report_no_platforms(self):
        service = OperationalReportService()
        report = await service.generate_platform_report({})
        assert report.report_type == OperationalReportType.PLATFORM
        assert len(report.alerts) > 0  # no platforms reached → alert

    @pytest.mark.asyncio
    async def test_platform_report_with_reach(self):
        service = OperationalReportService()
        state = {
            "analytics_report": {
                "platforms_reached": 3,
                "estimated_reach": 50000,
                "performance_score": 85,
            }
        }
        report = await service.generate_platform_report(state)
        assert "3" in report.summary

    @pytest.mark.asyncio
    async def test_persona_report_no_personas(self):
        service = OperationalReportService()
        report = await service.generate_persona_report({})
        assert report.report_type == OperationalReportType.PERSONA
        assert len(report.alerts) > 0  # no personas → alert

    @pytest.mark.asyncio
    async def test_persona_report_with_personas(self):
        service = OperationalReportService()
        state = {
            "active_personas": ["khalid_sportscaster", "sara_analyst"],
            "persona_outputs": [{"persona_id": "khalid_sportscaster"}],
        }
        report = await service.generate_persona_report(state)
        assert "2" in report.summary

    @pytest.mark.asyncio
    async def test_analytics_report(self):
        service = OperationalReportService()
        state = {
            "approved_content": [{"id": 1}, {"id": 2}],
            "rejected_content": [{"id": 3}],
            "analytics_report": {"performance_score": 80, "estimated_reach": 25000},
        }
        report = await service.generate_analytics_report(state)
        assert report.report_type == OperationalReportType.ANALYTICS
        assert report.metrics["content_published"] == 2.0
        assert report.metrics["content_rejected"] == 1.0

    @pytest.mark.asyncio
    async def test_revenue_report_no_signals(self):
        service = OperationalReportService()
        report = await service.generate_revenue_report({})
        assert report.report_type == OperationalReportType.REVENUE
        assert report.status == "ok"

    @pytest.mark.asyncio
    async def test_revenue_report_with_high_value_signal(self):
        service = OperationalReportService()
        state = {
            "analytics_report": {
                "revenue_summary": {
                    "total_opportunity_usd": 50000,
                    "signal_count": 5,
                    "high_value_signals": 2,
                }
            }
        }
        report = await service.generate_revenue_report(state)
        assert report.status == "warning"
        assert len(report.alerts) > 0

    @pytest.mark.asyncio
    async def test_governance_report_high_approval(self):
        service = OperationalReportService()
        state = {
            "approved_content": [1, 2, 3],
            "rejected_content": [],
            "governance_reviews": [1, 2, 3],
        }
        report = await service.generate_governance_report(state)
        assert report.report_type == OperationalReportType.GOVERNANCE
        assert report.status == "ok"
        assert "100.0" in report.summary

    @pytest.mark.asyncio
    async def test_governance_report_low_approval(self):
        service = OperationalReportService()
        state = {
            "approved_content": [1],
            "rejected_content": [2, 3, 4, 5],
        }
        report = await service.generate_governance_report(state)
        assert report.status == "warning"

    @pytest.mark.asyncio
    async def test_infrastructure_report_ready(self):
        service = OperationalReportService()
        state = {"infrastructure_ready": True, "ai_metrics": {"calls": 10}}
        report = await service.generate_infrastructure_report(state)
        assert report.report_type == OperationalReportType.INFRASTRUCTURE
        assert report.status == "ok"

    @pytest.mark.asyncio
    async def test_infrastructure_report_not_ready(self):
        service = OperationalReportService()
        report = await service.generate_infrastructure_report({})
        assert len(report.alerts) > 0

    @pytest.mark.asyncio
    async def test_history_tracking(self):
        service = OperationalReportService()
        await service.generate_war_room_report({})
        await service.generate_platform_report({})
        history = service.get_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_history_filtered_by_type(self):
        service = OperationalReportService()
        await service.generate_war_room_report({})
        await service.generate_platform_report({})
        await service.generate_war_room_report({})
        war_history = service.get_history(report_type=OperationalReportType.WAR_ROOM)
        assert len(war_history) == 2
        assert all(h["report_type"] == "war_room" for h in war_history)
