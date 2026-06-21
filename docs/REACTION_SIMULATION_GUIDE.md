# Reaction Simulation Guide

## Purpose

The Public Reaction Simulator forecasts how Saudi football audiences, sponsors, and media will respond to specific scenarios before they occur. It enables proactive narrative management and risk mitigation.

## Simulation Scenarios

| Scenario | Positive | Negative | Controversy | Risk Level |
|----------|---------|---------|------------|-----------|
| TITLE_WIN | 90% | 5% | 5% | LOW |
| MATCH_WIN | 70% | 15% | 15% | LOW |
| TRANSFER_ANNOUNCEMENT | 65% | 20% | 15% | MEDIUM |
| SPONSORSHIP_DEAL | 55% | 35% | 10% | LOW |
| CLUB_STATEMENT | 50% | 30% | 20% | LOW |
| COACH_CHANGE | 40% | 30% | 30% | MEDIUM |
| TOURNAMENT_EXIT | 15% | 20% | 65% | HIGH |
| MATCH_LOSS | 20% | 30% | 50% | MEDIUM |
| PLAYER_SCANDAL | 10% | 25% | 65% | HIGH |
| REFEREE_CONTROVERSY | 15% | 15% | 70% | HIGH |

## ReactionForecast Fields

| Field | Description |
|-------|-------------|
| audience_reactions | Per-segment probability breakdowns |
| sponsor_reaction | Revenue impact and reputation risk |
| media_reaction | Coverage probability and tone |
| overall_positive_probability | Aggregate positive % |
| overall_negative_probability | Aggregate negative % |
| risk_score | Composite risk 0-100 |
| proceed_recommendation | bool — whether to proceed |
| recommended_timing | Optimal publishing window |

## Risk Score Formula

```
risk_score = negative_prob * 0.4 + controversy_risk * 0.35 + sponsor_reputation_risk * 0.25
```

Proceed recommendation: `risk_score < 70 AND negative_probability < 50`

## Usage

```python
from sfc.simulation.reaction.service import get_reaction_simulator
from sfc.simulation.reaction.models import SimulationScenario

simulator = get_reaction_simulator()

# Single scenario simulation
forecast = await simulator.simulate(
    scenario=SimulationScenario.TRANSFER_ANNOUNCEMENT,
    narrative_id="narrative_001",
    context={"player": "target_player_name"},
)

print(f"Proceed: {forecast.proceed_recommendation}")
print(f"Risk score: {forecast.risk_score}/100")
print(f"Best timing: {forecast.recommended_timing}")

# Batch simulation
scenarios = [SimulationScenario.MATCH_WIN, SimulationScenario.TITLE_WIN]
forecasts = await simulator.batch_simulate(scenarios)
```

## Audience Segments Simulated

- `core_fans` — Hardcore supporters
- `casual_fans` — Occasional followers
- `national_team_fans` — National team focus
- `media_followers` — Journalists and media

## Optimal Timing Recommendations

| Scenario | Recommended Timing |
|----------|-------------------|
| MATCH_WIN | Within 30 minutes of final whistle |
| TITLE_WIN | Immediately — ride the peak sentiment wave |
| TRANSFER_ANNOUNCEMENT | Friday 18:00-20:00 UTC for maximum reach |
| CLUB_STATEMENT | Morning (09:00 UTC) for news cycle pickup |
| Others | Peak hours: 19:00-22:00 UTC |
