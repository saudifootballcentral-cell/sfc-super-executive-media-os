"""Email/Newsletter connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.email.models import (
    EmailCampaign,
    EmailCampaignStatus,
    EmailConnectorReport,
    EmailStats,
)

logger = logging.getLogger("sfc.connectors.email")

_singleton: "EmailService | None" = None


def get_email_service() -> "EmailService":
    global _singleton
    if _singleton is None:
        _singleton = EmailService()
    return _singleton


class EmailService:
    """Email/Newsletter connector service. All providers mocked; inject real credentials via
    EMAIL_SMTP_HOST / EMAIL_SMTP_PORT / EMAIL_USERNAME / EMAIL_PASSWORD /
    EMAIL_FROM_ADDRESS / EMAIL_LIST_ID env vars."""

    def __init__(self) -> None:
        self._smtp_host = os.environ.get("EMAIL_SMTP_HOST", "")
        self._smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
        self._username = os.environ.get("EMAIL_USERNAME", "")
        self._password = os.environ.get("EMAIL_PASSWORD", "")
        self._from_address = os.environ.get("EMAIL_FROM_ADDRESS", "")
        self._list_id = os.environ.get("EMAIL_LIST_ID", "")
        self._observability = ConnectorObservability(connector="email")
        self._campaign_history: list[EmailCampaign] = []
        self._single_email_count = 0

    def _next_campaign_id(self) -> str:
        return f"campaign_{uuid4().hex[:12]}"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def send_newsletter(
        self,
        subject: str,
        html_content: str,
        recipient_list: list[str],
    ) -> dict[str, Any]:
        """Send a newsletter to a list of recipients (mocked)."""
        try:
            campaign_id = self._next_campaign_id()
            campaign = EmailCampaign(
                platform_campaign_id=campaign_id,
                subject=subject,
                html_content=html_content,
                recipient_count=len(recipient_list),
                status=EmailCampaignStatus.SENT,
                sent_at=datetime.utcnow(),
            )
            self._campaign_history.append(campaign)
            self._observability.record_success(latency_ms=580.0)
            logger.info(
                "[Email] Newsletter sent | id=%s subject=%s recipients=%d",
                campaign_id, subject[:40], len(recipient_list),
            )
            return campaign.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def send_single_email(
        self, to: str, subject: str, html_content: str
    ) -> dict[str, Any]:
        """Send a single email (mocked)."""
        try:
            self._single_email_count += 1
            msg_id = f"msg_{uuid4().hex[:12]}"
            self._observability.record_success(latency_ms=180.0)
            logger.info("[Email] Single email sent | to=%s subject=%s", to, subject[:40])
            return {
                "message_id": msg_id,
                "to": to,
                "subject": subject,
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat(),
                "success": True,
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_campaign_stats(self, campaign_id: str) -> dict[str, Any]:
        """Get stats for an email campaign (mocked)."""
        try:
            stats = EmailStats(
                campaign_id=campaign_id,
                sent=12_400,
                delivered=12_200,
                opened=4_880,
                clicked=1_464,
                bounced=200,
                unsubscribed=24,
                open_rate=39.4,
                click_rate=11.8,
            )
            self._observability.record_success(latency_ms=130.0)
            return stats.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> EmailConnectorReport:
        avg_open = 39.4 if self._campaign_history else 0.0
        total_recipients = sum(c.recipient_count for c in self._campaign_history)
        return EmailConnectorReport(
            newsletters_sent=len(self._campaign_history),
            single_emails_sent=self._single_email_count,
            total_recipients=total_recipients,
            avg_open_rate=avg_open,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._smtp_host and self._username and self._password)
