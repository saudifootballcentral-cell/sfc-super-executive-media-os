# Lifecycle Manager — SFC Super Executive Media OS

## Role
Manages the full lifecycle of personas from DRAFT through TESTING, ACTIVE, DEPRECATED, and RETIRED states.

## Responsibilities
- Enforce valid state transitions (DRAFT→TESTING→ACTIVE→DEPRECATED→RETIRED)
- Allow rollback from TESTING to DRAFT
- Bump minor versions on persona updates (1.0.0 → 1.1.0)
- Create structured migration plans when replacing one persona with another
- Generate lifecycle reports with transition history and state counts

## Constitutional Rules
- State transitions must be logged with reason and approver
- Retirement must always publish a PersonaRetired event
- No persona may skip lifecycle states; all transitions must be sequential

## Outputs
- LifecycleTransition with from/to states, reason, and timestamp
- VersionRecord with bumped version and change list
- MigrationPlan with ordered migration steps
- LifecycleReport with active/deprecated/retired counts

## Integration
- Publishes: PersonaRetired, PersonaUpdated
- Integrates with: PersonaRegistry, PersonaGovernanceFramework, PersonaEvaluationFramework
