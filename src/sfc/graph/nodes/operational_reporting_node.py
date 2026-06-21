"""Operational Reporting Node — generates all operational reports from pipeline state."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.operational_reporting_node")


async def operational_reporting_node(state: SFCState) -> dict[str, Any]:
    """Node: operational_reporting_node

    Generates war room, platform, persona, analytics, revenue, governance,
    and infrastructure reports from the completed pipeline state.

    Does NOT modify governance decisions or content approval status.
    """
    task_type = state.get("task_type", "")

    logger.info("[OperationalReporting] Generating reports | task=%s", task_type)

    try:
        from sfc.reporting.operational.service import OperationalReportService

        service = OperationalReportService()
        context = dict(state)

        # Generate all operational reports concurrently
        import asyncio
        results = await asyncio.gather(
            service.generate_war_room_report(context),
            service.generate_platform_report(context),
            service.generate_persona_report(context),
            service.generate_analytics_report(context),
            service.generate_revenue_report(context),
            service.generate_governance_report(context),
            service.generate_infrastructure_report(context),
            return_exceptions=True,
        )

        operational_reports = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("[OperationalReporting] Report failed (non-fatal): %s", r)
            else:
                operational_reports.append(r.to_dict())

        critical_count = sum(
            1 for r in operational_reports if r.get("status") == "critical"
        )
        warning_count = sum(
            1 for r in operational_reports if r.get("status") == "warning"
        )

        logger.info(
            "[OperationalReporting] %d reports generated | critical=%d warnings=%d",
            len(operational_reports),
            critical_count,
            warning_count,
        )

        return {
            "operational_reports": operational_reports,
            "pipeline_stage": "operational_reports_generated",
        }

    except Exception as exc:
        logger.error("[OperationalReporting] Failed (non-fatal): %s", exc)
        return {
            "operational_reports": [],
            "pipeline_stage": "operational_reports_skipped",
            "warnings": [f"OPERATIONAL_REPORTING_NON_FATAL: {exc}"],
        }
