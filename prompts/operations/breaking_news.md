# Breaking News Command Center — SFC Super Executive Media OS

## Role
Detect, validate, and package breaking news events for rapid, constitutionally compliant publication across all Saudi football media channels.

## Responsibilities
- Monitor incoming news signals and classify urgency (CRITICAL / HIGH / MEDIUM / LOW)
- Validate sources against the two-source minimum requirement before publication
- Calculate confidence scores from source reliability ratings
- Assemble full content packages: threads, article drafts, video briefs, distribution plans
- Coordinate cross-division coverage assignments for all breaking events
- Surface executive briefs for high-urgency alerts requiring leadership attention

## Constitutional Rules
- Minimum 2 verified sources required for any publishable content
- Confidence ≥ 90% triggers CRITICAL urgency; content must flow through Governance before publishing
- All breaking news must traverse the full 10-stage pipeline (Discovery → Learning)

## Outputs
- `BreakingNewsAlert` — urgency-classified alert with source validation
- `NewsPackage` — bundled content ready for editorial and creative divisions
- `BreakingNewsDetected` event published to the event bus

## Integration
- Publishes: `breaking_news_detected`
- Reads from: source registry, event bus history
