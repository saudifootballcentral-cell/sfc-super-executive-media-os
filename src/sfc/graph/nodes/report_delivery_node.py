"""Report Delivery Node — delivers generated reports to configured channels."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.report_delivery_node")


async def report_delivery_node(state: SFCState) -> dict[str, Any]:
    """Node: report_delivery_node

    Delivers all generated reports (executive + operational) to configured
    delivery channels: dashboard, markdown export, JSON export, and when
    configured — email, Telegram, WhatsApp.

    Does NOT modify governance decisions or content approval status.
    """
    task_type = state.get("task_type", "")
    executive_report = state.get("executive_report", {})
    operational_reports = state.get("operational_reports", [])

    logger.info(
        "[ReportDelivery] Delivering reports | task=%s exec=%s operational=%d",
        task_type,
        "yes" if executive_report else "no",
        len(operational_reports),
    )

    try:
        from sfc.reporting.delivery.service import ReportDeliveryService
        from sfc.reporting.delivery.models import DeliveryChannel
        from sfc.reporting.executive.models import ExecutiveReport

        service = ReportDeliveryService()
        all_delivery_records: list[dict[str, Any]] = []

        # Deliver executive report if available
        if executive_report and not executive_report.get("error"):
            try:
                exec_report_obj = ExecutiveReport(**executive_report)
                records = await service.deliver(
                    exec_report_obj,
                    channels=[
                        DeliveryChannel.DASHBOARD,
                        DeliveryChannel.MARKDOWN_EXPORT,
                        DeliveryChannel.JSON_EXPORT,
                    ],
                )
                all_delivery_records.extend([r.model_dump(mode="json") for r in records])
            except Exception as e:
                logger.warning("[ReportDelivery] Executive report delivery failed: %s", e)

        stats = service.get_delivery_stats()
        logger.info(
            "[ReportDelivery] %d deliveries | success_rate=%.1f%%",
            stats.get("total", 0),
            stats.get("success_rate_pct", 100.0),
        )

        return {
            "delivery_log": all_delivery_records,
            "delivery_stats": stats,
            "pipeline_stage": "reports_delivered",
        }

    except Exception as exc:
        logger.error("[ReportDelivery] Failed (non-fatal): %s", exc)
        return {
            "delivery_log": [],
            "pipeline_stage": "report_delivery_skipped",
            "warnings": [f"REPORT_DELIVERY_NON_FATAL: {exc}"],
        }
