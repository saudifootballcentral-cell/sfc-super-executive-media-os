"""Tests for Production Quality Control (Package 8E)."""

from __future__ import annotations

import pytest

from sfc.creative.quality.models import (
    QualityBatch,
    QualityCheck,
    QualityCheckResult,
    QualityCheckType,
    QualityReport,
)
from sfc.creative.quality.service import QualityControlService, get_quality_control_service


class TestQualityModels:
    def test_quality_check_defaults(self):
        qc = QualityCheck(
            check_type=QualityCheckType.BRAND_ALIGNMENT,
            result=QualityCheckResult.PASS,
        )
        assert qc.check_id
        assert qc.score == 0.0

    def test_quality_report_to_dict(self):
        report = QualityReport(asset_id="test", asset_title="Test Asset")
        d = report.to_dict()
        assert "asset_id" in d
        assert "checks" in d

    def test_quality_report_to_summary_approved(self):
        report = QualityReport(asset_title="Good Asset", approved=True, overall_score=85)
        summary = report.to_summary()
        assert "APPROVED" in summary
        assert "85" in summary

    def test_quality_report_to_summary_rejected(self):
        report = QualityReport(asset_title="Bad Asset", approved=False, overall_score=45)
        summary = report.to_summary()
        assert "REJECTED" in summary

    def test_quality_batch_to_dict(self):
        batch = QualityBatch(total_reviewed=5, total_approved=4, pass_rate=80.0)
        d = batch.to_dict()
        assert d["total_reviewed"] == 5
        assert d["pass_rate"] == 80.0


class TestQualityControlService:
    @pytest.mark.asyncio
    async def test_review_asset_returns_report(self):
        service = QualityControlService()
        report = await service.review_asset(
            asset_id="img-001",
            asset_type="image",
            asset_title="Al Hilal Poster",
        )
        assert isinstance(report, QualityReport)
        assert report.asset_id == "img-001"
        assert report.asset_title == "Al Hilal Poster"

    @pytest.mark.asyncio
    async def test_five_checks_run(self):
        service = QualityControlService()
        report = await service.review_asset(
            asset_id="test", asset_type="video", asset_title="Test Video"
        )
        assert len(report.checks) == 5
        check_types = {c.check_type for c in report.checks}
        assert check_types == set(QualityCheckType)

    @pytest.mark.asyncio
    async def test_overall_score_is_average(self):
        service = QualityControlService()
        report = await service.review_asset(
            asset_id="avg", asset_type="image", asset_title="Score Test"
        )
        expected = sum(c.score for c in report.checks) / 5
        assert abs(report.overall_score - expected) < 0.1

    @pytest.mark.asyncio
    async def test_approved_when_score_above_threshold(self):
        service = QualityControlService()
        report = await service.review_asset(
            asset_id="high", asset_type="image", asset_title="High Quality"
        )
        expected_approved = report.overall_score >= 70.0
        assert report.approved == expected_approved

    @pytest.mark.asyncio
    async def test_review_batch(self):
        service = QualityControlService()
        assets = [
            {"asset_id": "a1", "asset_type": "image", "title": "Image A"},
            {"asset_id": "a2", "asset_type": "video", "title": "Video B"},
        ]
        batch = await service.review_batch(assets)
        assert isinstance(batch, QualityBatch)
        assert batch.total_reviewed == 2
        assert batch.total_approved + batch.total_rejected == 2

    @pytest.mark.asyncio
    async def test_pass_rate_calculated(self):
        service = QualityControlService()
        assets = [{"asset_id": f"a{i}", "asset_type": "image", "title": f"Asset {i}"} for i in range(4)]
        batch = await service.review_batch(assets)
        expected_rate = (batch.total_approved / 4) * 100
        assert abs(batch.pass_rate - expected_rate) < 0.1

    def test_singleton(self):
        s1 = get_quality_control_service()
        s2 = get_quality_control_service()
        assert s1 is s2
