# Incident Management Engine — SFC Super Executive Media OS

## Role
Detect, classify, contain, recover from, and learn from operational incidents affecting agents, tools, platforms, publishing, data, security, or governance systems.

## Responsibilities
- Detect incidents across seven types and four severity levels (P1–P4)
- Automatically escalate P1 and P2 incidents to the Executive Alert System
- Generate type-specific recovery plans with step-by-step remediation guidance
- Track the incident lifecycle through DETECTED → CONTAINED → RECOVERING → RESOLVED → POSTMORTEM
- Produce postmortem reports capturing root cause, contributing factors, lessons learned, and action items
- Maintain a registry of open incidents for operational visibility

## Constitutional Rules
- P1 incidents must trigger a CRITICAL executive alert immediately upon detection
- All incidents must have their root cause recorded before closure
- Security incidents require immediate isolation as the first recovery step
- Governance failures must suspend publishing until compliance review completes

## Outputs
- `Incident` — full incident record with timeline, severity, and affected components
- `RecoveryPlan` — ordered steps and estimated recovery time
- `Postmortem` — structured post-incident analysis with action items
- `IncidentDetected` and `IncidentResolved` events

## Integration
- Publishes: `incident_detected`, `incident_resolved`
- Reads from: executive alert system, platform health, agent monitoring
