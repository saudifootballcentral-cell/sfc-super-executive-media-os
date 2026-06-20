# Recommendation Engine — SFC Super Executive Media OS

## Role
Recommends the best-fit personas for incoming tasks by scoring candidates against task type, war room context, and performance history.

## Responsibilities
- Match task_type keywords to preferred persona categories
- Map war room types (match_day, world_cup, transfer, crisis, campaign) to category priorities
- Score personas by combining match score with performance score and select top 3
- Compute confidence score as mean performance of recommended team normalised to 0-1
- Project expected impact on engagement, quality, and revenue

## Constitutional Rules
- Recommendations must be evidence-based using quantified performance scores
- All recommendations must be published as PersonaRecommended events
- At least one persona must always be recommended, even for unrecognised task types

## Outputs
- PersonaRecommendation with recommended_team, confidence_score, and expected_impact
- Simplified team list from recommend_team() for quick integrations
- Health check confirming mapping tables are loaded

## Integration
- Publishes: PersonaRecommended
- Integrates with: PersonaRegistry, PersonaActivationEngine, PersonaCollaborationEngine
