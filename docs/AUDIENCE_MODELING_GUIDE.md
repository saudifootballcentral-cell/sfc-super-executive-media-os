# Audience Modeling Guide

## Purpose

The Audience Modeling subsystem builds digital twins for Saudi football audience segments, identifies clusters, tracks evolution, and forecasts growth and retention.

## Components

### Audience Digital Twins

Seven audience types modeled with behavioral fidelity:

| Type | Size | Primary Pattern |
|------|------|----------------|
| FAN | ~3.5M | Active Engager |
| SUPPORTER | ~1.2M | Content Sharer |
| CASUAL_FOLLOWER | ~4.8M | Passive Consumer |
| JOURNALIST | ~12K | Opinion Leader |
| INFLUENCER | ~8.5K | Trend Amplifier |
| SPONSOR | ~2.2K | Brand Advocate |
| EXECUTIVE | ~1.8K | Opinion Leader |

### Audience Clusters (Segmentation)

Eight clusters with precise targeting data:

| Cluster | Base Size | Engagement | Growth Rate |
|---------|-----------|------------|------------|
| HARDCORE_FANS | 900K | 15% | 4.5%/mo |
| CASUAL_FANS | 3.2M | 4% | 12.0%/mo |
| MATCH_DAY_FANS | 1.8M | 8% | 8.0%/mo |
| TRANSFER_FOLLOWERS | 750K | 12% | 20.0%/mo |
| NATIONAL_TEAM_FANS | 2.4M | 9% | 7.0%/mo |
| TACTICAL_ENTHUSIASTS | 380K | 18% | 5.0%/mo |
| MEDIA_FOLLOWERS | 220K | 22% | 6.0%/mo |
| SPONSOR_FOLLOWERS | 180K | 6% | 3.0%/mo |

## Usage

```python
# Digital Twins
from sfc.audience.modeling.service import get_audience_modeling_engine
engine = get_audience_modeling_engine()
twins = await engine.build_models()
report = await engine.generate_report(twins)

# Segmentation
from sfc.audience.segmentation.service import get_segmentation_engine
seg_engine = get_segmentation_engine()
segments = await seg_engine.segment()
segment_report = await seg_engine.generate_report(segments)

# Evolution
from sfc.audience.evolution.service import get_evolution_engine
evo_engine = get_evolution_engine()
evolution = await evo_engine.analyze_evolution(segments=[s.to_dict() for s in segments])
```

## BehaviorModel Fields

- `primary_pattern` — BehaviorPattern enum
- `engagement_rate` — Percentage engaging with content
- `share_propensity` — Likelihood to share (0-100)
- `narrative_adoption_speed` — How quickly they adopt narratives
- `platform_loyalty` — Stickiness to current platforms

## Evolution Drivers

- `NARRATIVE_ADOPTION` — Narrative spreads driving audience growth
- `PLATFORM_MIGRATION` — Users moving between platforms (x → tiktok)
- `BEHAVIOR_CHANGE` — Shifts in content consumption patterns
- `INTEREST_SHIFT` — Changing topic preferences
- `ENGAGEMENT_TREND` — Rising or falling engagement rates
