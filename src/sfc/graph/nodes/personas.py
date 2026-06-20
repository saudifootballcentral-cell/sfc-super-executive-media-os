"""LangGraph node functions for Persona Infrastructure Layer.

These are standalone async node functions — NOT wired into the main graph.
Each instantiates the relevant service and calls 1-2 of its methods.
"""
from __future__ import annotations


async def persona_registry_node(state: dict) -> dict:
    """Registry node: list all active personas."""
    from sfc.personas.registry.service import PersonaRegistry

    registry = PersonaRegistry()
    return {
        "persona_registry_status": registry.health_check(),
        "active_personas": [
            p.persona_id for p in registry.list_all() if p.status.value == "active"
        ],
    }


async def persona_activation_node(state: dict) -> dict:
    """Activation node: plan and activate personas for a given trigger."""
    from sfc.personas.registry.service import PersonaRegistry
    from sfc.personas.activation.service import PersonaActivationEngine
    from sfc.personas.activation.models import ActivationTrigger

    registry = PersonaRegistry()
    engine = PersonaActivationEngine(registry)
    task_type = state.get("task_type", "content_request")
    trigger_map = {
        "match_report": ActivationTrigger.MATCH_DAY,
        "transfer_news": ActivationTrigger.TRANSFER_WINDOW,
        "breaking_news": ActivationTrigger.BREAKING_NEWS,
        "campaign": ActivationTrigger.CAMPAIGN_REQUEST,
    }
    trigger = trigger_map.get(task_type, ActivationTrigger.CONTENT_REQUEST)
    plan = await engine.plan(trigger, context=state.get("task_payload", {}))
    decision = await engine.activate(plan)
    return {
        "persona_activation": {
            "plan_id": plan.plan_id,
            "activated": bool(decision.activated_personas),
        }
    }


async def persona_routing_node(state: dict) -> dict:
    """Routing node: classify intent and route to primary persona."""
    from sfc.personas.registry.service import PersonaRegistry
    from sfc.personas.routing.service import PersonaRoutingEngine
    from sfc.personas.shared.types import PersonaStatus

    registry = PersonaRegistry()
    engine = PersonaRoutingEngine(registry)
    task_type = state.get("task_type", "content_creation")
    intent = await engine.classify_intent(task_type)
    available = [p for p in registry.list_all() if p.status == PersonaStatus.ACTIVE]
    decision = await engine.route(intent, available)
    return {
        "persona_routing": {
            "intent": intent.value,
            "primary_persona_id": decision.primary_persona_id,
            "confidence": decision.confidence,
        }
    }


async def persona_memory_node(state: dict) -> dict:
    """Memory node: save context snapshot and assemble context package."""
    from sfc.personas.memory.service import PersonaMemoryLayer
    from sfc.personas.memory.models import MemoryNamespace

    memory = PersonaMemoryLayer()
    persona_id = state.get("persona_id", "PERSONA-JOURNALIST-01")
    task_type = state.get("task_type", "general")
    await memory.save_snapshot(
        persona_id=persona_id,
        namespace=MemoryNamespace.WORKING,
        content={"state": state},
    )
    context = await memory.assemble_context(persona_id=persona_id, task_type=task_type)
    return {
        "persona_memory": {
            "package_id": context.package_id,
            "snapshot_count": len(context.snapshots),
        }
    }


async def persona_evaluation_node(state: dict) -> dict:
    """Evaluation node: batch evaluate all seed personas."""
    from sfc.personas.registry.service import PersonaRegistry
    from sfc.personas.evaluation.service import PersonaEvaluationFramework

    registry = PersonaRegistry()
    evaluator = PersonaEvaluationFramework()
    all_personas = registry.list_all()
    report = await evaluator.batch_evaluate(all_personas)
    return {
        "persona_evaluation": {
            "report_id": report.report_id,
            "evaluated_count": len(report.scorecards),
            "top_performer_id": report.top_performer_id,
        }
    }


async def persona_lifecycle_node(state: dict) -> dict:
    """Lifecycle node: generate lifecycle report."""
    from sfc.personas.registry.service import PersonaRegistry
    from sfc.personas.lifecycle.service import PersonaLifecycleManager

    registry = PersonaRegistry()
    manager = PersonaLifecycleManager(registry)
    report = await manager.report(period="session")
    return {
        "persona_lifecycle": {
            "report_id": report.report_id,
            "active_count": report.active_count,
            "transition_count": len(report.transitions),
        }
    }


async def persona_governance_node(state: dict) -> dict:
    """Governance node: review and approve the primary persona."""
    from sfc.personas.registry.service import PersonaRegistry
    from sfc.personas.governance.service import PersonaGovernanceFramework

    registry = PersonaRegistry()
    governance = PersonaGovernanceFramework()
    persona_id = state.get("persona_id", "PERSONA-GOVERNANCE-01")
    persona = registry.get(persona_id)
    if persona is None:
        return {"persona_governance": {"error": f"Persona {persona_id} not found"}}
    report = await governance.review(persona)
    return {
        "persona_governance": {
            "report_id": report.report_id,
            "overall_passed": report.overall_passed,
            "risk_score": report.risk_score,
        }
    }


async def persona_collaboration_node(state: dict) -> dict:
    """Collaboration node: form team and build consensus."""
    from sfc.personas.registry.service import PersonaRegistry
    from sfc.personas.collaboration.service import PersonaCollaborationEngine

    registry = PersonaRegistry()
    engine = PersonaCollaborationEngine(registry)
    task_type = state.get("task_type", "content_creation")
    capabilities = state.get("required_capabilities", ["match_reporting"])
    team = await engine.form_team(task_type=task_type, required_capabilities=capabilities)
    plan = await engine.create_plan(team)
    consensus = await engine.build_consensus(plan)
    return {
        "persona_collaboration": {
            "team_id": team.team_id,
            "plan_id": plan.plan_id,
            "confidence": consensus.confidence,
        }
    }


async def persona_recommendation_node(state: dict) -> dict:
    """Recommendation node: recommend best personas for the task."""
    from sfc.personas.registry.service import PersonaRegistry
    from sfc.personas.recommendation.service import PersonaRecommendationEngine
    from sfc.personas.recommendation.models import RecommendationRequest

    registry = PersonaRegistry()
    engine = PersonaRecommendationEngine(registry)
    request = RecommendationRequest(
        task_type=state.get("task_type", "content_creation"),
        war_room_type=state.get("war_room_type", ""),
    )
    recommendation = await engine.recommend(request)
    return {
        "persona_recommendation": {
            "recommendation_id": recommendation.recommendation_id,
            "recommended_team": recommendation.recommended_team,
            "confidence_score": recommendation.confidence_score,
        }
    }


async def persona_analytics_node(state: dict) -> dict:
    """Analytics node: build performance dashboard."""
    from sfc.personas.registry.service import PersonaRegistry
    from sfc.personas.analytics.service import PersonaPerformanceAnalytics
    from sfc.personas.analytics.models import AnalyticsPeriod

    registry = PersonaRegistry()
    analytics = PersonaPerformanceAnalytics(registry)
    report = await analytics.generate_report(period=AnalyticsPeriod.SESSION)
    return {"persona_analytics": report}
