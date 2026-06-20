# Collaboration Engine — SFC Super Executive Media OS

## Role
Orchestrates multi-persona collaboration by forming teams, creating workflow plans, and building consensus outputs.

## Responsibilities
- Select ACTIVE personas matching required capabilities and assign LEAD/CONTRIBUTOR/REVIEWER roles
- Generate ordered CollaborationPlans with one step per team member
- Simulate contributions and compute confidence as mean performance score
- Resolve conflicts between two personas based on performance score comparison
- Publish collaboration lifecycle events at start and completion

## Constitutional Rules
- Teams must always have at least one LEAD persona
- Collaboration confidence must be computed from actual persona performance scores
- Conflict resolution must be deterministic and based on measurable metrics

## Outputs
- PersonaTeam with role-assigned member list
- CollaborationPlan with ordered workflow steps and expected outputs
- ConsensusReport with contributions, consensus output, and confidence score
- Conflict resolution dict with winner_id and rationale

## Integration
- Publishes: PersonaCollaborationStarted, PersonaCollaborationCompleted
- Integrates with: PersonaRegistry, PersonaRoutingEngine, PersonaRecommendationEngine
