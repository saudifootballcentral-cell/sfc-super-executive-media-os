"""War Rooms subsystem for the SFC Super Executive Media OS.

Four specialized war rooms:
- Match Day War Room (P3)
- World Cup War Room (P1)
- Transfer Window War Room (P3)
- Crisis Management War Room (P1)

Supporting infrastructure:
- WarRoomRegistry: central state store
- ActivationEngine: trigger → activation
- DeactivationEngine: closure + reports
- PriorityEngine: conflict resolution
- ResourceAllocationEngine: slot + budget management
"""

from __future__ import annotations
