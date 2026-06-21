"""Persona Layer Node — policy-driven persona selection and execution.

Sits between editorial and creative in the main pipeline.

Selection policy (via PersonaRecommendationEngine):
  task_type contains "match"    → prefers TacticalPersona, NationalTeamPersona
  task_type contains "transfer" → prefers TransferPersona, JournalistIntelligencePersona, FanSentimentPersona
  platform contains "tiktok"    → prefers TikTokPersona, ShortsPersona
  platform contains "youtube"   → prefers YouTubePersona, ThumbnailPersona, SEOPersona
  task_type contains "crisis"   → prefers GovernancePersona + executes ExecutiveAlertSystem

Governance preservation:
  - Persona outputs are stored in persona_outputs (metadata).
  - content_drafts are enriched with persona_insights key ONLY.
  - confidence_score, source_count, brand_alignment_score are NEVER modified.
  - All content still passes through governance_node unchanged.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.persona_layer")

# Persona ID → (module_path, class_name) for instantiation
_PERSONA_CLASSES: dict[str, tuple[str, str]] = {
    # Sports personas
    "SPORT-NATL-TEAM-01": ("sfc.personas.sports.national_team.service", "NationalTeamPersona"),
    "SPORT-SPL-01": ("sfc.personas.sports.spl.service", "SPLPersona"),
    "SPORT-WC-01": ("sfc.personas.sports.world_cup.service", "WorldCupPersona"),
    "SPORT-AFC-01": ("sfc.personas.sports.afc.service", "AFCPersona"),
    "SPORT-FIFA-01": ("sfc.personas.sports.fifa.service", "FIFAPersona"),
    "SPORT-TRANSFER-01": ("sfc.personas.sports.transfer.service", "TransferPersona"),
    "SPORT-TACTICAL-01": ("sfc.personas.sports.tactical.service", "TacticalPersona"),
    "SPORT-OPP-ANALYSIS-01": ("sfc.personas.sports.opponent_analysis.service", "OpponentAnalysisPersona"),
    "SPORT-FAN-SENT-01": ("sfc.personas.sports.fan_sentiment.service", "FanSentimentPersona"),
    "SPORT-JOURNALIST-INT-01": ("sfc.personas.sports.journalist_intelligence.service", "JournalistIntelligencePersona"),
    "SPORT-INJURY-INT-01": ("sfc.personas.sports.injury_intelligence.service", "InjuryIntelligencePersona"),
    "SPORT-PERF-SCI-01": ("sfc.personas.sports.performance_science.service", "PerformanceSciencePersona"),
    "SPORT-REF-ANALYSIS-01": ("sfc.personas.sports.referee_analysis.service", "RefereeAnalysisPersona"),
    # Media personas
    "MEDIA-TIKTOK-01": ("sfc.personas.media.tiktok.service", "TikTokPersona"),
    "MEDIA-INSTAGRAM-01": ("sfc.personas.media.instagram.service", "InstagramPersona"),
    "MEDIA-YOUTUBE-01": ("sfc.personas.media.youtube.service", "YouTubePersona"),
    "MEDIA-X-01": ("sfc.personas.media.x.service", "XPersona"),
    "MEDIA-SHORTS-01": ("sfc.personas.media.shorts.service", "ShortsPersona"),
    "MEDIA-DOC-01": ("sfc.personas.media.documentary.service", "DocumentaryPersona"),
    "MEDIA-THUMB-01": ("sfc.personas.media.thumbnail.service", "ThumbnailPersona"),
    "MEDIA-POSTER-01": ("sfc.personas.media.poster.service", "PosterPersona"),
    "MEDIA-GRAPHICS-01": ("sfc.personas.media.graphics.service", "GraphicsPersona"),
    "MEDIA-PODCAST-HOST-01": ("sfc.personas.media.podcast_host.service", "PodcastHostPersona"),
    "MEDIA-PODCAST-PROD-01": ("sfc.personas.media.podcast_producer.service", "PodcastProducerPersona"),
    "MEDIA-SEO-01": ("sfc.personas.media.seo.service", "SEOPersona"),
    "MEDIA-NEWSLETTER-01": ("sfc.personas.media.newsletter.service", "NewsletterPersona"),
    "MEDIA-WHATSAPP-01": ("sfc.personas.media.whatsapp.service", "WhatsAppPersona"),
    "MEDIA-TELEGRAM-01": ("sfc.personas.media.telegram.service", "TelegramPersona"),
}


def _instantiate_persona(persona_id: str) -> Any | None:
    """Dynamically instantiate a persona by ID. Returns None on failure."""
    entry = _PERSONA_CLASSES.get(persona_id)
    if entry is None:
        return None
    module_path, class_name = entry
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls()
    except Exception as exc:
        logger.warning("[PersonaLayer] Could not instantiate %s: %s", persona_id, exc)
        return None


def _build_analysis_context(state: SFCState) -> dict[str, Any]:
    """Extract relevant context from state for persona.analyze() calls."""
    intel = state.get("intelligence_report", {})
    payload = state.get("task_payload", {})
    plan = state.get("execution_plan", {})
    return {
        "run_id": state.get("run_id", ""),
        "task_type": state.get("task_type", ""),
        "topic": payload.get("topic", payload.get("headline", "")),
        "team": payload.get("team", payload.get("home_team", "")),
        "formation": payload.get("formation", "4-3-3"),
        "platforms": plan.get("platforms_targeted", []),
        "confidence_score": intel.get("confidence_score", 0),
        "key_facts": intel.get("key_facts", []),
        "war_room_type": state.get("war_room_state", {}).get("war_room_type", ""),
    }


async def persona_layer_node(state: SFCState) -> dict[str, Any]:
    """Node: persona_layer

    Selects and executes optimal personas for the current task via the
    PolicyDriven PersonaRecommendationEngine. Enriches content_drafts
    with persona insights without modifying governance-gated score fields.
    """
    task_type = state.get("task_type", "")
    war_room_state = state.get("war_room_state", {})
    war_room_type = war_room_state.get("war_room_type", "")

    logger.info("[PersonaLayer] Selecting personas | task=%s war_room=%s", task_type, war_room_type)

    try:
        from sfc.personas.registry.service import PersonaRegistry
        from sfc.personas.recommendation.service import PersonaRecommendationEngine
        from sfc.personas.recommendation.models import RecommendationRequest
        from sfc.personas.sports import register_sports_personas
        from sfc.personas.media import register_media_personas

        # Build a fully populated registry for this run
        registry = PersonaRegistry()
        register_sports_personas(registry)
        register_media_personas(registry)

        # Policy-driven recommendation
        request = RecommendationRequest(
            task_type=task_type,
            war_room_type=war_room_type or "",
            platform=_detect_primary_platform(state),
        )
        engine = PersonaRecommendationEngine(registry)
        recommendation = await engine.recommend(request)
        recommended_ids = recommendation.recommended_team

        logger.info(
            "[PersonaLayer] Recommended %d personas: %s",
            len(recommended_ids),
            recommended_ids,
        )

        # Execute each recommended persona
        analysis_context = _build_analysis_context(state)
        persona_outputs: list[dict[str, Any]] = []
        active_personas: list[str] = []

        for persona_id in recommended_ids:
            persona = _instantiate_persona(persona_id)
            if persona is None:
                logger.warning("[PersonaLayer] Persona %s not found in class map — skipping", persona_id)
                continue
            try:
                output = await persona.analyze(analysis_context)
                persona_outputs.append({
                    "persona_id": persona_id,
                    "persona_name": getattr(persona, "PERSONA_NAME", persona_id),
                    "output": output,
                    "task_type": task_type,
                })
                active_personas.append(persona_id)
                logger.info("[PersonaLayer] %s analysis complete", persona_id)
            except Exception as exc:
                logger.warning("[PersonaLayer] %s.analyze() failed (non-fatal): %s", persona_id, exc)

        # Enrich content_drafts with persona insights
        # IMPORTANT: Only adds persona_insights metadata. Never modifies score fields.
        content_drafts = state.get("content_drafts", [])
        enriched_drafts = []
        for draft in content_drafts:
            enriched = {
                **draft,
                "persona_insights": persona_outputs,
                "recommended_personas": active_personas,
            }
            enriched_drafts.append(enriched)

        logger.info(
            "[PersonaLayer] %d personas activated | %d drafts enriched",
            len(active_personas),
            len(enriched_drafts),
        )

        return {
            "active_personas": active_personas,
            "persona_outputs": persona_outputs,
            "content_drafts": enriched_drafts if enriched_drafts else content_drafts,
            "pipeline_stage": "persona_layer_complete",
        }

    except Exception as exc:
        logger.error("[PersonaLayer] Failed (non-fatal): %s", exc, exc_info=True)
        return {
            "active_personas": [],
            "persona_outputs": [],
            "pipeline_stage": "persona_layer_skipped",
            "warnings": [f"PERSONA_LAYER_NON_FATAL: {exc}"],
        }


def _detect_primary_platform(state: SFCState) -> str:
    """Detect the primary platform from execution_plan or task_payload."""
    plan = state.get("execution_plan", {})
    platforms = plan.get("platforms_targeted", [])
    if not platforms:
        payload = state.get("task_payload", {})
        platforms = payload.get("platforms", [])
    if platforms:
        return str(platforms[0])
    return ""
