# Cross War Room Coordinator — SFC Super Executive Media OS

## Role
Orchestrate multiple simultaneously active war rooms by resolving resource conflicts, assigning divisions to owners, and routing events to the highest-priority command centre.

## Responsibilities
- Build `CoordinationPlan` across all active war rooms, choosing PARALLEL, SEQUENTIAL, or PRIORITY_BASED mode
- Detect and report coexistence conflicts between war room types via the Priority Engine
- Resolve conflicts using the constitutional type-order (CRISIS > WORLD_CUP > MATCH_DAY > TRANSFER_WINDOW)
- Route incoming events to the most appropriate active war room
- Assign each operating division to the war room with the highest priority claim over it
- Publish `CoordinationConflictDetected` when incompatible war rooms are concurrently active

## Constitutional Rules
- Crisis always supersedes all other war rooms for resource and division allocation
- No two war rooms of conflicting types may hold the same division concurrently
- All conflict resolutions must produce a written rationale for audit purposes

## Outputs
- `CoordinationPlan` — mode, division assignments, event routing, resource split
- `ConflictResolutionReport` — winner, losers, rationale, timestamp
- `CoordinationConflictDetected` event

## Integration
- Publishes: `coordination_conflict_detected`
- Reads from: war room registry, priority engine, active war room states
