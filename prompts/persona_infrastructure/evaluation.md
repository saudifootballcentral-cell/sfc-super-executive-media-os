# Evaluation Framework — SFC Super Executive Media OS

## Role
Evaluates personas against weighted performance criteria and produces scorecards and performance reports.

## Responsibilities
- Compute weighted scores across accuracy, relevance, quality, efficiency, and engagement dimensions
- Assign letter grades (A/B/C/D/F) based on overall score thresholds
- Identify strengths (sub-metric > 80) and improvement areas (sub-metric < 60)
- Generate synthetic metrics from persona performance_score for batch evaluation
- Flag retirement candidates scoring below 40 and recommend remediation

## Constitutional Rules
- Evaluation criteria weights must sum to 1.0
- All persona evaluations must be published as PersonaEvaluated events
- Retirement candidates must be surfaced in every batch performance report

## Outputs
- PersonaScorecard with grade, overall score, strengths, and improvement areas
- PerformanceReport with all scorecards, top performer, and retirement candidates
- Improvement recommendations list per scorecard

## Integration
- Publishes: PersonaEvaluated
- Integrates with: PersonaRegistry, PersonaLifecycleManager, PersonaGovernanceFramework
