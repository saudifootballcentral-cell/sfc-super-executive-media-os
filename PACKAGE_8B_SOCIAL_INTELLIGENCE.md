# Package 8B — Social Intelligence & Trend Analysis Engine

Autonomous social intelligence platform for SFC Super Executive Media OS. Monitors Saudi football conversations across 8 platforms, detects trends and narratives, measures fan sentiment, tracks influencers, predicts virality, analyzes audiences, and activates crisis war rooms.

## Architecture

```
src/sfc/social/
├── center.py                    SocialIntelligenceCenter (master orchestrator)
├── trend_radar/
│   ├── models.py                TrendState, TrendMetrics, TrendReport, TrendRadarSnapshot
│   └── service.py               TrendRadarService — scans platforms, classifies trends
├── narrative/
│   ├── models.py                NarrativeLifecycle, NarrativeMetrics, Narrative, NarrativeMap
│   └── service.py               NarrativeIntelligenceService — detects narrative lifecycles
├── sentiment/
│   ├── models.py                SentimentMetrics, SentimentTarget_, FanPulseReport
│   └── service.py               FanSentimentService — measures fan emotion
├── influencer/
│   ├── models.py                InfluencerMetrics, InfluencerProfile, InfluencerReport
│   └── service.py               InfluencerIntelligenceService — tracks key influencers
├── virality/
│   ├── models.py                ViralityMetrics, ViralityForecast, ViralityBatch
│   └── service.py               ViralityPredictionEngine — forecasts content virality
├── audience/
│   ├── models.py                AudienceSegment, AudienceProfile, AudienceReport
│   └── service.py               AudienceIntelligenceService — analyzes fan segments
├── war_room/
│   ├── models.py                SocialWarRoomState, SocialWarRoomReport
│   └── service.py               SocialWarRoomService — activates crisis protocols
├── opportunity/
│   ├── models.py                OpportunityMetrics, Opportunity, OpportunityReport
│   └── service.py               OpportunityDetectionEngine — detects strategic opportunities
└── knowledge/
    ├── models.py                KnowledgeEntity, KnowledgeRelation, SocialKnowledgeSnapshot
    └── service.py               SocialKnowledgeLayer — persistent knowledge graph
```

## LangGraph Nodes (9 new)

| Node | Function | Output Key |
|------|----------|------------|
| `social_intelligence_node` | Full scan orchestrator | `social_intelligence_report` |
| `trend_radar_node` | Trend detection | `trend_radar_data` |
| `narrative_intelligence_node` | Narrative lifecycle | `narrative_intelligence_data` |
| `fan_sentiment_node` | Fan emotion measurement | `fan_sentiment_data` |
| `influencer_intelligence_node` | Influencer ranking | `influencer_data` |
| `virality_prediction_node` | Virality forecasting | `virality_forecast` |
| `audience_intelligence_node` | Audience segmentation | `audience_intelligence_data` |
| `opportunity_detection_node` | Strategic opportunities | `opportunity_detections` |
| `social_war_room_node` | Crisis activation | `social_war_room_state` |

## New Event Types (9)

- `trend_peaked` — trend reaches peak state
- `trend_declined` — trend enters declining/dead state
- `narrative_detected` — new narrative identified
- `narrative_shift_detected` — narrative changes lifecycle
- `sentiment_updated` — entity sentiment changes
- `sentiment_crisis_detected` — entity sentiment drops critically
- `influencer_detected` — new influencer identified
- `virality_forecast_generated` — virality forecast produced
- `social_war_room_activated` — war room activated

## Social Sources Monitored

X (Twitter), Instagram, TikTok, YouTube, Reddit, Google Trends, Forums, News

## Constitutional Compliance

- All social intelligence is **read-only analytics** — no content published from these nodes
- War room activations always route through `governance_node` before any publishing action
- All content still requires `len(sources) >= 2` and `confidence_score >= 85`
- No stage in the mandatory 10-stage pipeline is bypassed

## Running

```bash
pytest tests/social/ tests/integration/test_pkg8b_e2e.py -v
```
