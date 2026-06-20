"""Executive Reports — Daily, Weekly, Monthly, Quarterly, Annual."""

from __future__ import annotations

from datetime import datetime, date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from divisions.analytics.division import AnalyticsDivision
    from divisions.intelligence.division import IntelligenceDivision
    from divisions.revenue.division import RevenueDivision
    from agentops.monitors import CostMonitor, QualityMonitor


class ReportBase:
    """Base for all executive reports."""

    def __init__(self, generated_at: datetime | None = None) -> None:
        self.generated_at = generated_at or datetime.utcnow()

    def _header(self, title: str) -> str:
        line = "=" * 60
        return f"\n{line}\n{title}\nGenerated: {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}\n{line}\n"


class DailyBrief(ReportBase):
    """Daily Executive Brief — top-line summary for each operating day."""

    def generate(
        self,
        analytics: AnalyticsDivision,
        intelligence: IntelligenceDivision,
        cost_monitor: CostMonitor,
        quality_monitor: QualityMonitor,
    ) -> str:
        agg = analytics.aggregate_period(days=1)
        cost_report = cost_monitor.report()
        quality_report = quality_monitor.report()
        active_trends = intelligence.get_active_trends()

        lines: list[str] = [
            self._header("SFC SUPER EXECUTIVE — DAILY BRIEF"),
            f"Date: {date.today().strftime('%A, %d %B %Y')}",
            "",
            "[ CONTENT PERFORMANCE ]",
            f"  Content Published : {agg.get('content_count', 0)}",
            f"  Total Reach       : {agg.get('total_reach', 0):,}",
            f"  Avg Engagement    : {agg.get('avg_engagement_rate', 0.0)*100:.2f}%",
            f"  Watch Time        : {agg.get('total_watch_time_seconds', 0)//60:,} min",
            "",
            "[ INTELLIGENCE ]",
            f"  Active Trends     : {len(active_trends)}",
            f"  Unverified Rumors : {len(intelligence.get_unverified_rumors())}",
            "",
            "[ QUALITY ]",
            f"  Approval Rate     : {quality_report.get('approval_rate', 0.0)*100:.1f}%",
            f"  Hallucination Rate: {quality_report.get('hallucination_rate', 0.0)*100:.2f}%",
            f"  Publish Success   : {quality_report.get('publish_success_rate', 0.0)*100:.1f}%",
            "",
            "[ COST ]",
            f"  Total Cost Today  : ${cost_report.get('total_cost_usd', 0.0):.4f}",
            "",
        ]
        return "\n".join(lines)


class WeeklyReport(ReportBase):
    """Weekly Executive Report — full week performance review."""

    def generate(
        self,
        analytics: AnalyticsDivision,
        revenue: RevenueDivision,
        cost_monitor: CostMonitor,
    ) -> str:
        agg = analytics.aggregate_period(days=7)
        platform_breakdown = analytics.platform_breakdown()
        rev_forecast = revenue.forecast_revenue(period_days=7)
        cost_report = cost_monitor.report()

        lines: list[str] = [
            self._header("SFC SUPER EXECUTIVE — WEEKLY REPORT"),
            f"Week ending: {date.today().strftime('%d %B %Y')}",
            "",
            "[ WEEKLY PERFORMANCE ]",
            f"  Content Published : {agg.get('content_count', 0)}",
            f"  Total Reach       : {agg.get('total_reach', 0):,}",
            f"  Avg Engagement    : {agg.get('avg_engagement_rate', 0.0)*100:.2f}%",
            "",
            "[ PLATFORM BREAKDOWN ]",
        ]
        for platform, data in platform_breakdown.items():
            lines.append(f"  {platform:<20} Reach: {data.get('reach', 0):>10,}  Eng: {data.get('avg_engagement', 0.0)*100:.1f}%")

        lines += [
            "",
            "[ REVENUE ]",
            f"  Active Sponsors   : {rev_forecast.get('active_sponsors', 0)}",
            f"  Week Revenue Est. : ${rev_forecast.get('forecast_revenue_usd', 0.0):,.0f}",
            f"  Annualized        : ${rev_forecast.get('annualized_revenue_usd', 0.0):,.0f}",
            "",
            "[ COSTS ]",
            f"  Total Week Cost   : ${cost_report.get('total_cost_usd', 0.0):.2f}",
        ]
        for provider, cost in cost_report.get("by_provider", {}).items():
            lines.append(f"    {provider:<16}: ${cost:.4f}")

        lines.append("")
        return "\n".join(lines)


