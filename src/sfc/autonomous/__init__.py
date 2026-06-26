"""SFC Autonomous Operations — scheduler, loop, source providers, dedup, metrics."""

from sfc.autonomous.dedup_store import DedupStore
from sfc.autonomous.execution_manager import AutonomousExecutionManager, get_execution_manager
from sfc.autonomous.loop import AutonomousLoop
from sfc.autonomous.metrics import LoopMetrics
from sfc.autonomous.scheduler import AutonomousScheduler
from sfc.autonomous.source_provider import FixtureSourceProvider, SourceProvider
from sfc.autonomous.trigger_engine import AutonomousTriggerEngine, TriggerEvent

__all__ = [
    "AutonomousExecutionManager",
    "get_execution_manager",
    "AutonomousTriggerEngine",
    "TriggerEvent",
    "SourceProvider",
    "FixtureSourceProvider",
    "DedupStore",
    "LoopMetrics",
    "AutonomousLoop",
    "AutonomousScheduler",
]
