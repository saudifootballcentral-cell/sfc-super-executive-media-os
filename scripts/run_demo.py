"""SFC Super Executive Media OS — demo runner.

Boots the LangGraph pipeline and processes a sample transfer news event.
Set ANTHROPIC_API_KEY in your environment for live Claude decisions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# Make src importable when running from repo root
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)

from sfc.graph.graph import build_graph, get_graph_ascii
from sfc.graph.state import make_initial_state


async def run_transfer_scenario() -> None:
    """Simulate a Saudi Pro League transfer news event through the full pipeline."""

    print(get_graph_ascii())
    print("=" * 60)
    print("SCENARIO: Transfer confirmation — Saudi Pro League")
    print("=" * 60)

    state = make_initial_state(
        task_type="transfer",
        task_payload={
            "headline": "CONFIRMED: Al Hilal sign Brazilian star in record Saudi deal",
            "body": (
                "Al Hilal FC have officially confirmed the signing of a world-class "
                "Brazilian forward in what represents the biggest transfer fee in "
                "Saudi Pro League history."
            ),
            "is_rumor": False,
            "official_statement": True,
            "importance_score": 95,
            "players": ["[Player Name]"],
            "clubs": ["Al Hilal"],
            "competitions": ["Saudi Pro League"],
            "sources": [
                {
                    "name": "Al Hilal FC Official Statement",
                    "url": "https://alhilal.com",
                    "reliability": 99,
                },
                {
                    "name": "Saudi Football Federation",
                    "url": "https://saff.com.sa",
                    "reliability": 98,
                },
                {
                    "name": "Fabrizio Romano",
                    "url": "https://twitter.com/FabrizioRomano",
                    "reliability": 92,
                },
            ],
        },
    )

    print(f"\nRun ID: {state['run_id']}")
    print(f"Task Type: {state['task_type']}")
    print("\nStarting pipeline...\n")

    graph = build_graph()
    result = await graph.ainvoke(state)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

    print(f"\nStage: {result.get('pipeline_stage')}")
    print(f"Completed: {result.get('completed_at')}")

    decision = result.get("executive_decision", {})
    print(f"\nExecutive Decision:")
    print(f"  Priority:  {decision.get('priority', 'N/A')}")
    print(f"  Risk:      {decision.get('risk_level', 'N/A')}")
    print(f"  Strategy:  {decision.get('content_strategy', 'N/A')}")

    plan = result.get("execution_plan", {})
    print(f"\nExecution Plan:")
    print(f"  Platforms: {', '.join(plan.get('platforms_targeted', [])[:5])}")
    print(f"  Content:   {', '.join(plan.get('content_types', [])[:3])}")

    intel = result.get("intelligence_report", {})
    print(f"\nIntelligence:")
    print(f"  Confidence:  {intel.get('confidence_score', 0):.1f}%")
    print(f"  Sources:     {intel.get('source_count', 0)}")
    print(f"  Newsworth:   {intel.get('newsworthiness_score', 0)}")

    drafts = result.get("content_drafts", [])
    approved = result.get("approved_content", [])
    rejected = result.get("rejected_content", [])
    print(f"\nEditorial → Governance:")
    print(f"  Drafts:    {len(drafts)}")
    print(f"  Approved:  {len(approved)}")
    print(f"  Rejected:  {len(rejected)}")

    assets = result.get("creative_assets", [])
    print(f"\nCreative: {len(assets)} asset brief(s) produced")

    publish = result.get("publish_results", {})
    print(f"\nPublishing:")
    print(f"  Status:    {publish.get('status', 'N/A')}")
    print(f"  Jobs:      {publish.get('job_count', 0)}")

    analytics = result.get("analytics_report", {})
    print(f"\nAnalytics:")
    print(f"  Est. Reach:  {analytics.get('estimated_reach', 0):,}")
    print(f"  Revenue Sig: {analytics.get('revenue_signal_count', 0)}")
    print(f"  Rev. Impact: ${analytics.get('estimated_revenue_impact_usd', 0):,.0f}")

    lessons = result.get("lessons_learned", [])
    print(f"\nLessons Learned ({len(lessons)}):")
    for lesson in lessons:
        print(f"  • {lesson[:100]}")

    errors = result.get("errors", [])
    if errors:
        print(f"\n⚠ Errors: {errors}")

    memory = result.get("memory_update_log", [])
    print(f"\nMemory Updates: {len(memory)} record(s) persisted")
    print("\n" + "=" * 60)


async def run_match_scenario() -> None:
    """Simulate a match end event — smaller demo."""
    state = make_initial_state(
        task_type="match",
        task_payload={
            "headline": "Al Nassr 2-1 Al Ittihad — Full Time",
            "home_team": "Al Nassr",
            "away_team": "Al Ittihad",
            "score": "2-1",
            "sources": [
                {"name": "SPL Official", "url": "https://spl.com.sa", "reliability": 99},
                {"name": "Kooora", "url": "https://kooora.com", "reliability": 90},
            ],
        },
    )

    graph = build_graph()
    result = await graph.ainvoke(state)

    print(f"\nMatch scenario complete | approved={len(result.get('approved_content', []))} | "
          f"reach={result.get('analytics_report', {}).get('estimated_reach', 0):,}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SFC Super Executive Media OS Demo")
    parser.add_argument("--scenario", choices=["transfer", "match", "all"], default="transfer")
    args = parser.parse_args()

    if args.scenario in ("transfer", "all"):
        asyncio.run(run_transfer_scenario())
    if args.scenario in ("match", "all"):
        asyncio.run(run_match_scenario())
