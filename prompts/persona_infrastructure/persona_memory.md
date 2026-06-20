# Persona Memory Layer — SFC Super Executive Media OS

## Role
Lightweight in-memory store for persona knowledge snapshots, learning records, and assembled context packages.

## Responsibilities
- Save and retrieve knowledge snapshots per persona per namespace (global/division/working/episodic)
- Record learning events with lesson text and quality scores
- Assemble context packages combining snapshots and learnings for task execution
- Maintain PersonaMemoryState for each registered persona
- Provide deterministic, in-process storage with no external dependencies

## Constitutional Rules
- Memory operations must not block or introduce latency to the publishing pipeline
- All knowledge must be namespaced to prevent cross-persona contamination
- Context packages must be assembled on demand, not pre-cached

## Outputs
- KnowledgeSnapshot with namespace, content, and tags
- LearningRecord with lesson, context, and quality score
- ContextPackage aggregating snapshots and learnings for a task

## Integration
- Publishes: (none — memory layer is read/write only)
- Integrates with: PersonaEvaluationFramework, PersonaCollaborationEngine, LangGraph memory node
