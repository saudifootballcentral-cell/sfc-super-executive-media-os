"""Webhook connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.webhook.models import (
    WebhookConnectorReport,
    WebhookPayload,
    WebhookResult,
)

logger = logging.getLogger("sfc.connectors.webhook")

_singleton: "WebhookService | None" = None


def get_webhook_service() -> "WebhookService":
    global _singleton
    if _singleton is None:
        _singleton = WebhookService()
    return _singleton


class WebhookService:
    """Webhook connector service. All providers mocked; inject real credentials via
    WEBHOOK_URL / WEBHOOK_SECRET env vars (per-webhook, not global)."""

    def __init__(self) -> None:
        self._default_url = os.environ.get("WEBHOOK_URL", "")
        self._default_secret = os.environ.get("WEBHOOK_SECRET", "")
        self._observability = ConnectorObservability(connector="webhook")
        self._result_history: list[WebhookResult] = []
        self._broadcast_count = 0

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def send(
        self,
        payload: dict[str, Any],
        webhook_url: str = "",
        secret: str | None = None,
    ) -> dict[str, Any]:
        """Send a payload to a single webhook endpoint (mocked)."""
        try:
            url = webhook_url or self._default_url or "https://mock.webhook.sfc/events"
            result = WebhookResult(
                webhook_url=url,
                status_code=200,
                success=True,
                response_body='{"status":"ok"}',
                latency_ms=85.0,
                sent_at=datetime.utcnow(),
            )
            self._result_history.append(result)
            self._observability.record_success(latency_ms=85.0)
            logger.info(
                "[Webhook] Sent | url=%s payload_keys=%s",
                url[:60],
                list(payload.keys()),
            )
            return result.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def broadcast(
        self,
        payload: dict[str, Any],
        webhooks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Send a payload to multiple webhook endpoints in sequence (mocked)."""
        results: list[dict[str, Any]] = []
        self._broadcast_count += 1
        for hook in webhooks:
            url = hook.get("url", "")
            secret = hook.get("secret")
            result = await self.send(payload, webhook_url=url, secret=secret)
            results.append(result)
        logger.info(
            "[Webhook] Broadcast complete | endpoints=%d", len(webhooks)
        )
        return results

    async def verify_signature(
        self,
        payload_bytes: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """Verify a webhook HMAC-SHA256 signature (real implementation)."""
        try:
            expected = hmac.new(
                secret.encode("utf-8"),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()
            # Support both bare hex and "sha256=<hex>" formats
            sig_value = signature.removeprefix("sha256=")
            return hmac.compare_digest(expected, sig_value)
        except Exception as exc:
            logger.warning("[Webhook] Signature verification error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> WebhookConnectorReport:
        success_count = sum(1 for r in self._result_history if r.success)
        failure_count = sum(1 for r in self._result_history if not r.success)
        return WebhookConnectorReport(
            webhooks_sent=len(self._result_history),
            broadcasts_sent=self._broadcast_count,
            total_endpoints=len(self._result_history),
            success_count=success_count,
            failure_count=failure_count,
            api_errors=self._observability.api_errors,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        # Webhooks don't require credentials; URL is sufficient
        return True
