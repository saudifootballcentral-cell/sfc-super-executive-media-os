# Reporting Guide

## Executive Reports

Six report periods covering all executive intelligence needs.

### Generating Reports

```python
from sfc.reporting.executive.service import ExecutiveReportService

service = ExecutiveReportService()
context = {"content_published": 5, "analytics_report": {...}}

daily   = await service.generate_daily_brief(context)
weekly  = await service.generate_weekly_report(context)
monthly = await service.generate_monthly_review(context)
quarterly = await service.generate_quarterly_review(context)
annual  = await service.generate_annual_summary(context)
dash    = await service.generate_dashboard_pack(context)
```

### ExecutiveReport Structure

Every `ExecutiveReport` contains:

| Field | Type | Description |
|-------|------|-------------|
| `executive_summary` | str | One-paragraph strategic overview |
| `key_wins` | list[str] | Top achievements this period |
| `key_risks` | list[str] | Critical risks requiring attention |
| `opportunities` | list[str] | Actionable opportunities |
| `recommendations` | list[str] | Prioritized action items |
| `ai_usage` | dict | AI call counts and model breakdown |
| `cost_summary` | dict | AI cost totals and by-provider |
| `war_room_summary` | dict | Active war room status |
| `persona_summary` | dict | Persona activation summary |
| `revenue_summary` | dict | Revenue opportunity tracking |
| `governance_summary` | dict | Content approval/rejection rates |
| `kpis` | list[ExecutiveKPI] | KPI metrics with trends |
| `ai_insights` | str | Claude-generated strategic insights |

### Exporting

```python
markdown = report.to_markdown()
data = report.to_dict()         # JSON-serializable dict
```

## Operational Reports

Seven report types for operations teams.

```python
from sfc.reporting.operational.service import OperationalReportService

service = OperationalReportService()
state = dict(pipeline_state)  # SFCState dict

war_room = await service.generate_war_room_report(state)
platform = await service.generate_platform_report(state)
persona  = await service.generate_persona_report(state)
analytics = await service.generate_analytics_report(state)
revenue  = await service.generate_revenue_report(state)
governance = await service.generate_governance_report(state)
infra    = await service.generate_infrastructure_report(state)
```

Each `OperationalReport` has status: `"ok"` / `"warning"` / `"critical"`.

## Report Delivery

```python
from sfc.reporting.delivery.service import ReportDeliveryService
from sfc.reporting.delivery.models import DeliveryChannel

service = ReportDeliveryService()
records = await service.deliver(
    report,
    channels=[
        DeliveryChannel.DASHBOARD,
        DeliveryChannel.MARKDOWN_EXPORT,
        DeliveryChannel.JSON_EXPORT,
        DeliveryChannel.EMAIL,       # requires SMTP_HOST env var
        DeliveryChannel.TELEGRAM,    # requires TELEGRAM_BOT_TOKEN
        DeliveryChannel.WHATSAPP,    # requires WHATSAPP_API_KEY
    ]
)

stats = service.get_delivery_stats()
log = service.get_delivery_log(limit=100)
read_status = service.get_read_status(report_id)
```

### Graceful Degradation

External channels (`EMAIL`, `TELEGRAM`, `WHATSAPP`) return `SKIPPED` status when credentials are not configured. The pipeline never fails due to missing delivery credentials.

| Channel | Required Env Var |
|---------|-----------------|
| EMAIL | `SMTP_HOST` |
| TELEGRAM | `TELEGRAM_BOT_TOKEN` |
| WHATSAPP | `WHATSAPP_API_KEY` |

### File Export

To write markdown/JSON to disk, pass an export directory:

```python
service = ReportDeliveryService(export_dir="/reports/output")
```
