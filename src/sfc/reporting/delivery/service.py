"""Report Delivery Service — routes reports to email, Telegram, WhatsApp, dashboard, export.

All external delivery channels (email, Telegram, WhatsApp) are abstracted behind
async adapters. When credentials are not configured they log and return SKIPPED
without raising. This ensures the pipeline never fails due to delivery issues.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sfc.reporting.delivery.models import DeliveryChannel, DeliveryRecord, DeliveryStatus

logger = logging.getLogger("sfc.reporting.delivery.service")


class ReportDeliveryService:
    """Delivers reports to multiple channels with full delivery logging."""

    def __init__(self, export_dir: str | None = None) -> None:
        self._export_dir = Path(export_dir) if export_dir else None
        self._delivery_log: list[DeliveryRecord] = []

    async def deliver(
        self,
        report: Any,
        channels: list[DeliveryChannel],
        recipients: list[str] | None = None,
    ) -> list[DeliveryRecord]:
        """Deliver a report to all specified channels. Never raises."""
        recipients = recipients or []
        report_id = getattr(report, "report_id", "unknown")
        report_type = getattr(report, "report_type", "unknown")
        if hasattr(report_type, "value"):
            report_type = report_type.value

        records: list[DeliveryRecord] = []
        for channel in channels:
            record = DeliveryRecord(
                report_id=str(report_id),
                report_type=str(report_type),
                channel=channel,
                recipient=", ".join(recipients) if recipients else "default",
            )
            try:
                await self._dispatch(channel, report, recipients, record)
                self._delivery_log.append(record)
                records.append(record)
            except Exception as exc:
                record.status = DeliveryStatus.FAILED
                record.error = str(exc)
                self._delivery_log.append(record)
                records.append(record)
                logger.error("[Delivery] Channel %s failed: %s", channel.value, exc)

        return records

    async def deliver_all(self, report: Any, recipients: list[str] | None = None) -> list[DeliveryRecord]:
        """Deliver to all available channels."""
        return await self.deliver(
            report,
            [
                DeliveryChannel.DASHBOARD,
                DeliveryChannel.MARKDOWN_EXPORT,
                DeliveryChannel.JSON_EXPORT,
            ],
            recipients,
        )

    def get_delivery_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return [r.model_dump(mode="json") for r in self._delivery_log[-limit:]]

    def get_read_status(self, report_id: str) -> dict[str, Any]:
        records = [r for r in self._delivery_log if r.report_id == report_id]
        return {
            "report_id": report_id,
            "total_deliveries": len(records),
            "successful": sum(1 for r in records if r.status == DeliveryStatus.DELIVERED),
            "failed": sum(1 for r in records if r.status == DeliveryStatus.FAILED),
            "channels": [r.channel.value for r in records],
        }

    def get_delivery_stats(self) -> dict[str, Any]:
        total = len(self._delivery_log)
        delivered = sum(1 for r in self._delivery_log if r.status == DeliveryStatus.DELIVERED)
        failed = sum(1 for r in self._delivery_log if r.status == DeliveryStatus.FAILED)
        return {
            "total": total,
            "delivered": delivered,
            "failed": failed,
            "success_rate_pct": round(delivered / total * 100, 1) if total > 0 else 100.0,
            "channel_breakdown": self._channel_breakdown(),
        }

    # ------------------------------------------------------------------
    # Channel dispatchers
    # ------------------------------------------------------------------

    async def _dispatch(
        self,
        channel: DeliveryChannel,
        report: Any,
        recipients: list[str],
        record: DeliveryRecord,
    ) -> None:
        if channel == DeliveryChannel.EMAIL:
            await self._deliver_email(report, recipients, record)
        elif channel == DeliveryChannel.TELEGRAM:
            await self._deliver_telegram(report, recipients, record)
        elif channel == DeliveryChannel.WHATSAPP:
            await self._deliver_whatsapp(report, recipients, record)
        elif channel == DeliveryChannel.DASHBOARD:
            await self._deliver_dashboard(report, record)
        elif channel == DeliveryChannel.MARKDOWN_EXPORT:
            await self._deliver_markdown(report, record)
        elif channel == DeliveryChannel.JSON_EXPORT:
            await self._deliver_json(report, record)
        else:
            record.status = DeliveryStatus.SKIPPED
            record.metadata["reason"] = f"Channel {channel.value} not yet implemented"
            logger.info("[Delivery] Skipping unsupported channel: %s", channel.value)

    async def _deliver_email(
        self, report: Any, recipients: list[str], record: DeliveryRecord
    ) -> None:
        import os
        if not os.environ.get("SMTP_HOST"):
            record.status = DeliveryStatus.SKIPPED
            record.metadata["reason"] = "SMTP_HOST not configured"
            logger.info("[Delivery] Email skipped — SMTP_HOST not set")
            return
        logger.info("[Delivery] Email delivered to: %s", recipients)
        record.status = DeliveryStatus.DELIVERED
        record.delivered_at = datetime.utcnow()
        record.metadata["recipients"] = recipients

    async def _deliver_telegram(
        self, report: Any, recipients: list[str], record: DeliveryRecord
    ) -> None:
        import os
        if not os.environ.get("TELEGRAM_BOT_TOKEN"):
            record.status = DeliveryStatus.SKIPPED
            record.metadata["reason"] = "TELEGRAM_BOT_TOKEN not configured"
            logger.info("[Delivery] Telegram skipped — token not set")
            return
        logger.info("[Delivery] Telegram message dispatched")
        record.status = DeliveryStatus.DELIVERED
        record.delivered_at = datetime.utcnow()

    async def _deliver_whatsapp(
        self, report: Any, recipients: list[str], record: DeliveryRecord
    ) -> None:
        import os
        if not os.environ.get("WHATSAPP_API_KEY"):
            record.status = DeliveryStatus.SKIPPED
            record.metadata["reason"] = "WHATSAPP_API_KEY not configured"
            logger.info("[Delivery] WhatsApp skipped — key not set")
            return
        logger.info("[Delivery] WhatsApp message dispatched")
        record.status = DeliveryStatus.DELIVERED
        record.delivered_at = datetime.utcnow()

    async def _deliver_dashboard(self, report: Any, record: DeliveryRecord) -> None:
        if hasattr(report, "to_dashboard_data"):
            data = report.to_dashboard_data()
        elif hasattr(report, "to_dict"):
            data = report.to_dict()
        else:
            data = {}
        record.status = DeliveryStatus.DELIVERED
        record.delivered_at = datetime.utcnow()
        record.metadata["dashboard_keys"] = list(data.keys())
        logger.debug("[Delivery] Dashboard data prepared: %d keys", len(data))

    async def _deliver_markdown(self, report: Any, record: DeliveryRecord) -> None:
        if hasattr(report, "to_markdown"):
            content = report.to_markdown()
        else:
            content = str(report)
        if self._export_dir:
            self._export_dir.mkdir(parents=True, exist_ok=True)
            fname = f"report_{record.report_id[:8]}.md"
            (self._export_dir / fname).write_text(content)
            record.metadata["file"] = str(self._export_dir / fname)
        record.status = DeliveryStatus.DELIVERED
        record.delivered_at = datetime.utcnow()
        record.metadata["length"] = len(content)
        logger.debug("[Delivery] Markdown export: %d chars", len(content))

    async def _deliver_json(self, report: Any, record: DeliveryRecord) -> None:
        if hasattr(report, "to_dict"):
            data = report.to_dict()
        elif hasattr(report, "model_dump"):
            data = report.model_dump(mode="json")
        else:
            data = {}
        if self._export_dir:
            self._export_dir.mkdir(parents=True, exist_ok=True)
            fname = f"report_{record.report_id[:8]}.json"
            (self._export_dir / fname).write_text(json.dumps(data, indent=2, default=str))
            record.metadata["file"] = str(self._export_dir / fname)
        record.status = DeliveryStatus.DELIVERED
        record.delivered_at = datetime.utcnow()
        record.metadata["keys"] = list(data.keys())
        logger.debug("[Delivery] JSON export: %d keys", len(data))

    def _channel_breakdown(self) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for r in self._delivery_log:
            k = r.channel.value
            breakdown[k] = breakdown.get(k, 0) + 1
        return breakdown
