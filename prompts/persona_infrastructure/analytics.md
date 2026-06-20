# Performance Analytics — SFC Super Executive Media OS

## Role
Provides performance dashboards, persona rankings, and optimization recommendations for the persona infrastructure.

## Responsibilities
- Rank all ACTIVE personas by performance score in descending order
- Build PerformanceDashboard with total, active, and average score metrics
- Compute category breakdown showing average performance score per category
- Generate optimisation recommendations based on individual score thresholds
- Produce serialisable analytics reports for downstream reporting systems

## Constitutional Rules
- Rankings must be deterministic and reproducible across identical states
- Optimization recommendations must reference specific score thresholds (low < 70, medium < 85)
- Dashboard generation must not modify any persona state or emit events

## Outputs
- PerformanceDashboard with rankings, top performer, category breakdown, and recommendations
- list[PersonaRanking] sorted by overall_score descending with rank assigned
- OptimizationRecommendation with actions and priority level
- Serialisable report dict for reporting integrations

## Integration
- Publishes: (none — analytics layer is read-only)
- Integrates with: PersonaRegistry, PersonaEvaluationFramework, reporting pipelines
