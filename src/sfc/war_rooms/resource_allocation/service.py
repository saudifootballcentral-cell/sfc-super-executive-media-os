"""Resource Allocation Engine — manages execution slots and budgets for war rooms."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sfc.war_rooms.resource_allocation.models import AllocationPlan, ResourceProfile, ResourceUtilization
from sfc.war_rooms.shared.types import WarRoomType

if TYPE_CHECKING:
    from sfc.war_rooms.registry.service import WarRoomRegistry

logger = logging.getLogger("sfc.war_rooms.resource_allocation")


class ResourceAllocationEngine:
    TOTAL_SLOTS = 10
    TOTAL_BUDGET_USD = 100.0

    PROFILES: dict[WarRoomType, ResourceProfile] = {
        WarRoomType.CRISIS: ResourceProfile(
            divisions=["intelligence", "editorial", "governance", "publishing"],
            capabilities=["fact_verification", "content_creation", "governance_review", "publishing"],
            memory_namespace="crisis",
            priority_slots=5,
            cost_budget_usd=25.0,
        ),
        WarRoomType.WORLD_CUP: ResourceProfile(
            divisions=["strategic_planning", "intelligence", "editorial", "creative", "publishing", "analytics", "revenue", "governance"],
            capabilities=["research", "content_creation", "video_generation", "publishing", "analytics"],
            memory_namespace="world_cup",
            priority_slots=8,
            cost_budget_usd=50.0,
        ),
        WarRoomType.MATCH_DAY: ResourceProfile(
            divisions=["intelligence", "editorial", "creative", "publishing", "analytics", "governance"],
            capabilities=["research", "content_creation", "video_generation", "publishing", "analytics"],
            memory_namespace="match_day",
            priority_slots=4,
            cost_budget_usd=15.0,
        ),
        WarRoomType.TRANSFER_WINDOW: ResourceProfile(
            divisions=["intelligence", "editorial", "revenue", "governance"],
            capabilities=["research", "fact_verification", "content_creation", "revenue_analysis"],
            memory_namespace="transfer_window",
            priority_slots=3,
            cost_budget_usd=10.0,
        ),
    }

    def __init__(self, registry: "WarRoomRegistry") -> None:
        self._registry = registry
        self._allocations: dict[str, AllocationPlan] = {}  # war_room_id → plan
        self._slots_used: int = 0
        self._budget_used: float = 0.0

    def allocate(self, war_room_id: str, war_room_type: WarRoomType) -> AllocationPlan:
        """Allocate resources to a newly activated war room."""
        profile = self.PROFILES.get(war_room_type)
        if profile is None:
            raise ValueError(f"No resource profile found for war room type: {war_room_type}")

        warnings: list[str] = []
        conflict_resolutions: list[str] = []

        # Check slot availability
        if self._slots_used + profile.priority_slots > self.TOTAL_SLOTS:
            available = self.TOTAL_SLOTS - self._slots_used
            warnings.append(
                f"Requested {profile.priority_slots} slots but only {available} available. "
                "Clamping to available slots."
            )
            # Use a reduced copy
            profile = ResourceProfile(
                divisions=profile.divisions,
                capabilities=profile.capabilities,
                memory_namespace=profile.memory_namespace,
                priority_slots=max(1, available),
                cost_budget_usd=profile.cost_budget_usd,
            )
            conflict_resolutions.append(f"Slot conflict resolved: reduced to {profile.priority_slots} slots")

        # Check budget
        if self._budget_used + profile.cost_budget_usd > self.TOTAL_BUDGET_USD:
            warnings.append(
                f"Budget constraint: requested ${profile.cost_budget_usd:.2f} "
                f"but only ${self.TOTAL_BUDGET_USD - self._budget_used:.2f} remaining."
            )

        plan = AllocationPlan(
            war_room_id=war_room_id,
            resources=profile,
            conflict_resolutions=conflict_resolutions,
            warnings=warnings,
        )
        self._allocations[war_room_id] = plan
        self._slots_used += profile.priority_slots
        self._budget_used += profile.cost_budget_usd

        logger.info(
            "[ResourceAllocation] Allocated %d slots to %s (total used: %d/%d)",
            profile.priority_slots, war_room_id, self._slots_used, self.TOTAL_SLOTS,
        )
        return plan

    def release(self, war_room_id: str) -> None:
        """Release all resources when a war room deactivates."""
        plan = self._allocations.pop(war_room_id, None)
        if plan is None:
            logger.warning("[ResourceAllocation] No allocation found for %s", war_room_id)
            return
        self._slots_used = max(0, self._slots_used - plan.resources.priority_slots)
        self._budget_used = max(0.0, self._budget_used - plan.resources.cost_budget_usd)
        logger.info("[ResourceAllocation] Released resources for %s", war_room_id)

    def get_utilization(self) -> ResourceUtilization:
        """Current resource utilization across all active war rooms."""
        division_utilization: dict[str, float] = {}
        for plan in self._allocations.values():
            for div in plan.resources.divisions:
                division_utilization[div] = division_utilization.get(div, 0.0) + 1.0

        # Normalize to 0-1 (max reasonable is 4 war rooms sharing a division)
        for div in division_utilization:
            division_utilization[div] = min(1.0, division_utilization[div] / 4.0)

        return ResourceUtilization(
            total_slots=self.TOTAL_SLOTS,
            used_slots=self._slots_used,
            division_utilization=division_utilization,
            budget_used_usd=round(self._budget_used, 2),
            budget_remaining_usd=round(self.TOTAL_BUDGET_USD - self._budget_used, 2),
        )

    def get_allocation(self, war_room_id: str) -> AllocationPlan | None:
        return self._allocations.get(war_room_id)

    def can_allocate(self, war_room_type: WarRoomType) -> bool:
        """Check if resources are available for a new war room."""
        profile = self.PROFILES.get(war_room_type)
        if profile is None:
            return False
        return self._slots_used + profile.priority_slots <= self.TOTAL_SLOTS

    def capacity_report(self) -> dict[str, Any]:
        utilization = self.get_utilization()
        return {
            "total_slots": self.TOTAL_SLOTS,
            "used_slots": self._slots_used,
            "available_slots": self.TOTAL_SLOTS - self._slots_used,
            "slot_utilization_pct": round(self._slots_used / self.TOTAL_SLOTS * 100, 1),
            "total_budget_usd": self.TOTAL_BUDGET_USD,
            "budget_used_usd": self._budget_used,
            "budget_remaining_usd": self.TOTAL_BUDGET_USD - self._budget_used,
            "active_allocations": len(self._allocations),
            "division_utilization": utilization.division_utilization,
        }
