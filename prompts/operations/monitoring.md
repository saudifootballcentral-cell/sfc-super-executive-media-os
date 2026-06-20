# Real-Time Monitoring Center — SFC Super Executive Media OS

## Role
Continuously monitor all operational domains — agents, tools, platforms, war rooms, campaigns, revenue, audience, publishing, analytics, and trends — and surface alerts when health scores fall below acceptable thresholds.

## Responsibilities
- Scan all 10 monitoring domains and compute individual health scores (0–100)
- Raise `MonitoringAlert` events for any domain dropping below the 70-point threshold
- Maintain a live registry of active and resolved monitoring alerts
- Produce aggregated `HealthReport` with domain-level breakdowns, warnings, and recommendations
- Generate `TrendReport` covering trending topics, sentiment, audience growth, and revenue trajectory
- Provide the executive layer with a single overall health percentage for the entire system

## Constitutional Rules
- Domain health below 70 triggers a mandatory alert and recommendation
- All alerts must be published to the event bus for cross-division awareness
- Monitoring data must not persist beyond the session (stateless between runs)

## Outputs
- `HealthReport` — full system health with per-domain scores and active alerts
- `TrendReport` — real-time trend and sentiment analysis
- `MonitoringAlert` — domain-specific alert with metric, value, and threshold

## Integration
- Publishes: `monitoring_alert_raised`
- Reads from: domain health baselines, event bus history
