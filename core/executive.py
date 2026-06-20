"""SFC Super Executive — the central operating system orchestrator."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from agentops.monitors import CostMonitor, HealthMonitor, QualityMonitor
from agentops.registries import AgentRegistry, CapabilityRegistry, PromptRegistry, ToolRegistry
from core.event_bus import EventBus
from core.knowledge_graph.graph import KnowledgeGraph
from core.memory.division_memory import DivisionMemoryStore
from core.memory.episodic_memory import EpisodicMemory
from core.memory.global_memory import GlobalMemory
from core.memory.persona_memory import PersonaMemoryStore
from core.memory.working_memory import WorkingMemory
from core.models import Division, EventType, SFCEvent
from divisions.analytics.division import AnalyticsDivision
from divisions.creative.division import CreativeDivision
from divisions.editorial.division import EditorialDivision
from divisions.governance.division import GovernanceDivision
from divisions.intelligence.division import IntelligenceDivision
from divisions.publishing.division import PublishingDivision
from divisions.revenue.division import RevenueDivision
from divisions.strategic_planning.division import StrategicPlanningDivision

logger = logging.getLogger("sfc.executive")


class SFCExecutive:
    """The autonomous executive operating system of SFC.

    Orchestrates all divisions, memory layers, agentops, and war rooms
    under a single authoritative executive layer.

    Authority: Final authority belongs only to SFC Super Executive.
    """

    VERSION = "1.0.0"

    def __init__(self) -> None:
        # Core infrastructure
        self.event_bus = EventBus()
        self.global_memory = GlobalMemory()
        self.division_memory = DivisionMemoryStore()
        self.persona_memory = PersonaMemoryStore()
        self.working_memory = WorkingMemory()
        self.episodic_memory = EpisodicMemory()
        self.knowledge_graph = KnowledgeGraph()

        # AgentOps
        self.agent_registry = AgentRegistry()
        self.prompt_registry = PromptRegistry()
        self.capability_registry = CapabilityRegistry()
        self.tool_registry = ToolRegistry()
        self.health_monitor = HealthMonitor()
        self.cost_monitor = CostMonitor()
        self.quality_monitor = QualityMonitor()

        # Divisions
        self.divisions: dict[Division, Any] = {}
        self._init_divisions()
        self._wire_event_handlers()

        self.started_at = datetime.utcnow()
        logger.info("SFC Super Executive v%s initialized at %s", self.VERSION, self.started_at.isoformat())

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _init_divisions(self) -> None:
        def make(div_class):
            return div_class(
                event_bus=self.event_bus,
                memory=self.division_memory.for_division(div_class.division),
                episodic=self.episodic_memory,
            )

        self.divisions = {
            Division.STRATEGIC_PLANNING: make(StrategicPlanningDivision),
            Division.INTELLIGENCE: make(IntelligenceDivision),
            Division.EDITORIAL: make(EditorialDivision),
            Division.CREATIVE: make(CreativeDivision),
            Division.PUBLISHING: make(PublishingDivision),
            Division.ANALYTICS: make(AnalyticsDivision),
            Division.REVENUE: make(RevenueDivision),
            Division.GOVERNANCE: make(GovernanceDivision),
        }

    def _wire_event_handlers(self) -> None:
        intelligence = self.get_division(IntelligenceDivision)
        editorial = self.get_division(EditorialDivision)
        creative = self.get_division(CreativeDivision)
        strategic = self.get_division(StrategicPlanningDivision)
        revenue = self.get_division(RevenueDivision)

        for event_type in [EventType.TREND_DETECTED, EventType.NEWS_DETECTED,
                           EventType.RUMOR_DETECTED, EventType.TRANSFER_RUMOR]:
            self.event_bus.subscribe(event_type, intelligence.handle_event, Division.INTELLIGENCE)

        for event_type in [EventType.NEWS_DETECTED, EventType.TRANSFER_CONFIRMED,
                           EventType.MATCH_ENDED, EventType.TREND_DETECTED]:
            self.event_bus.subscribe(event_type, editorial.handle_event, Division.EDITORIAL)

        for event_type in [EventType.CONTENT_CREATED, EventType.MATCH_STARTED]:
            self.event_bus.subscribe(event_type, creative.handle_event, Division.CREATIVE)

        for event_type in [EventType.CAMPAIGN_STARTED, EventType.CAMPAIGN_COMPLETED]:
            self.event_bus.subscribe(event_type, strategic.handle_event, Division.STRATEGIC_PLANNING)

        self.event_bus.subscribe(
            EventType.SPONSOR_OPPORTUNITY_DETECTED, revenue.handle_event, Division.REVENUE
        )

    # ------------------------------------------------------------------
    # Division access
    # ------------------------------------------------------------------

    def get_division(self, division_class):
        return self.divisions[division_class.division]

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        event_type: EventType,
        source: str,
        payload: dict[str, Any] | None = None,
        owner: Division | None = None,
    ) -> SFCEvent:
        event = self.event_bus.create_event(event_type, source, payload, owner)
        await self.event_bus.publish(event)
        return event

    # ------------------------------------------------------------------
    # Executive decision making
    # ------------------------------------------------------------------

    def evaluate_decision(
        self,
        impact: float,
        confidence: float,
        risk: float,
        cost: float,
        speed: float,
        revenue_potential: float,
        brand_impact: float,
    ) -> dict[str, Any]:
        from core.models import DecisionEvaluation
        evaluation = DecisionEvaluation(
            impact=impact,
            confidence=confidence,
            risk=risk,
            cost=cost,
            speed=speed,
            revenue_potential=revenue_potential,
            brand_impact=brand_impact,
        )
        decision = {
            "long_term_value_score": evaluation.long_term_value_score,
            "recommend": evaluation.long_term_value_score > 10.0,
            "evaluation": evaluation.model_dump(),
        }
        logger.info("[Executive] Decision evaluated — LTV Score: %.2f | Recommend: %s",
                    decision["long_term_value_score"], decision["recommend"])
        return decision

    # ------------------------------------------------------------------
    # System status
    # ------------------------------------------------------------------

    def system_status(self) -> dict[str, Any]:
        uptime_seconds = (datetime.utcnow() - self.started_at).total_seconds()
        return {
            "system": "SFC Super Executive Media OS",
            "version": self.VERSION,
            "started_at": self.started_at.isoformat(),
            "uptime_seconds": uptime_seconds,
            "divisions_active": len(self.divisions),
            "agents_registered": self.agent_registry.count,
            "events_processed": len(self.event_bus.event_log),
            "episodes_recorded": self.episodic_memory.total_count,
            "knowledge_graph": {
                "entities": self.knowledge_graph.entity_count,
                "relationships": self.knowledge_graph.relationship_count,
            },
            "cost": self.cost_monitor.report(),
            "quality": self.quality_monitor.report(),
        }

    def executive_brief(self) -> str:
        status = self.system_status()
        return (
            f"\n{'='*60}\n"
            f"SFC SUPER EXECUTIVE MEDIA OS v{self.VERSION}\n"
            f"{'='*60}\n"
            f"Uptime        : {status['uptime_seconds']:.0f}s\n"
            f"Divisions     : {status['divisions_active']}\n"
            f"Events        : {status['events_processed']}\n"
            f"Episodes      : {status['episodes_recorded']}\n"
            f"KG Entities   : {status['knowledge_graph']['entities']}\n"
            f"KG Relations  : {status['knowledge_graph']['relationships']}\n"
            f"Total Cost    : ${status['cost']['total_cost_usd']:.4f}\n"
            f"Approval Rate : {status['quality']['approval_rate']*100:.1f}%\n"
            f"{'='*60}\n"
        )
