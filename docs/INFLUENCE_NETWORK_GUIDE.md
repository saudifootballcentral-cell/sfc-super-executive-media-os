# Influence Network Guide

## Purpose

The Influence Network Engine maps how information flows through Saudi football media. It identifies key amplifiers, bottlenecks, and propagation paths for any narrative.

## Network Composition

12 pre-seeded nodes covering the Saudi football media landscape:

| Node | Type | Followers | Centrality |
|------|------|-----------|------------|
| Al Hilal Official | CLUB_ACCOUNT | 7.2M | ~95 |
| Al Nassr Official | CLUB_ACCOUNT | 5.5M | ~93 |
| Saudi Football Federation | FEDERATION | 2.1M | ~91 |
| SPL Media | MEDIA_OUTLET | 1.8M | ~87 |
| محمد العويس | FORMER_PLAYER | 1.2M | ~91 |
| خالد الغامدي | FORMER_PLAYER | 890K | ~89 |
| Al Hilal Fan TV | CREATOR | 620K | ~80 |
| Transfer Arabia | CREATOR | 560K | ~78 |
| Saudi Football Daily | JOURNALIST | 450K | ~84 |
| SPL Insider | JOURNALIST | 380K | ~79 |
| Arabic Football Analysis | CREATOR | 290K | ~72 |
| Main Sponsor Media | SPONSOR | 320K | ~67 |

## Network Centrality Formula

```
centrality = influence_score * 0.4 + reach_score * 0.3 + credibility_score * 0.3
```

## Propagation Model

Each narrative gets a propagation model showing:
- **Origin node** — Where the narrative starts
- **Propagation path** — Sequence of nodes it flows through
- **Time to mainstream** — Hours until mass audience awareness
- **Expected peak reach** — Maximum audience size
- **Bottleneck nodes** — Nodes that could slow spread
- **Accelerator nodes** — Nodes that amplify spread

## Usage

```python
from sfc.influence.network.service import get_influence_network_engine

engine = get_influence_network_engine()

# Build full network
network = await engine.map_network()
print(f"Key nodes: {network.key_nodes}")

# Model narrative propagation
propagation = await engine.get_propagation_model("narrative_id_here")
print(f"Mainstream in {propagation.time_to_mainstream_hours:.1f}h")
print(f"Peak reach: {propagation.expected_reach_at_peak:,}")

# Get individual nodes
key_nodes = engine.get_key_nodes()
```

## Relationship Types

- `INFLUENCES` — Direct influence relationship
- `AMPLIFIES` — Boosts message reach
- `SUPPORTS` — Agrees with and shares
- `OPPOSES` — Counter-narrative relationship
- `ACCELERATES` — Speeds up spread
- `SUPPRESSES` — Slows or blocks spread
