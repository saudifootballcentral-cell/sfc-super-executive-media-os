"""Social War Room Node — evaluates and activates crisis response protocols."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.social_war_room_node")


async def social_war_room_node(state: SFCState) -> dict[str, Any]:
    """Node: social_war_room_node

    Evaluates social signals for war room triggers.
    Activates P1/P2/P3 war rooms for narrative spikes, sentiment crises,
    transfer explosions, breaking stories, and media attacks.
    All activated war rooms route through governance before any publishing action.
    """
    sentiment_data = state.get("fan_sentiment_data", {})
    trend_data = state.get("trend_radar_data", {})
    task_payload = state.get("task_payload", {})

    logger.info("[SocialWarRoomNode] Evaluating war room triggers")

    try:
        from sfc.social.war_room.service import get_war_room_service
        from sfc.social.war_room.models import SocialWarRoomTrigger

        service = get_war_room_service()

        alerts = sentiment_data.get("alerts", [])
        breaking_trends = trend_data.get("breaking_trends", [])
        top_score = trend_data.get("top_score", 0)

        trigger_context = {
            "sentiment_alerts": alerts,
            "breaking_trend_count": len(breaking_trends),
            "top_trend_score": top_score,
            "task_payload": task_payload,
        }

        activated_rooms: list[dict[str, Any]] = []

        if alerts:
            sentiment_score = sentiment_data.get("overall_score", 0)
            should_activate = await service.evaluate(
                SocialWarRoomTrigger.SENTIMENT_CRISIS,
                context={"sentiment_score": sentiment_score},
            )
            if should_activate:
                state_obj = await service.activate(
                    SocialWarRoomTrigger.SENTIMENT_CRISIS,
                    context={"alerts": alerts, "score": sentiment_score},
                )
                report = await service.generate_report(state_obj)
                activated_rooms.append(report.to_dict())
                logger.warning(
                    "[SocialWarRoomNode] SENTIMENT_CRISIS war room activated | priority=%s",
                    state_obj.priority.value,
                )

        if breaking_trends and top_score > 80:
            top_topic = trend_data.get("top_topic", "")
            should_activate = await service.evaluate(
                SocialWarRoomTrigger.NARRATIVE_SPIKE,
                context={"velocity": 8.5},
            )
            if should_activate:
                state_obj = await service.activate(
                    SocialWarRoomTrigger.NARRATIVE_SPIKE,
                    context={"topic": top_topic, "score": top_score},
                )
                report = await service.generate_report(state_obj)
                activated_rooms.append(report.to_dict())
                logger.warning(
                    "[SocialWarRoomNode] NARRATIVE_SPIKE war room activated | topic=%s",
                    top_topic,
                )

        explicit_trigger = task_payload.get("war_room_trigger")
        if explicit_trigger:
            try:
                trigger = SocialWarRoomTrigger(explicit_trigger)
                state_obj = await service.activate(trigger, context=task_payload)
                report = await service.generate_report(state_obj)
                activated_rooms.append(report.to_dict())
                logger.warning(
                    "[SocialWarRoomNode] %s war room activated (explicit) | priority=%s",
                    trigger.value,
                    state_obj.priority.value,
                )
            except ValueError:
                logger.warning("[SocialWarRoomNode] Unknown trigger: %s", explicit_trigger)

        war_room_summary = {
            "activated_count": len(activated_rooms),
            "active_rooms": service.get_active_rooms(),
            "rooms": activated_rooms,
        }

        logger.info(
            "[SocialWarRoomNode] Evaluation complete | activated=%d",
            len(activated_rooms),
        )

        return {
            "social_war_room_state": war_room_summary,
            "pipeline_stage": "social_war_room_complete",
        }

    except Exception as exc:
        logger.error("[SocialWarRoomNode] Failed (non-fatal): %s", exc)
        return {
            "social_war_room_state": {"error": str(exc), "activated_count": 0},
            "pipeline_stage": "social_war_room_skipped",
            "warnings": [f"SOCIAL_WAR_ROOM_NODE_NON_FATAL: {exc}"],
        }
