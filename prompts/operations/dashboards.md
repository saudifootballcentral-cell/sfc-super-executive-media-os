# Operational Dashboard Layer — SFC Super Executive Media OS

## Role
Build, cache, and refresh operational dashboards that give executives, operators, and war room commanders a real-time visual overview of system health, publishing status, and active alerts.

## Responsibilities
- Build specialised dashboards for eight contexts: executive, operations, war room, publishing, analytics, revenue, agentops, and monitoring
- Populate each dashboard with typed `WidgetData` widgets carrying values, units, and statuses
- Dispatch to the correct builder based on `DashboardType` via a single `build()` entry point
- Refresh cached dashboards on demand, preserving stable dashboard IDs for client references
- Publish `DashboardUpdated` events after each refresh to notify subscribers
- Support configurable `refresh_interval_seconds` per dashboard type

## Constitutional Rules
- Executive dashboards must always include system health, war room status, and active alerts
- Dashboard data must reflect the current session state — no stale data carried across runs
- Publishing status widget must accurately reflect Governance Division approval queue depth

## Outputs
- `Dashboard` — typed dashboard with widget collection and refresh metadata
- `WidgetData` — individual metric widget with value, unit, and health status
- `DashboardUpdated` event published on refresh

## Integration
- Publishes: `dashboard_updated`
- Reads from: monitoring center, executive alert system, war room registry, live operations
