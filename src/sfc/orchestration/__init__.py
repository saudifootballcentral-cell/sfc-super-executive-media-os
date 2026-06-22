"""Package 10D — Master Orchestrator."""

from sfc.orchestration.approval_gate import ApprovalDeniedError, ApprovalGate, GateDecision
from sfc.orchestration.audit_trail import AuditEntry, AuditTrail
from sfc.orchestration.execution_plan import ExecutionPlan, ExecutionStage
from sfc.orchestration.graph_bridge import GraphBridge, GraphBridgeError
from sfc.orchestration.master_orchestrator import MasterOrchestrator
from sfc.orchestration.master_state import (
    ApprovalRecord,
    MasterState,
    RunStatus,
    StageRecord,
    StageStatus,
    WorkflowType,
)
from sfc.orchestration.persistence import (
    FuturePostgresPersistence,
    InMemoryPersistence,
    JSONLAuditPersistence,
    PersistenceProvider,
)
from sfc.orchestration.recovery import RecoveryEngine, RecoveryResult, RecoveryStrategy
from sfc.orchestration.run_context import RunContext
from sfc.orchestration.status import OrchestrationStatus, RunSummary
from sfc.orchestration.workflow_runner import WorkflowRunner

__all__ = [
    # Entry point
    "MasterOrchestrator",
    # State
    "MasterState",
    "WorkflowType",
    "RunStatus",
    "StageStatus",
    "StageRecord",
    "ApprovalRecord",
    # Planning
    "ExecutionPlan",
    "ExecutionStage",
    # Execution
    "WorkflowRunner",
    "GraphBridge",
    "GraphBridgeError",
    "RunContext",
    # Approval
    "ApprovalGate",
    "GateDecision",
    "ApprovalDeniedError",
    # Persistence
    "PersistenceProvider",
    "InMemoryPersistence",
    "JSONLAuditPersistence",
    "FuturePostgresPersistence",
    # Audit
    "AuditTrail",
    "AuditEntry",
    # Recovery
    "RecoveryEngine",
    "RecoveryStrategy",
    "RecoveryResult",
    # Status
    "OrchestrationStatus",
    "RunSummary",
]
