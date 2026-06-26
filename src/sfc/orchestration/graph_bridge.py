"""GraphBridge — loads, executes, and threads state through each existing graph."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.graph.state import make_initial_state


class GraphBridgeError(Exception):
    """Raised when a graph execution fails and recovery is not possible."""


class GraphBridge:
    """Adapts each compiled LangGraph into a uniform async execute() interface.

    Responsibilities:
      - Build (or accept) compiled graphs lazily
      - Merge incoming MasterState context into a fresh SFCState
      - Execute the graph with ainvoke()
      - Write back selected output keys to caller-supplied artifacts dict
      - Publish the appropriate orchestration event on the EventBus
    """

    def __init__(self) -> None:
        self._graphs: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Graph loaders (lazy, cached)
    # ------------------------------------------------------------------

    def _get_main_graph(self) -> Any:
        if "main_graph" not in self._graphs:
            from sfc.graph.graph import build_graph
            self._graphs["main_graph"] = build_graph()
        return self._graphs["main_graph"]

    def _get_social_intelligence_graph(self) -> Any:
        if "social_intelligence_graph" not in self._graphs:
            from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
            self._graphs["social_intelligence_graph"] = build_social_intelligence_graph()
        return self._graphs["social_intelligence_graph"]

    def _get_creative_production_graph(self) -> Any:
        if "creative_production_graph" not in self._graphs:
            from sfc.graph.creative_production_graph import build_creative_production_graph
            self._graphs["creative_production_graph"] = build_creative_production_graph()
        return self._graphs["creative_production_graph"]

    def _get_publishing_connectors_graph(self) -> Any:
        if "publishing_connectors_graph" not in self._graphs:
            from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
            self._graphs["publishing_connectors_graph"] = build_publishing_connectors_graph()
        return self._graphs["publishing_connectors_graph"]

    def _get_autonomous_graph(self) -> Any:
        if "autonomous_graph" not in self._graphs:
            from sfc.graph.autonomous_graph import build_autonomous_graph
            self._graphs["autonomous_graph"] = build_autonomous_graph()
        return self._graphs["autonomous_graph"]

    # ------------------------------------------------------------------
    # Core execute method
    # ------------------------------------------------------------------

    async def execute(
        self,
        graph_name: str,
        run_id: str,
        task_type: str,
        task_payload: dict[str, Any],
        prior_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a named graph and return its final SFCState as a plain dict.

        Args:
            graph_name: One of the registered graph names.
            run_id: Propagated from MasterState for traceability.
            task_type: TaskType string passed to make_initial_state().
            task_payload: Input payload for this run.
            prior_state: Optional keys to overlay on the initial state (e.g. social
                         intelligence output fed into the main pipeline).

        Returns:
            SFCState dict as returned by graph.ainvoke().
        """
        graph = self._load_graph(graph_name)
        initial = make_initial_state(task_type=task_type, task_payload=task_payload, run_id=run_id)

        if prior_state:
            for k, v in prior_state.items():
                if k in initial and v:
                    initial[k] = v  # type: ignore[literal-required]

        started = datetime.utcnow()
        try:
            result: dict[str, Any] = await graph.ainvoke(initial)
        except Exception as exc:
            raise GraphBridgeError(f"Graph '{graph_name}' failed: {exc}") from exc

        elapsed_ms = (datetime.utcnow() - started).total_seconds() * 1000
        self._publish_completion_event(graph_name, run_id, elapsed_ms, result)
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_graph(self, name: str) -> Any:
        loaders = {
            "main_graph": self._get_main_graph,
            "social_intelligence_graph": self._get_social_intelligence_graph,
            "creative_production_graph": self._get_creative_production_graph,
            "publishing_connectors_graph": self._get_publishing_connectors_graph,
            "autonomous_graph": self._get_autonomous_graph,
        }
        loader = loaders.get(name)
        if loader is None:
            raise GraphBridgeError(f"Unknown graph: '{name}'. Valid: {list(loaders)}")
        return loader()

    def _publish_completion_event(
        self,
        graph_name: str,
        run_id: str,
        elapsed_ms: float,
        result: dict[str, Any],
    ) -> None:
        from sfc.events.types import (
            ConnectorRunCompleted,
            CreativeProductionRunCompleted,
            NarrativeIntelligenceRunCompleted,
            SocialIntelligenceRunCompleted,
            StageCompleted,
        )

        event_map = {
            "social_intelligence_graph": lambda: SocialIntelligenceRunCompleted(
                division="social_intelligence",
                run_id=run_id,
                payload={"elapsed_ms": elapsed_ms},
            ),
            "creative_production_graph": lambda: CreativeProductionRunCompleted(
                division="creative",
                run_id=run_id,
                payload={"elapsed_ms": elapsed_ms},
            ),
            "publishing_connectors_graph": lambda: ConnectorRunCompleted(
                division="publishing",
                run_id=run_id,
                payload={"elapsed_ms": elapsed_ms},
            ),
        }
        bus = get_event_bus()
        builder = event_map.get(graph_name)
        if builder:
            bus.publish(builder())
        else:
            bus.publish(
                StageCompleted(
                    division="orchestration",
                    run_id=run_id,
                    payload={"graph": graph_name, "elapsed_ms": elapsed_ms},
                )
            )

    def clear_cache(self) -> None:
        self._graphs.clear()
