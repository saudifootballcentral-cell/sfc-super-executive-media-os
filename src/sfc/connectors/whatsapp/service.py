"""WhatsApp Business API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.whatsapp.models import (
    WhatsAppConnectorReport,
    WhatsAppMedia,
    WhatsAppMessage,
    WhatsAppMessageStatus,
    WhatsAppTemplate,
)

logger = logging.getLogger("sfc.connectors.whatsapp")

_singleton: "WhatsAppService | None" = None


def get_whatsapp_service() -> "WhatsAppService":
    global _singleton
    if _singleton is None:
        _singleton = WhatsAppService()
    return _singleton


class WhatsAppService:
    """WhatsApp Business API connector. All providers mocked; inject real credentials via
    WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_BUSINESS_ACCOUNT_ID env vars."""

    _BASE_MSG_ID = "wamid.mock."

    def __init__(self) -> None:
        self._access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
        self._phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self._business_account_id = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
        self._observability = ConnectorObservability(connector="whatsapp")
        self._message_history: list[WhatsAppMessage] = []
        self._media_history: list[WhatsAppMedia] = []
        self._template_history: list[WhatsAppTemplate] = []

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def send_text(self, to: str, text: str) -> dict[str, Any]:
        """Send a text message via WhatsApp Business API (mocked)."""
        try:
            msg_id = f"{self._BASE_MSG_ID}{uuid4().hex[:16]}"
            message = WhatsAppMessage(
                platform_message_id=msg_id,
                to=to,
                text=text,
                status=WhatsAppMessageStatus.SENT,
                sent_at=datetime.utcnow(),
            )
            self._message_history.append(message)
            self._observability.record_success(latency_ms=210.0)
            logger.info("[WhatsApp] Text sent | to=%s id=%s", to, msg_id)
            return message.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def send_media(
        self, to: str, media_url: str, media_type: str, caption: str = ""
    ) -> dict[str, Any]:
        """Send a media message (image/video/document) via WhatsApp Business API (mocked)."""
        try:
            msg_id = f"{self._BASE_MSG_ID}{uuid4().hex[:16]}"
            media = WhatsAppMedia(
                platform_message_id=msg_id,
                to=to,
                media_url=media_url,
                media_type=media_type,
                caption=caption,
                status=WhatsAppMessageStatus.SENT,
                sent_at=datetime.utcnow(),
            )
            self._media_history.append(media)
            self._observability.record_success(latency_ms=380.0)
            logger.info("[WhatsApp] Media sent | type=%s to=%s", media_type, to)
            return media.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def send_template(
        self, to: str, template_name: str, params: list[str]
    ) -> dict[str, Any]:
        """Send a pre-approved template message via WhatsApp Business API (mocked)."""
        try:
            msg_id = f"{self._BASE_MSG_ID}{uuid4().hex[:16]}"
            template = WhatsAppTemplate(
                platform_message_id=msg_id,
                to=to,
                template_name=template_name,
                params=params,
                status=WhatsAppMessageStatus.SENT,
                sent_at=datetime.utcnow(),
            )
            self._template_history.append(template)
            self._observability.record_success(latency_ms=260.0)
            logger.info(
                "[WhatsApp] Template sent | name=%s to=%s", template_name, to
            )
            return template.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def get_message_status(self, message_id: str) -> dict[str, Any]:
        """Get delivery status for a WhatsApp message (mocked)."""
        try:
            self._observability.record_success(latency_ms=100.0)
            return {
                "message_id": message_id,
                "status": "delivered",
                "timestamp": datetime.utcnow().isoformat(),
                "recipient_id": "mock_recipient",
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> WhatsAppConnectorReport:
        return WhatsAppConnectorReport(
            messages_sent=len(self._message_history),
            media_sent=len(self._media_history),
            templates_sent=len(self._template_history),
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token and self._phone_number_id)
