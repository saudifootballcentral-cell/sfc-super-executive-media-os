# Executive Alert System — SFC Super Executive Media OS

## Role
Surface high-priority, decision-requiring items directly to executive leadership through a structured, categorised, and prioritised alert interface.

## Responsibilities
- Create `ExecutiveAlert` objects spanning eight categories: breaking news, crisis, opportunities, revenue, system failure, security, governance, and summaries
- Publish `ExecutiveAlertTriggered` events to the event bus for downstream subscribers
- Allow leadership to acknowledge alerts, timestamping the decision trail
- Maintain separate views: active alerts, critical-only alerts, and all alerts
- Generate `ExecutiveSummary` reports synthesising the full alert landscape for a period
- Ensure P1/P2 incidents raised by the Incident Management Engine are surfaced immediately

## Constitutional Rules
- All CRITICAL alerts require explicit acknowledgement before clearing
- Revenue opportunities and major opportunities must be surfaced within the session
- Executive summaries must accurately reflect decisions required vs. informational items

## Outputs
- `ExecutiveAlert` — categorised, severity-graded alert with recommended action
- `ExecutiveSummary` — period summary with key points, decisions, opportunities, and risks
- `ExecutiveAlertTriggered` event

## Integration
- Publishes: `executive_alert_triggered`
- Reads from: escalation framework, incident management engine, monitoring alerts
