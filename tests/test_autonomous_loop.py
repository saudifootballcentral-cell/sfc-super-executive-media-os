"""Regression tests: Package 11 — Autonomous Production Loop.

Covers:
1. DedupStore: unseen items pass; seen items are filtered; TTL eviction works
2. DedupStore: fingerprint is deterministic and case/whitespace-insensitive
3. LoopMetrics: counters increment correctly; to_dict() is safe
4. FixtureSourceProvider: returns non-empty list of dicts with 'headline' keys
5. AutonomousLoop: no_new_items status when all items already deduped
6. AutonomousLoop: governance_rejected status when pipeline returns no approved content
7. AutonomousScheduler: disabled by default (AUTONOMOUS_ENABLED not set)
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sfc.autonomous.dedup_store import DedupStore
from sfc.autonomous.loop import AutonomousLoop
from sfc.autonomous.metrics import LoopMetrics
from sfc.autonomous.scheduler import AutonomousScheduler
from sfc.autonomous.source_provider import FixtureSourceProvider


# ---------------------------------------------------------------------------
# 1. DedupStore — unseen items pass; seen items are filtered; TTL eviction
# ---------------------------------------------------------------------------

class TestDedupStore:
    def test_unseen_item_is_not_seen(self):
        store = DedupStore(window_hours=1)
        assert not store.is_seen("Al Hilal wins AFC")

    def test_mark_seen_makes_it_seen(self):
        store = DedupStore(window_hours=1)
        headline = "Ronaldo scores brace"
        store.mark_seen(headline)
        assert store.is_seen(headline)

    def test_size_increments_and_decrements(self):
        store = DedupStore(window_hours=1)
        assert store.size == 0
        store.mark_seen("headline A")
        store.mark_seen("headline B")
        assert store.size == 2

    def test_ttl_expired_item_is_evicted(self):
        """Items with a past expiry are evicted on the next read."""
        store = DedupStore(window_hours=0)  # 0-hour window → instant expiry
        store.mark_seen("expired headline")
        # Force a tiny forward in time so monotonic > expiry
        import time
        time.sleep(0.01)
        # is_seen triggers eviction
        assert not store.is_seen("expired headline")
        assert store.size == 0


# ---------------------------------------------------------------------------
# 2. DedupStore — fingerprint determinism
# ---------------------------------------------------------------------------

class TestDedupStoreFingerprint:
    def test_fingerprint_is_case_insensitive(self):
        store = DedupStore()
        assert store.fingerprint("Al Hilal WINS") == store.fingerprint("al hilal wins")

    def test_fingerprint_strips_whitespace(self):
        store = DedupStore()
        assert store.fingerprint("  Al Hilal  ") == store.fingerprint("Al Hilal")

    def test_different_headlines_have_different_fingerprints(self):
        store = DedupStore()
        assert store.fingerprint("Al Hilal wins") != store.fingerprint("Al Nassr wins")


# ---------------------------------------------------------------------------
# 3. LoopMetrics — counters and to_dict()
# ---------------------------------------------------------------------------

class TestLoopMetrics:
    def test_initial_state_all_zero(self):
        m = LoopMetrics()
        assert m.scans_total == 0
        assert m.pubs_total == 0
        assert m.cycles_failed == 0

    def test_record_scan_increments_counter(self):
        m = LoopMetrics()
        m.record_scan()
        m.record_scan()
        assert m.scans_total == 2

    def test_record_publish_increments_counters(self):
        m = LoopMetrics()
        m.record_scan()
        m.record_publish(buffer_id="abc123", platform="x")
        assert m.pubs_total == 1
        assert m.pubs_today == 1
        assert m.last_pub_buffer_id == "abc123"
        assert m.last_pub_platform == "x"

    def test_record_failure_increments_counter(self):
        m = LoopMetrics()
        m.record_failure()
        assert m.cycles_failed == 1

    def test_to_dict_returns_expected_keys(self):
        m = LoopMetrics()
        d = m.to_dict()
        for key in ("scans_total", "pubs_total", "pubs_today", "cycles_failed",
                    "items_deduped", "items_governance_rejected",
                    "last_scan_age_s", "last_pub_age_s",
                    "last_cycle_duration_ms", "last_pub_buffer_id", "last_pub_platform"):
            assert key in d, f"Missing key: {key}"

    def test_to_dict_last_scan_age_is_none_before_scan(self):
        m = LoopMetrics()
        d = m.to_dict()
        assert d["last_scan_age_s"] is None

    def test_to_dict_last_scan_age_after_scan(self):
        m = LoopMetrics()
        m.record_scan()
        d = m.to_dict()
        assert d["last_scan_age_s"] is not None
        assert d["last_scan_age_s"] >= 0.0


# ---------------------------------------------------------------------------
# 4. FixtureSourceProvider — returns valid items
# ---------------------------------------------------------------------------

class TestFixtureSourceProvider:
    def test_name(self):
        assert FixtureSourceProvider().name == "fixture"

    @pytest.mark.asyncio
    async def test_get_items_returns_list(self):
        provider = FixtureSourceProvider()
        items = await provider.get_items()
        assert isinstance(items, list)
        assert len(items) > 0

    @pytest.mark.asyncio
    async def test_each_item_has_headline(self):
        provider = FixtureSourceProvider()
        items = await provider.get_items()
        for item in items:
            assert "headline" in item, f"Item missing 'headline': {item}"
            assert isinstance(item["headline"], str)
            assert len(item["headline"]) > 0


# ---------------------------------------------------------------------------
# 5. AutonomousLoop — no_new_items when all already deduped
# ---------------------------------------------------------------------------

class TestAutonomousLoopNoNewItems:
    @pytest.mark.asyncio
    async def test_no_new_items_when_all_deduped(self):
        items = [{"headline": "Al Hilal wins", "source_url": "http://x.com"}]

        source = AsyncMock()
        source.name = "mock"
        source.get_items = AsyncMock(return_value=items)

        dedup = DedupStore(window_hours=1)
        dedup.mark_seen("Al Hilal wins")

        metrics = LoopMetrics()
        orchestrator = AsyncMock()

        loop = AutonomousLoop(
            orchestrator=orchestrator,
            source_provider=source,
            dedup_store=dedup,
            metrics=metrics,
        )

        result = await loop.run_cycle()

        assert result["status"] == "no_new_items"
        assert result["published"] is False
        orchestrator.run.assert_not_called()


# ---------------------------------------------------------------------------
# 6. AutonomousLoop — governance_rejected when pipeline returns no approved content
# ---------------------------------------------------------------------------

class TestAutonomousLoopGovernanceRejected:
    @pytest.mark.asyncio
    async def test_governance_rejected_when_no_approved_content(self):
        items = [{"headline": "Transfer rumour unverified", "source_url": "http://x.com",
                  "category": "rumour", "tags": [], "summary": "", "language": "en"}]

        source = AsyncMock()
        source.name = "mock"
        source.get_items = AsyncMock(return_value=items)

        dedup = DedupStore(window_hours=1)
        metrics = LoopMetrics()

        # Simulate pipeline returning empty approved_content (governance rejected)
        mock_state = MagicMock()
        mock_state.run_id = "test-run-id"
        mock_state.graph_states = {
            "main_graph": {"approved_content": [], "rejected_content": [{"reason": "low_confidence"}]},
        }

        orchestrator = AsyncMock()
        orchestrator.run = AsyncMock(return_value=mock_state)

        with patch.dict(os.environ, {"LIVE_PUBLISHING_ENABLED": "false", "OPERATOR_AUTO_APPROVE": "false"}):
            loop = AutonomousLoop(
                orchestrator=orchestrator,
                source_provider=source,
                dedup_store=dedup,
                metrics=metrics,
            )
            result = await loop.run_cycle()

        assert result["status"] == "governance_rejected"
        assert result["governance_approved"] is False
        assert result["published"] is False
        assert metrics.items_governance_rejected == 1


# ---------------------------------------------------------------------------
# 7. AutonomousScheduler — disabled by default
# ---------------------------------------------------------------------------

class TestAutonomousSchedulerDisabledByDefault:
    def test_disabled_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUTONOMOUS_ENABLED", None)
            scheduler = AutonomousScheduler()
            assert not scheduler.is_enabled

    def test_enabled_when_env_true(self):
        with patch.dict(os.environ, {"AUTONOMOUS_ENABLED": "true"}):
            scheduler = AutonomousScheduler()
            assert scheduler.is_enabled

    def test_disabled_when_env_false(self):
        with patch.dict(os.environ, {"AUTONOMOUS_ENABLED": "false"}):
            scheduler = AutonomousScheduler()
            assert not scheduler.is_enabled

    @pytest.mark.asyncio
    async def test_run_exits_immediately_when_disabled(self):
        with patch.dict(os.environ, {"AUTONOMOUS_ENABLED": "false"}):
            scheduler = AutonomousScheduler()
            # Should complete without hanging (disabled path exits immediately)
            await asyncio.wait_for(scheduler.run(), timeout=2.0)

    def test_metrics_initial_state(self):
        with patch.dict(os.environ, {"AUTONOMOUS_ENABLED": "false"}):
            scheduler = AutonomousScheduler()
            m = scheduler.metrics
            assert m.scans_total == 0
            assert m.pubs_total == 0
