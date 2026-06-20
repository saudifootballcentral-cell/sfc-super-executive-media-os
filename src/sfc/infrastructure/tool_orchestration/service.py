"""Tool Orchestration — policy-driven tool selection without hardcoded provider choices."""

from __future__ import annotations

import logging
import os
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus

logger = logging.getLogger("sfc.infrastructure.tool_orchestration")


class ToolProvider(BaseModel):
    """A registered tool provider."""

    provider_id: str
    name: str
    capabilities: list[str]
    cost_tier: str  # "free", "low", "medium", "high"
    avg_latency_ms: float
    quality_score: float  # 0-100
    available: bool = True
    api_key_env: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SelectionPolicy(BaseModel):
    """A tool selection policy."""

    policy_id: str
    name: str
    optimize_for: str  # "cost", "quality", "speed", "balanced"
    max_cost_per_call: float = 1.0
    preferred_providers: list[str] = Field(default_factory=list)
    fallback_providers: list[str] = Field(default_factory=list)


# Cost tier ordering (ascending cost)
_COST_ORDER = {"free": 0, "low": 1, "medium": 2, "high": 3}

# Default providers
_DEFAULT_PROVIDERS: list[dict[str, Any]] = [
    # LLM providers
    {
        "provider_id": "claude_opus",
        "name": "Claude Opus",
        "capabilities": ["llm", "reasoning", "content_creation", "analysis"],
        "cost_tier": "high",
        "avg_latency_ms": 3000.0,
        "quality_score": 95.0,
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    {
        "provider_id": "claude_sonnet",
        "name": "Claude Sonnet",
        "capabilities": ["llm", "reasoning", "content_creation", "analysis", "translation"],
        "cost_tier": "medium",
        "avg_latency_ms": 1500.0,
        "quality_score": 88.0,
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    {
        "provider_id": "claude_haiku",
        "name": "Claude Haiku",
        "capabilities": ["llm", "content_creation", "translation", "summarization"],
        "cost_tier": "low",
        "avg_latency_ms": 500.0,
        "quality_score": 75.0,
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    {
        "provider_id": "openai_gpt4o",
        "name": "OpenAI GPT-4o",
        "capabilities": ["llm", "reasoning", "content_creation", "vision"],
        "cost_tier": "high",
        "avg_latency_ms": 2500.0,
        "quality_score": 92.0,
        "api_key_env": "OPENAI_API_KEY",
    },
    {
        "provider_id": "gemini_pro",
        "name": "Google Gemini Pro",
        "capabilities": ["llm", "reasoning", "content_creation", "analysis"],
        "cost_tier": "medium",
        "avg_latency_ms": 1800.0,
        "quality_score": 85.0,
        "api_key_env": "GOOGLE_API_KEY",
    },
    # Video providers
    {
        "provider_id": "veo",
        "name": "Google Veo",
        "capabilities": ["video_generation", "video"],
        "cost_tier": "high",
        "avg_latency_ms": 60000.0,
        "quality_score": 95.0,
        "api_key_env": "GOOGLE_VEO_API_KEY",
    },
    {
        "provider_id": "kling",
        "name": "Kling AI",
        "capabilities": ["video_generation", "video"],
        "cost_tier": "medium",
        "avg_latency_ms": 45000.0,
        "quality_score": 85.0,
        "api_key_env": "KLING_API_KEY",
    },
    {
        "provider_id": "runway",
        "name": "Runway ML",
        "capabilities": ["video_generation", "video", "image_to_video"],
        "cost_tier": "medium",
        "avg_latency_ms": 40000.0,
        "quality_score": 82.0,
        "api_key_env": "RUNWAY_API_KEY",
    },
    # Audio providers
    {
        "provider_id": "elevenlabs",
        "name": "ElevenLabs",
        "capabilities": ["audio_generation", "tts", "voice_cloning"],
        "cost_tier": "medium",
        "avg_latency_ms": 3000.0,
        "quality_score": 90.0,
        "api_key_env": "ELEVENLABS_API_KEY",
    },
    # Image providers
    {
        "provider_id": "flux",
        "name": "Flux AI",
        "capabilities": ["image_generation", "image"],
        "cost_tier": "low",
        "avg_latency_ms": 5000.0,
        "quality_score": 88.0,
        "api_key_env": "FAL_API_KEY",
    },
    {
        "provider_id": "ideogram",
        "name": "Ideogram AI",
        "capabilities": ["image_generation", "image", "text_in_image"],
        "cost_tier": "low",
        "avg_latency_ms": 4000.0,
        "quality_score": 85.0,
        "api_key_env": "IDEOGRAM_API_KEY",
    },
    # Publishing
    {
        "provider_id": "internal_publisher",
        "name": "Internal Publisher",
        "capabilities": ["publishing", "distribution", "scheduling"],
        "cost_tier": "free",
        "avg_latency_ms": 200.0,
        "quality_score": 90.0,
        "api_key_env": None,
    },
]

# Default policies
_DEFAULT_POLICIES: list[dict[str, Any]] = [
    {
        "policy_id": "quality",
        "name": "Quality-First",
        "optimize_for": "quality",
        "max_cost_per_call": 5.0,
        "preferred_providers": ["claude_opus", "veo", "elevenlabs", "openai_gpt4o"],
        "fallback_providers": ["claude_sonnet", "kling", "gemini_pro"],
    },
    {
        "policy_id": "cost",
        "name": "Cost-Optimized",
        "optimize_for": "cost",
        "max_cost_per_call": 0.10,
        "preferred_providers": ["claude_haiku", "flux", "internal_publisher"],
        "fallback_providers": ["claude_sonnet", "ideogram"],
    },
    {
        "policy_id": "speed",
        "name": "Speed-Optimized",
        "optimize_for": "speed",
        "max_cost_per_call": 1.0,
        "preferred_providers": ["claude_haiku", "flux", "internal_publisher"],
        "fallback_providers": ["claude_sonnet", "ideogram"],
    },
    {
        "policy_id": "balanced",
        "name": "Balanced",
        "optimize_for": "balanced",
        "max_cost_per_call": 1.0,
        "preferred_providers": ["claude_sonnet", "kling", "elevenlabs", "flux"],
        "fallback_providers": ["claude_haiku", "runway", "ideogram", "internal_publisher"],
    },
]


class ToolOrchestrationService:
    """Policy-driven tool selection — never hardcodes a provider."""

    def __init__(self) -> None:
        self._providers: dict[str, ToolProvider] = {}
        self._policies: dict[str, SelectionPolicy] = {}
        self._active_policy: str = "balanced"
        self._call_log: list[dict[str, Any]] = []
        self._provider_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total_calls": 0,
                "success_calls": 0,
                "total_cost_usd": 0.0,
                "total_latency_ms": 0.0,
            }
        )
        self._lock = threading.RLock()
        self._register_providers()
        self._register_policies()

    def _register_providers(self) -> None:
        """Register all default providers."""
        for p_data in _DEFAULT_PROVIDERS:
            provider = ToolProvider(**p_data)
            # Check API key availability to determine if truly available
            if provider.api_key_env and not os.environ.get(provider.api_key_env):
                # No key — mark as available=False but keep registered for fallback tracking
                provider = provider.model_copy(update={"available": False})
            self._providers[provider.provider_id] = provider

        # Internal publisher is always available (no key needed)
        if "internal_publisher" in self._providers:
            self._providers["internal_publisher"] = self._providers[
                "internal_publisher"
            ].model_copy(update={"available": True})

    def _register_policies(self) -> None:
        """Register all default policies."""
        for p_data in _DEFAULT_POLICIES:
            policy = SelectionPolicy(**p_data)
            self._policies[policy.policy_id] = policy

    def _score_provider(
        self,
        provider: ToolProvider,
        policy: SelectionPolicy,
    ) -> float:
        """Score a provider according to the policy's optimization target."""
        optimize_for = policy.optimize_for

        if optimize_for == "quality":
            return provider.quality_score

        if optimize_for == "cost":
            # Lower cost = higher score
            cost_rank = _COST_ORDER.get(provider.cost_tier, 3)
            return 100.0 - (cost_rank * 25.0)

        if optimize_for == "speed":
            # Lower latency = higher score (normalize to 0-100)
            latency = provider.avg_latency_ms
            return max(0.0, 100.0 - (latency / 1000.0))

        # "balanced" — weighted combination
        quality_score = provider.quality_score
        cost_score = 100.0 - (_COST_ORDER.get(provider.cost_tier, 3) * 25.0)
        speed_score = max(0.0, 100.0 - (provider.avg_latency_ms / 1000.0))
        return quality_score * 0.40 + cost_score * 0.30 + speed_score * 0.30

    def select_tool(
        self,
        capability: str,
        policy: str | None = None,
    ) -> ToolProvider | None:
        """Select optimal provider for capability per policy."""
        policy_id = policy or self._active_policy
        selected_policy = self._policies.get(policy_id) or self._policies.get("balanced")
        if not selected_policy:
            return None

        candidates = self.select_with_fallback(capability, policy_id)
        return candidates[0] if candidates else None

    def select_with_fallback(
        self,
        capability: str,
        policy: str | None = None,
    ) -> list[ToolProvider]:
        """Return ordered list: primary + fallbacks for capability."""
        policy_id = policy or self._active_policy
        selected_policy = self._policies.get(policy_id) or self._policies.get("balanced")

        if not selected_policy:
            return []

        # Filter providers by capability
        with self._lock:
            all_providers = list(self._providers.values())

        capable = [
            p for p in all_providers
            if capability in p.capabilities or any(
                cap in capability for cap in p.capabilities
            )
        ]

        # Filter by policy preferred + fallback + any available
        preferred_ids = set(selected_policy.preferred_providers)
        fallback_ids = set(selected_policy.fallback_providers)

        # Only include available ones
        available = [p for p in capable if p.available]

        if not available:
            # No API keys but return candidates anyway (graceful degradation)
            available = capable

        # Sort: preferred first, then fallback, then others — all scored within group
        preferred = [p for p in available if p.provider_id in preferred_ids]
        fallback = [p for p in available if p.provider_id in fallback_ids and p not in preferred]
        others = [p for p in available if p not in preferred and p not in fallback]

        def sort_by_score(providers: list[ToolProvider]) -> list[ToolProvider]:
            return sorted(
                providers,
                key=lambda p: self._score_provider(p, selected_policy),
                reverse=True,
            )

        ordered = sort_by_score(preferred) + sort_by_score(fallback) + sort_by_score(others)
        return ordered

    def record_outcome(
        self,
        provider_id: str,
        success: bool,
        latency_ms: float,
        cost_usd: float,
    ) -> None:
        """Update provider stats based on outcome."""
        record = {
            "provider_id": provider_id,
            "success": success,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "timestamp": datetime.utcnow().isoformat(),
        }
        with self._lock:
            self._call_log.append(record)
            stats = self._provider_stats[provider_id]
            stats["total_calls"] += 1
            if success:
                stats["success_calls"] += 1
            stats["total_cost_usd"] += cost_usd
            stats["total_latency_ms"] += latency_ms

            # Update avg latency in provider record
            provider = self._providers.get(provider_id)
            if provider and stats["total_calls"] > 0:
                new_avg = stats["total_latency_ms"] / stats["total_calls"]
                self._providers[provider_id] = provider.model_copy(
                    update={"avg_latency_ms": new_avg}
                )

    def get_utilization_report(self) -> dict[str, Any]:
        """Provider utilization, success rates, costs."""
        with self._lock:
            stats = dict(self._provider_stats)
            total_calls = len(self._call_log)

        report: dict[str, Any] = {
            "total_calls": total_calls,
            "by_provider": {},
        }

        for provider_id, s in stats.items():
            total = s["total_calls"]
            success_rate = s["success_calls"] / total if total > 0 else 1.0
            avg_lat = s["total_latency_ms"] / total if total > 0 else 0.0
            report["by_provider"][provider_id] = {
                "total_calls": total,
                "success_rate": round(success_rate, 3),
                "total_cost_usd": round(s["total_cost_usd"], 4),
                "avg_latency_ms": round(avg_lat, 1),
            }

        return report

    def get_cost_optimization_report(self) -> list[str]:
        """Ranked recommendations to reduce cost."""
        recommendations: list[str] = []
        with self._lock:
            stats = dict(self._provider_stats)
            providers = dict(self._providers)

        for provider_id, s in stats.items():
            total = s["total_calls"]
            if total == 0:
                continue
            avg_cost = s["total_cost_usd"] / total
            provider = providers.get(provider_id)
            if not provider:
                continue

            # Check if a cheaper provider with quality delta < 10 exists
            if provider.cost_tier in ("high", "medium"):
                cheaper = [
                    p for p in providers.values()
                    if p.cost_tier in ("free", "low")
                    and any(cap in provider.capabilities for cap in p.capabilities)
                    and abs(p.quality_score - provider.quality_score) < 10
                ]
                if cheaper:
                    alt = cheaper[0]
                    recommendations.append(
                        f"Replace '{provider.name}' (cost_tier={provider.cost_tier}) with "
                        f"'{alt.name}' (cost_tier={alt.cost_tier}) — quality delta "
                        f"{abs(alt.quality_score - provider.quality_score):.1f} pts, "
                        f"est. savings ${avg_cost * total * 0.5:.2f}."
                    )

        if not recommendations:
            recommendations.append(
                "No significant cost optimizations identified. Current tool mix is efficient."
            )

        return recommendations

    def health_check(self) -> ComponentHealth:
        """Return health status of the tool orchestration service."""
        try:
            with self._lock:
                total = len(self._providers)
                available = sum(1 for p in self._providers.values() if p.available)

            status = HealthStatus.HEALTHY
            errors: list[str] = []

            if available == 0:
                status = HealthStatus.DEGRADED
                errors.append("No providers are currently available (no API keys configured)")
            elif available < total // 2:
                status = HealthStatus.DEGRADED
                errors.append(f"Only {available}/{total} providers available")

            return ComponentHealth(
                component="tool_orchestration",
                status=status,
                last_check=datetime.utcnow(),
                metrics={
                    "total_providers": total,
                    "available_providers": available,
                    "active_policy": self._active_policy,
                },
                errors=errors,
            )
        except Exception as exc:  # noqa: BLE001
            return ComponentHealth(
                component="tool_orchestration",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                metrics={},
                errors=[str(exc)],
            )
