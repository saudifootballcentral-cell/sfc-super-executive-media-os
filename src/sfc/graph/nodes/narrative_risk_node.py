"""LangGraph node — Narrative Risk."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.narrative_risk")


async def narrative_risk_node(state: dict[str, Any]) -> dict[str, Any]:
    """Assess reputational and operational risk for active narratives."""
    try:
        from sfc.narrative.modeling.service import get_narrative_modeling_service
        from sfc.narrative.risk.service import get_risk_engine
        risk_engine = get_risk_engine()
        modeling = get_narrative_modeling_service()

        narrative_map = state.get("narrative_models", {})
        profiles_data = narrative_map.get("profiles", [])

        risk_reports = []
        if profiles_data:
            all_profiles = modeling.get_profiles_by_type()
            for profile in all_profiles[:3]:
                report = await risk_engine.assess_risk(profile)
                risk_reports.append(report.to_dict())
        else:
            from sfc.narrative.modeling.models import NarrativeProfile, NarrativeType, NarrativeInfluenceModel
            placeholder = NarrativeProfile(
                title="Default Narrative",
                narrative_type=NarrativeType.CLUB,
                description="Placeholder",
                strength_score=50.0,
                momentum_score=40.0,
                sentiment_score=60.0,
                credibility_score=70.0,
                virality_potential=30.0,
                influence_model=NarrativeInfluenceModel(
                    primary_drivers=[],
                    amplifiers=[],
                    suppressors=[],
                    platform_weights={},
                    influencer_impact=0.5,
                    media_impact=0.5,
                    organic_impact=0.5,
                ),
            )
            report = await risk_engine.assess_risk(placeholder)
            risk_reports.append(report.to_dict())

        return {
            "narrative_risk": {"reports": risk_reports, "total": len(risk_reports)},
            "pipeline_stage": "narrative_risk",
        }
    except Exception as exc:
        logger.warning("narrative_risk_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"narrative_risk_node: {exc}")
        return {
            "narrative_risk": {},
            "pipeline_stage": "narrative_risk",
            "warnings": warnings,
        }
