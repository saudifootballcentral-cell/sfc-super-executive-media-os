"""Tests for report delivery service and models."""

from __future__ import annotations

import os
import pytest

from sfc.reporting.delivery.models import DeliveryChannel, DeliveryRecord, DeliveryStatus
from sfc.reporting.delivery.service import ReportDeliveryService
from sfc.reporting.executive.models import ExecutiveReport, ReportPeriod


class _MockReport:
    """Minimal mock report for delivery tests."""

    def __init__(self):
        self.report_id = "test-report-123"
        self.report_type = "test"

    def to_markdown(self) -> str:
        return "# Test Report\n\nTest content."

    def to_dict(self) -> dict:
        return {"report_id": self.report_id, "type": "test"}


class TestDeliveryModels:
    def test_delivery_channels(self):
        expected = {"email", "telegram", "whatsapp", "dashboard", "markdown_export", "json_export", "slack", "teams", "notion"}
        assert {c.value for c in DeliveryChannel} == expected

    def test_delivery_status_values(self):
        assert DeliveryStatus.PENDING.value == "pending"
        assert DeliveryStatus.DELIVERED.value == "delivered"
        assert DeliveryStatus.FAILED.value == "failed"
        assert DeliveryStatus.SKIPPED.value == "skipped"

    def test_delivery_record_defaults(self):
        record = DeliveryRecord(
            report_id="r1",
            report_type="executive",
            channel=DeliveryChannel.DASHBOARD,
        )
        assert record.delivery_id
        assert record.status == DeliveryStatus.PENDING
        assert record.error is None


class TestReportDeliveryService:
    @pytest.mark.asyncio
    async def test_dashboard_delivery_succeeds(self):
        service = ReportDeliveryService()
        report = _MockReport()
        records = await service.deliver(report, [DeliveryChannel.DASHBOARD])
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.DELIVERED
        assert records[0].channel == DeliveryChannel.DASHBOARD

    @pytest.mark.asyncio
    async def test_markdown_export_no_dir(self):
        service = ReportDeliveryService()  # no export dir
        report = _MockReport()
        records = await service.deliver(report, [DeliveryChannel.MARKDOWN_EXPORT])
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.DELIVERED
        assert records[0].metadata.get("length", 0) > 0

    @pytest.mark.asyncio
    async def test_json_export_no_dir(self):
        service = ReportDeliveryService()
        report = _MockReport()
        records = await service.deliver(report, [DeliveryChannel.JSON_EXPORT])
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_email_skipped_without_smtp(self):
        env = os.environ.pop("SMTP_HOST", None)
        try:
            service = ReportDeliveryService()
            report = _MockReport()
            records = await service.deliver(report, [DeliveryChannel.EMAIL])
            assert records[0].status == DeliveryStatus.SKIPPED
        finally:
            if env:
                os.environ["SMTP_HOST"] = env

    @pytest.mark.asyncio
    async def test_telegram_skipped_without_token(self):
        env = os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        try:
            service = ReportDeliveryService()
            report = _MockReport()
            records = await service.deliver(report, [DeliveryChannel.TELEGRAM])
            assert records[0].status == DeliveryStatus.SKIPPED
        finally:
            if env:
                os.environ["TELEGRAM_BOT_TOKEN"] = env

    @pytest.mark.asyncio
    async def test_whatsapp_skipped_without_key(self):
        env = os.environ.pop("WHATSAPP_API_KEY", None)
        try:
            service = ReportDeliveryService()
            report = _MockReport()
            records = await service.deliver(report, [DeliveryChannel.WHATSAPP])
            assert records[0].status == DeliveryStatus.SKIPPED
        finally:
            if env:
                os.environ["WHATSAPP_API_KEY"] = env

    @pytest.mark.asyncio
    async def test_unsupported_channel_skipped(self):
        service = ReportDeliveryService()
        report = _MockReport()
        records = await service.deliver(report, [DeliveryChannel.SLACK])
        assert records[0].status == DeliveryStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_deliver_all_returns_three_records(self):
        service = ReportDeliveryService()
        report = _MockReport()
        records = await service.deliver_all(report)
        assert len(records) == 3
        channels = {r.channel for r in records}
        assert DeliveryChannel.DASHBOARD in channels
        assert DeliveryChannel.MARKDOWN_EXPORT in channels
        assert DeliveryChannel.JSON_EXPORT in channels

    @pytest.mark.asyncio
    async def test_multiple_channels_in_one_call(self):
        service = ReportDeliveryService()
        report = _MockReport()
        records = await service.deliver(
            report,
            [DeliveryChannel.DASHBOARD, DeliveryChannel.MARKDOWN_EXPORT, DeliveryChannel.JSON_EXPORT],
        )
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_delivery_log_populated(self):
        service = ReportDeliveryService()
        report = _MockReport()
        await service.deliver(report, [DeliveryChannel.DASHBOARD, DeliveryChannel.JSON_EXPORT])
        log = service.get_delivery_log()
        assert len(log) == 2

    @pytest.mark.asyncio
    async def test_delivery_stats_structure(self):
        service = ReportDeliveryService()
        report = _MockReport()
        await service.deliver(report, [DeliveryChannel.DASHBOARD])
        stats = service.get_delivery_stats()
        assert "total" in stats
        assert "delivered" in stats
        assert "failed" in stats
        assert "success_rate_pct" in stats
        assert stats["total"] == 1
        assert stats["delivered"] == 1

    @pytest.mark.asyncio
    async def test_read_status_for_report(self):
        service = ReportDeliveryService()
        report = _MockReport()
        await service.deliver(
            report,
            [DeliveryChannel.DASHBOARD, DeliveryChannel.JSON_EXPORT],
        )
        status = service.get_read_status("test-report-123")
        assert status["report_id"] == "test-report-123"
        assert status["total_deliveries"] == 2
        assert status["successful"] == 2

    @pytest.mark.asyncio
    async def test_executive_report_deliverable(self):
        service = ReportDeliveryService()
        report = ExecutiveReport(
            period=ReportPeriod.DAILY,
            executive_summary="Daily summary here.",
        )
        records = await service.deliver(
            report,
            [DeliveryChannel.DASHBOARD, DeliveryChannel.MARKDOWN_EXPORT],
        )
        assert all(r.status == DeliveryStatus.DELIVERED for r in records)

    @pytest.mark.asyncio
    async def test_delivery_never_raises_on_bad_report(self):
        service = ReportDeliveryService()

        class BadReport:
            report_id = "bad"
            report_type = "broken"
            def to_markdown(self):
                raise RuntimeError("markdown broken")
            def to_dict(self):
                raise RuntimeError("dict broken")

        records = await service.deliver(BadReport(), [DeliveryChannel.MARKDOWN_EXPORT])
        # Should either succeed (exception caught in _deliver_markdown) or fail gracefully
        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_markdown_export_with_dir(self, tmp_path):
        service = ReportDeliveryService(export_dir=str(tmp_path))
        report = _MockReport()
        records = await service.deliver(report, [DeliveryChannel.MARKDOWN_EXPORT])
        assert records[0].status == DeliveryStatus.DELIVERED
        assert "file" in records[0].metadata
