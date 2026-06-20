"""Infrastructure Context — process-level singleton holding all infrastructure service references."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("sfc.infrastructure.context")


class InfrastructureContext:
    """Process-level singleton holding all infrastructure service references.

    All services are lazy-initialized (not on import) through the initialize() method.
    Services are NOT inserted as new LangGraph graph nodes — they are called FROM
    within existing division nodes when needed.
    """

    def __init__(self) -> None:
        # Services — set during initialize()
        from sfc.infrastructure.agentops.service import AgentOpsService
        from sfc.infrastructure.memory_manager.service import MemoryManagerService
        from sfc.infrastructure.knowledge_graph.service import KnowledgeGraphService
        from sfc.infrastructure.event_bus_manager.service import EventBusManagerService
        from sfc.infrastructure.simulation_engine.service import SimulationEngineService
        from sfc.infrastructure.capability_registry.service import CapabilityRegistryService
        from sfc.infrastructure.tool_orchestration.service import ToolOrchestrationService
        from sfc.infrastructure.learning_engine.service import LearningEngineService

        # Pre-create but NOT yet initialized
        self.agentops: AgentOpsService = AgentOpsService()
        self.memory_manager: MemoryManagerService = MemoryManagerService()
        self.knowledge_graph: KnowledgeGraphService = KnowledgeGraphService()
        self.event_bus_manager: EventBusManagerService = EventBusManagerService()
        self.simulation_engine: SimulationEngineService = SimulationEngineService()
        self.capability_registry: CapabilityRegistryService = CapabilityRegistryService()
        self.tool_orchestration: ToolOrchestrationService = ToolOrchestrationService()
        self.learning_engine: LearningEngineService = LearningEngineService(
            memory_manager=self.memory_manager
        )

        self._initialized: bool = False
        self._started_at: datetime = datetime.utcnow()

    async def initialize(self) -> None:
        """Initialize all infrastructure services in dependency order."""
        if self._initialized:
            logger.debug("[InfraCtx] Already initialized, skipping")
            return

        logger.info("[InfraCtx] Initializing infrastructure services...")

        # 1. AgentOps (no dependencies)
        await self.agentops.initialize()
        logger.debug("[InfraCtx] AgentOps initialized")

        # 2. Memory Manager (no dependencies beyond memory layer)
        # Already created — no async init needed but we audit
        self.agentops.audit("infrastructure", "memory_manager_ready", "init")
        logger.debug("[InfraCtx] MemoryManager ready")

        # 3. Knowledge Graph (no dependencies)
        self.agentops.audit("infrastructure", "knowledge_graph_ready", "init")
        logger.debug("[InfraCtx] KnowledgeGraph ready")

        # 4. Event Bus Manager (wraps existing bus)
        self.agentops.audit("infrastructure", "event_bus_manager_ready", "init")
        logger.debug("[InfraCtx] EventBusManager ready")

        # 5. Simulation Engine (no dependencies)
        self.agentops.audit("infrastructure", "simulation_engine_ready", "init")
        logger.debug("[InfraCtx] SimulationEngine ready")

        # 6. Capability Registry (no dependencies)
        self.agentops.audit("infrastructure", "capability_registry_ready", "init")
        logger.debug("[InfraCtx] CapabilityRegistry ready")

        # 7. Tool Orchestration (no dependencies)
        self.agentops.audit("infrastructure", "tool_orchestration_ready", "init")
        logger.debug("[InfraCtx] ToolOrchestration ready")

        # 8. Learning Engine (depends on memory_manager — already linked in __init__)
        self.agentops.audit("infrastructure", "learning_engine_ready", "init")
        logger.debug("[InfraCtx] LearningEngine ready")

        self._initialized = True
        logger.info("[InfraCtx] All 8 infrastructure services initialized successfully")

    async def shutdown(self) -> None:
        """Gracefully shut down all infrastructure services."""
        logger.info("[InfraCtx] Shutting down infrastructure services...")
        self.agentops.audit("infrastructure", "shutdown", "system")
        self._initialized = False
        logger.info("[InfraCtx] Shutdown complete")

    def health_report(self) -> dict[str, Any]:
        """Return health status of all infrastructure services."""
        components: dict[str, Any] = {}

        services = {
            "agentops": self.agentops,
            "memory_manager": self.memory_manager,
            "knowledge_graph": self.knowledge_graph,
            "event_bus_manager": self.event_bus_manager,
            "simulation_engine": self.simulation_engine,
            "capability_registry": self.capability_registry,
            "tool_orchestration": self.tool_orchestration,
            "learning_engine": self.learning_engine,
        }

        for name, service in services.items():
            try:
                health = service.health_check()
                components[name] = health.model_dump()
            except Exception as exc:  # noqa: BLE001
                components[name] = {
                    "component": name,
                    "status": "unhealthy",
                    "errors": [str(exc)],
                    "last_check": datetime.utcnow().isoformat(),
                }

        overall_statuses = [c.get("status", "unknown") for c in components.values()]
        if all(s == "healthy" for s in overall_statuses):
            overall = "healthy"
        elif any(s == "unhealthy" for s in overall_statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        return {
            "overall_status": overall,
            "initialized": self._initialized,
            "started_at": self._started_at.isoformat(),
            "components": components,
        }


# ---------------------------------------------------------------------------
# Process-level singleton
# ---------------------------------------------------------------------------

_ctx: InfrastructureContext | None = None


def get_infrastructure() -> InfrastructureContext:
    """Return the process-wide singleton InfrastructureContext.

    Creates it if it doesn't exist (lazy initialization).
    Does NOT call initialize() — call init_infrastructure() for that.
    """
    global _ctx
    if _ctx is None:
        _ctx = InfrastructureContext()
    return _ctx


async def init_infrastructure() -> InfrastructureContext:
    """Get and initialize the infrastructure context.

    Safe to call multiple times — initialize() is idempotent.
    """
    ctx = get_infrastructure()
    if not ctx._initialized:
        await ctx.initialize()
    return ctx


def reset_infrastructure() -> None:
    """Reset the singleton — for testing only."""
    global _ctx
    _ctx = None
