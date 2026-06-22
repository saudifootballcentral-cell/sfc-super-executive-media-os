"""ExecutionPlan — ordered, dependency-aware stage sequence for a workflow run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sfc.orchestration.master_state import WorkflowType


@dataclass
class ExecutionStage:
    name: str
    graph: str  # which graph drives this stage (or "builtin" for approval/skip)
    required: bool = True
    skippable_in_dry_run: bool = False
    depends_on: list[str] = field(default_factory=list)
    timeout_seconds: float = 300.0
    max_retries: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage catalogue
# ---------------------------------------------------------------------------

_DATA_INGESTION = ExecutionStage(
    name="data_ingestion",
    graph="builtin",
    required=True,
    timeout_seconds=60.0,
    metadata={"description": "Refresh fixture/provider cache — Package 10A"},
)

_SOCIAL_INTELLIGENCE = ExecutionStage(
    name="social_intelligence",
    graph="social_intelligence_graph",
    required=True,
    depends_on=["data_ingestion"],
    timeout_seconds=120.0,
    metadata={"description": "8B+8C social and narrative intelligence scan"},
)

_MAIN_PIPELINE = ExecutionStage(
    name="main_pipeline",
    graph="main_graph",
    required=True,
    depends_on=["social_intelligence"],
    timeout_seconds=180.0,
    metadata={"description": "Core 14-node pipeline: super_executive → learning"},
)

_CREATIVE_PRODUCTION = ExecutionStage(
    name="creative_production",
    graph="creative_production_graph",
    required=True,
    depends_on=["main_pipeline"],
    timeout_seconds=240.0,
    metadata={"description": "8E asset generation: images, video, thumbnails, audio, shorts, podcast"},
)

_GOVERNANCE_GATE = ExecutionStage(
    name="governance_gate",
    graph="builtin",
    required=True,
    depends_on=["creative_production"],
    timeout_seconds=30.0,
    metadata={"description": "Constitutional review — no bypass allowed"},
)

_OPERATOR_APPROVAL = ExecutionStage(
    name="operator_approval",
    graph="builtin",
    required=True,
    depends_on=["governance_gate"],
    timeout_seconds=3600.0,
    metadata={"description": "Human operator must grant approval before live publishing"},
)

_PUBLISHING = ExecutionStage(
    name="publishing",
    graph="publishing_connectors_graph",
    required=True,
    skippable_in_dry_run=True,
    depends_on=["operator_approval"],
    timeout_seconds=120.0,
    metadata={"description": "9A connectors: YouTube, X, Buffer — skipped in dry_run"},
)

_ANALYTICS = ExecutionStage(
    name="analytics",
    graph="builtin",
    required=True,
    depends_on=["publishing"],
    timeout_seconds=60.0,
    metadata={"description": "Post-publish analytics aggregation"},
)

_REPORTING = ExecutionStage(
    name="reporting",
    graph="builtin",
    required=False,
    depends_on=["analytics"],
    timeout_seconds=120.0,
    metadata={"description": "Autonomous executive reporting (Package 8)"},
)


# ---------------------------------------------------------------------------
# Workflow type → stage list
# ---------------------------------------------------------------------------

_WORKFLOW_STAGES: dict[WorkflowType, list[ExecutionStage]] = {
    WorkflowType.FULL_PIPELINE: [
        _DATA_INGESTION,
        _SOCIAL_INTELLIGENCE,
        _MAIN_PIPELINE,
        _CREATIVE_PRODUCTION,
        _GOVERNANCE_GATE,
        _OPERATOR_APPROVAL,
        _PUBLISHING,
        _ANALYTICS,
        _REPORTING,
    ],
    WorkflowType.DRY_RUN: [
        _DATA_INGESTION,
        _SOCIAL_INTELLIGENCE,
        _MAIN_PIPELINE,
        _CREATIVE_PRODUCTION,
        _GOVERNANCE_GATE,
        _OPERATOR_APPROVAL,
        _PUBLISHING,   # will be skipped (skippable_in_dry_run=True)
        _ANALYTICS,
        _REPORTING,
    ],
    WorkflowType.SOCIAL_INTELLIGENCE_ONLY: [
        _DATA_INGESTION,
        _SOCIAL_INTELLIGENCE,
    ],
    WorkflowType.CREATIVE_ONLY: [
        _DATA_INGESTION,
        _CREATIVE_PRODUCTION,
        _GOVERNANCE_GATE,
        _OPERATOR_APPROVAL,
    ],
    WorkflowType.PUBLISH_ONLY: [
        _GOVERNANCE_GATE,
        _OPERATOR_APPROVAL,
        _PUBLISHING,
        _ANALYTICS,
    ],
    WorkflowType.REPORTING: [
        _DATA_INGESTION,
        _REPORTING,
    ],
}


class ExecutionPlan:
    """Ordered, dependency-validated sequence of stages for a single run."""

    def __init__(self, workflow_type: WorkflowType, dry_run: bool = True) -> None:
        self.workflow_type = workflow_type
        self.dry_run = dry_run
        self._stages = list(_WORKFLOW_STAGES.get(workflow_type, _WORKFLOW_STAGES[WorkflowType.FULL_PIPELINE]))

    @property
    def stages(self) -> list[ExecutionStage]:
        return self._stages

    @property
    def stage_names(self) -> list[str]:
        return [s.name for s in self._stages]

    def get_stage(self, name: str) -> ExecutionStage | None:
        return next((s for s in self._stages if s.name == name), None)

    def is_skippable(self, stage_name: str) -> bool:
        stage = self.get_stage(stage_name)
        return self.dry_run and stage is not None and stage.skippable_in_dry_run

    def validate_dependencies(self) -> list[str]:
        """Return list of dependency violations (empty = valid).

        Only validates dependencies that are present in this workflow's stage list.
        Cross-workflow dependencies (e.g., creative_production depending on main_pipeline
        which is absent from CREATIVE_ONLY) are considered externally satisfied and ignored.
        """
        in_plan = {s.name for s in self._stages}
        known: set[str] = set()
        errors: list[str] = []
        for stage in self._stages:
            for dep in stage.depends_on:
                if dep in in_plan and dep not in known:
                    errors.append(
                        f"Stage '{stage.name}' depends on '{dep}' which is not defined before it"
                    )
            known.add(stage.name)
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_type": self.workflow_type.value,
            "dry_run": self.dry_run,
            "stages": [
                {
                    "name": s.name,
                    "graph": s.graph,
                    "required": s.required,
                    "skippable_in_dry_run": s.skippable_in_dry_run,
                    "depends_on": s.depends_on,
                    "timeout_seconds": s.timeout_seconds,
                }
                for s in self._stages
            ],
        }
