"""Capability Registry — catalog of all capabilities the system can perform."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus

logger = logging.getLogger("sfc.infrastructure.capability_registry")


class Capability(BaseModel):
    """A registered system capability."""

    capability_id: str
    name: str
    description: str
    category: str  # research, content, creative, publishing, analytics, revenue, governance, learning, infrastructure
    provider: str  # which service/tool provides this
    status: str = "active"  # active, degraded, unavailable
    cost_per_call_usd: float = 0.0
    avg_latency_ms: float = 0.0
    dependencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# Default capabilities to register at startup
_DEFAULT_CAPABILITIES: list[dict[str, Any]] = [
    # Research
    {
        "capability_id": "cap_research",
        "name": "research",
        "description": "Gather and aggregate information from multiple sources",
        "category": "research",
        "provider": "intelligence",
        "cost_per_call_usd": 0.02,
        "avg_latency_ms": 2000.0,
    },
    {
        "capability_id": "cap_fact_verification",
        "name": "fact_verification",
        "description": "Cross-check facts against verified sources",
        "category": "research",
        "provider": "intelligence",
        "cost_per_call_usd": 0.015,
        "avg_latency_ms": 1500.0,
    },
    {
        "capability_id": "cap_trend_detection",
        "name": "trend_detection",
        "description": "Identify trending topics in Saudi football",
        "category": "research",
        "provider": "intelligence",
        "cost_per_call_usd": 0.01,
        "avg_latency_ms": 1000.0,
    },
    {
        "capability_id": "cap_narrative_analysis",
        "name": "narrative_analysis",
        "description": "Analyze media narratives and sentiment",
        "category": "research",
        "provider": "intelligence",
        "cost_per_call_usd": 0.025,
        "avg_latency_ms": 2500.0,
    },
    # Content
    {
        "capability_id": "cap_content_creation",
        "name": "content_creation",
        "description": "Create editorial content in Arabic and English",
        "category": "content",
        "provider": "editorial",
        "cost_per_call_usd": 0.05,
        "avg_latency_ms": 3000.0,
    },
    {
        "capability_id": "cap_translation",
        "name": "translation",
        "description": "Translate content between Arabic and English",
        "category": "content",
        "provider": "editorial",
        "cost_per_call_usd": 0.02,
        "avg_latency_ms": 1000.0,
    },
    # Creative
    {
        "capability_id": "cap_video_generation",
        "name": "video_generation",
        "description": "Generate video content using AI",
        "category": "creative",
        "provider": "veo/kling",
        "cost_per_call_usd": 0.50,
        "avg_latency_ms": 30000.0,
    },
    {
        "capability_id": "cap_image_generation",
        "name": "image_generation",
        "description": "Generate images using AI",
        "category": "creative",
        "provider": "flux/ideogram",
        "cost_per_call_usd": 0.10,
        "avg_latency_ms": 5000.0,
    },
    {
        "capability_id": "cap_audio_generation",
        "name": "audio_generation",
        "description": "Generate voiceover and audio using ElevenLabs",
        "category": "creative",
        "provider": "elevenlabs",
        "cost_per_call_usd": 0.08,
        "avg_latency_ms": 4000.0,
    },
    {
        "capability_id": "cap_thumbnail_creation",
        "name": "thumbnail_creation",
        "description": "Create optimized thumbnails for platforms",
        "category": "creative",
        "provider": "creative",
        "cost_per_call_usd": 0.05,
        "avg_latency_ms": 3000.0,
    },
    {
        "capability_id": "cap_poster_creation",
        "name": "poster_creation",
        "description": "Create promotional posters and graphics",
        "category": "creative",
        "provider": "creative",
        "cost_per_call_usd": 0.07,
        "avg_latency_ms": 4000.0,
    },
    # Publishing
    {
        "capability_id": "cap_publishing",
        "name": "publishing",
        "description": "Distribute content across platforms",
        "category": "publishing",
        "provider": "publishing",
        "cost_per_call_usd": 0.005,
        "avg_latency_ms": 500.0,
    },
    # Analytics
    {
        "capability_id": "cap_analytics",
        "name": "analytics",
        "description": "Track and analyze content performance",
        "category": "analytics",
        "provider": "analytics",
        "cost_per_call_usd": 0.01,
        "avg_latency_ms": 1000.0,
    },
    # Revenue
    {
        "capability_id": "cap_revenue_analysis",
        "name": "revenue_analysis",
        "description": "Analyze revenue opportunities and performance",
        "category": "revenue",
        "provider": "revenue",
        "cost_per_call_usd": 0.02,
        "avg_latency_ms": 1500.0,
    },
    {
        "capability_id": "cap_sponsor_discovery",
        "name": "sponsor_discovery",
        "description": "Discover and match sponsorship opportunities",
        "category": "revenue",
        "provider": "revenue",
        "cost_per_call_usd": 0.03,
        "avg_latency_ms": 2000.0,
    },
    # Governance
    {
        "capability_id": "cap_governance_review",
        "name": "governance_review",
        "description": "Review content for compliance and brand safety",
        "category": "governance",
        "provider": "governance",
        "cost_per_call_usd": 0.02,
        "avg_latency_ms": 1500.0,
    },
    # Infrastructure
    {
        "capability_id": "cap_learning",
        "name": "learning",
        "description": "Extract and apply lessons from workflow outcomes",
        "category": "learning",
        "provider": "infrastructure",
        "cost_per_call_usd": 0.005,
        "avg_latency_ms": 200.0,
    },
    {
        "capability_id": "cap_forecasting",
        "name": "forecasting",
        "description": "Forecast performance and trends",
        "category": "analytics",
        "provider": "infrastructure",
        "cost_per_call_usd": 0.01,
        "avg_latency_ms": 500.0,
    },
    {
        "capability_id": "cap_simulation",
        "name": "simulation",
        "description": "Simulate scenario outcomes before execution",
        "category": "infrastructure",
        "provider": "infrastructure",
        "cost_per_call_usd": 0.002,
        "avg_latency_ms": 100.0,
    },
]


class CapabilityRegistryService:
    """Catalog of all capabilities the system can perform."""

    def __init__(self) -> None:
        self._catalog: dict[str, Capability] = {}
        self._call_counts: dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all built-in capabilities."""
        for cap_data in _DEFAULT_CAPABILITIES:
            self.register(Capability(**cap_data))

    def register(self, capability: Capability) -> None:
        """Register a capability in the catalog."""
        with self._lock:
            self._catalog[capability.capability_id] = capability
        logger.debug("[CapabilityRegistry] Registered: %s (%s)", capability.name, capability.provider)

    def get(self, capability_id: str) -> Capability | None:
        """Retrieve a capability by ID."""
        with self._lock:
            return self._catalog.get(capability_id)

    def find_by_category(self, category: str) -> list[Capability]:
        """Return all capabilities in a category."""
        with self._lock:
            return [c for c in self._catalog.values() if c.category == category]

    def find_by_provider(self, provider: str) -> list[Capability]:
        """Return all capabilities from a provider."""
        with self._lock:
            return [c for c in self._catalog.values() if c.provider == provider]

    def get_available(self) -> list[Capability]:
        """Return only active capabilities."""
        with self._lock:
            return [c for c in self._catalog.values() if c.status == "active"]

    def update_status(
        self,
        capability_id: str,
        status: str,
        avg_latency_ms: float | None = None,
    ) -> None:
        """Update the status (and optionally latency) of a capability."""
        with self._lock:
            cap = self._catalog.get(capability_id)
            if cap:
                # Pydantic model — rebuild with updated fields
                updated = cap.model_copy(
                    update={
                        "status": status,
                        **({"avg_latency_ms": avg_latency_ms} if avg_latency_ms is not None else {}),
                    }
                )
                self._catalog[capability_id] = updated
                logger.info("[CapabilityRegistry] Status update: %s → %s", capability_id, status)

    def record_use(self, capability_id: str) -> None:
        """Increment the usage count for a capability."""
        with self._lock:
            self._call_counts[capability_id] += 1

    def report(self) -> dict[str, Any]:
        """Generate a full capability report."""
        with self._lock:
            caps = list(self._catalog.values())
            counts = dict(self._call_counts)

        by_category: dict[str, int] = defaultdict(int)
        by_provider: dict[str, int] = defaultdict(int)
        unavailable: list[str] = []

        for cap in caps:
            by_category[cap.category] += 1
            by_provider[cap.provider] += 1
            if cap.status != "active":
                unavailable.append(cap.capability_id)

        top_used = sorted(
            [{"capability_id": cid, "calls": cnt} for cid, cnt in counts.items()],
            key=lambda x: x["calls"],
            reverse=True,
        )[:10]

        return {
            "total_capabilities": len(caps),
            "active_capabilities": sum(1 for c in caps if c.status == "active"),
            "by_category": dict(by_category),
            "by_provider": dict(by_provider),
            "unavailable": unavailable,
            "top_used": top_used,
            "total_calls": sum(counts.values()),
        }

    def health_check(self) -> ComponentHealth:
        """Return health of the capability registry."""
        try:
            with self._lock:
                total = len(self._catalog)
                active = sum(1 for c in self._catalog.values() if c.status == "active")
                unavailable = [
                    c.capability_id for c in self._catalog.values() if c.status == "unavailable"
                ]

            errors: list[str] = []
            status = HealthStatus.HEALTHY

            if active < total // 2:
                status = HealthStatus.DEGRADED
                errors.append(f"Only {active}/{total} capabilities are active")

            return ComponentHealth(
                component="capability_registry",
                status=status,
                last_check=datetime.utcnow(),
                metrics={
                    "total_capabilities": total,
                    "active_capabilities": active,
                    "unavailable_capabilities": len(unavailable),
                },
                errors=errors,
            )
        except Exception as exc:  # noqa: BLE001
            return ComponentHealth(
                component="capability_registry",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                metrics={},
                errors=[str(exc)],
            )
