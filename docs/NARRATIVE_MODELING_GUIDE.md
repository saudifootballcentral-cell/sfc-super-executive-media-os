# Narrative Modeling Guide

## Purpose

The Narrative Modeling Engine identifies, profiles, and maps active narratives in Saudi football media. It detects narratives across 9 types and builds a relationship graph showing how they amplify, support, or oppose each other.

## Narrative Types

| Type | Description |
|------|-------------|
| PLAYER | Individual player narratives |
| CLUB | Club-level narratives |
| NATIONAL_TEAM | Saudi national team coverage |
| TRANSFER | Transfer window narratives |
| TOURNAMENT | Competition and tournament stories |
| SPONSOR | Commercial partner narratives |
| MEDIA | Media institution narratives |
| REFEREE | Officiating controversy |
| FAN | Fan community narratives |

## NarrativeProfile Fields

| Field | Type | Description |
|-------|------|-------------|
| profile_id | str | UUID |
| title | str | Narrative title |
| narrative_type | NarrativeType | Category |
| strength_score | float | 0-100 current strength |
| momentum_score | float | 0-100 growth momentum |
| sentiment_score | float | 0-100 sentiment (50=neutral) |
| credibility_score | float | 0-100 source credibility |
| virality_potential | float | 0-100 spread potential |
| influence_model | NarrativeInfluenceModel | Driver analysis |

## Usage

```python
from sfc.narrative.modeling.service import get_narrative_modeling_service

service = get_narrative_modeling_service()

# Get all narrative profiles
profiles = await service.model_narratives()

# Build full narrative map with relationships
narrative_map = await service.build_narrative_map()

# Filter by type
player_narratives = service.get_profiles_by_type(NarrativeType.PLAYER)
```

## Narrative Relationship Types

- **AMPLIFIES** — One narrative boosts another
- **SUPPORTS** — Narratives reinforce each other
- **OPPOSES** — Competing narratives
- **ORIGINATES** — One narrative spawns another
- **FEEDS** — Content feeds from one narrative to another
- **MERGES** — Two narratives combine

## NarrativeMap

```python
narrative_map.profiles          # list[NarrativeProfile]
narrative_map.relationships     # list[NarrativeRelationship]
narrative_map.dominant_narrative_id  # Most influential narrative
narrative_map.total_active      # Count of active narratives
```