class MonthlyReview(ReportBase):
    """Monthly Performance Review — 30-day deep analysis."""

    def generate(self, analytics: AnalyticsDivision, revenue: RevenueDivision) -> str:
        agg = analytics.aggregate_period(days=30)
        rev_forecast = revenue.forecast_revenue(period_days=30)
        top_content = analytics.get_top_content(n=5)

        lines: list[str] = [
            self._header("SFC SUPER EXECUTIVE — MONTHLY PERFORMANCE REVIEW"),
            f"Month: {date.today().strftime('%B %Y')}",
            "",
            "[ MONTHLY TOTALS ]",
            f"  Content Published : {agg.get('content_count', 0)}",
            f"  Total Reach       : {agg.get('total_reach', 0):,}",
            f"  Total Watch Time  : {agg.get('total_watch_time_seconds', 0)//3600:,} hrs",
            f"  Avg Engagement    : {agg.get('avg_engagement_rate', 0.0)*100:.2f}%",
            "",
            "[ TOP 5 CONTENT ]",
        ]
        for i, item in enumerate(top_content, 1):
            lines.append(f"  {i}. [{item.get('platform','')}] Reach: {item.get('reach',0):,} — {item.get('content_id','')[:12]}")

        lines += [
            "",
            "[ REVENUE ]",
            f"  Month Revenue Est.: ${rev_forecast.get('forecast_revenue_usd', 0.0):,.0f}",
            "",
        ]
        return "\n".join(lines)


class QuarterlyStrategy(ReportBase):
    """Quarterly Strategy Review — strategic assessment and next quarter planning."""

    def generate(self, context: dict[str, Any] | None = None) -> str:
        ctx = context or {}
        lines: list[str] = [
            self._header("SFC SUPER EXECUTIVE — QUARTERLY STRATEGY REVIEW"),
            f"Quarter: Q{((date.today().month - 1) // 3) + 1} {date.today().year}",
            "",
            "[ STRATEGIC ASSESSMENT ]",
            f"  Audience Growth   : {ctx.get('follower_growth_pct', 'N/A')}%",
            f"  Revenue Growth    : {ctx.get('revenue_growth_pct', 'N/A')}%",
            f"  Share of Voice    : {ctx.get('share_of_voice_pct', 'N/A')}%",
            f"  Brand Authority   : {ctx.get('authority_score', 'N/A')}",
            "",
            "[ NEXT QUARTER PRIORITIES ]",
        ]
        for priority in ctx.get("next_priorities", ["[To be defined]"]):
            lines.append(f"  • {priority}")

        lines.append("")
        return "\n".join(lines)


class AnnualSummary(ReportBase):
    """Annual Executive Summary — full year state of the company."""

    def generate(self, context: dict[str, Any] | None = None) -> str:
        ctx = context or {}
        lines: list[str] = [
            self._header(f"SFC SUPER EXECUTIVE — ANNUAL SUMMARY {date.today().year}"),
            "",
            "[ YEAR IN REVIEW ]",
            f"  Total Content     : {ctx.get('total_content', 'N/A')}",
            f"  Total Reach       : {ctx.get('total_reach', 'N/A')}",
            f"  Total Revenue     : ${ctx.get('total_revenue_usd', 0):,.0f}",
            f"  Follower Growth   : {ctx.get('follower_growth', 'N/A')}",
            f"  Platform Authority: {ctx.get('authority_score', 'N/A')}",
            "",
            "[ KEY MILESTONES ]",
        ]
        for milestone in ctx.get("milestones", ["[No milestones recorded]"]):
            lines.append(f"  ✓ {milestone}")

        lines += [
            "",
            "[ STRATEGIC DIRECTION ]",
            f"  {ctx.get('strategic_direction', 'Continue executing on core mission.')}",
            "",
        ]
        return "\n".join(lines)
