# Routing Engine — SFC Super Executive Media OS

## Role
Classifies incoming task intents and routes them to the most suitable primary and supporting personas.

## Responsibilities
- Classify task_type strings into RoutingIntent categories using keyword matching
- Select primary persona based on intent-to-category mapping
- Identify supporting personas from complementary categories
- Build ordered ExecutionPlans for multi-persona workflows
- Distribute workload evenly across persona pools via round-robin

## Constitutional Rules
- Primary persona must match the canonical category for the given intent
- Routing confidence must be calculated and reported for every decision
- Workload distribution must be deterministic and auditable

## Outputs
- RoutingDecision with primary and supporting persona IDs, confidence score, and rationale
- ExecutionPlan with ordered steps per persona
- Workload distribution map (persona_id → task_count)

## Integration
- Publishes: PersonaAssigned
- Integrates with: PersonaRegistry, PersonaCollaborationEngine, LangGraph routing node
