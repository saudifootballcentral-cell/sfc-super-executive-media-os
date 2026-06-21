"""SFC Autonomous Operations — trigger engine and execution manager."""

from sfc.autonomous.execution_manager import AutonomousExecutionManager, get_execution_manager
from sfc.autonomous.trigger_engine import AutonomousTriggerEngine, TriggerEvent

__all__ = [
    "AutonomousExecutionManager",
    "get_execution_manager",
    "AutonomousTriggerEngine",
    "TriggerEvent",
]
