"""Executive Reporting Node — generates executive reports from pipeline state."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.executive_reporting_node")


async def executive_reporting_node(state: SFCState) -> dict[str, Any]:
    """Node: executive_reporting_node

    Generates the executive report for this pipeline run.
    Report type is determined by task_type prefix:
      executive_brief / daily_*  → daily brief
      weekly_*                   → weekly report
      monthly_*                  → monthly review
      quarterly_*                → quarterly review
      annual_*                   → annual summary
      (default)                  → daily brief

    Does NOT modify governance decisions or content approval status.
    """
    task_type = state.get("task_type", "")
    run_id = state.get("run_id", "")

    logger.info("[ExecutiveReporting] Generating report | task=%s", task_type)

    try:
        from sfc.reporting.executive.service import ExecutiveReportService
        from sfc.reporting.executive.models import ReportPeriod

        service = ExecutiveReportService()
        context = dict(state)

        # Determine report period from task_type
        if "weekly" in task_type:
            period = ReportPeriod.WEEKLY
            report = await service.generate_weekly_report(context)
        elif "monthly" in task_type:
            period = ReportPeriod.MONTHLY
            report = await service.generate_monthly_review(context)
        elif "quarterly" in task_type:
            period = ReportPeriod.QUARTERLY
            report = await service.generate_quarterly_review(context)
        elif "annual" in task_type:
            period = ReportPeriod.ANNUAL
            report = await service.generate_annual_summary(context)
        elif "dashboard" in task_type:
            period = ReportPeriod.DASHBOARD
            report = await service.generate_dashboard_pack(context)
        else:
            period = ReportPeriod.DAILY
            report = await service.generate_daily_brief(context)

        logger.info(
            "[ExecutiveReporting] %s report generated | id=%s revenue=$%.0f",
            period.value,
            report.report_id,
            report.total_revenue_opportunity_usd,
        )

        return {
            "executive_report": report.to_dict(),
            "pipeline_stage": "executive_report_generated",
        }

    except Exception as exc:
        logger.error("[ExecutiveReporting] Failed (non-fatal): %s", exc)
        return {
            "executive_report": {"error": str(exc), "generated": False},
            "pipeline_stage": "executive_report_skipped",
            "warnings": [f"EXECUTIVE_REPORTING_NON_FATAL: {exc}"],
        }
