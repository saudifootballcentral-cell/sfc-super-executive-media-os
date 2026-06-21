# Influencer Intelligence Engine

Identifies and ranks key influencers in the Saudi football media ecosystem.

## Influencer Types

JOURNALIST, CREATOR, ANALYST, FORMER_PLAYER, CLUB_ACCOUNT, MEDIA_ORG

## Composite Score Formula

```
composite_score = influence_score × 0.30
               + trust_score    × 0.20
               + reach_score    × 0.20
               + authority_score × 0.30
```

Range: 0–100. Velocity score is tracked separately but not included in composite.

## Default Tracked Influencers

The service pre-seeds 12 Saudi football influencers including journalists, creators, former players, club accounts, and media organizations — covering Arabic and bilingual content.

## Usage

```python
from sfc.social.influencer.service import get_influencer_service
from sfc.social.influencer.models import InfluencerType

svc = get_influencer_service()
top = await svc.get_top_influencers(limit=5, influencer_type=InfluencerType.JOURNALIST)
report = await svc.generate_report(top)
```

## Media Map

`report.media_map` — dict mapping influencer type → list of names. Used for partner outreach and content distribution planning.
