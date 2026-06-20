"""Tests that verify core constitutional rules are enforced by the OS."""

import asyncio
import pytest

from core.executive import SFCExecutive
from core.models import (
    ContentItem,
    ContentStatus,
    Division,
    EventType,
    OutputScores,
    Platform,
    Source,
)
from divisions.governance.division import GovernanceDivision, MINIMUM_CONFIDENCE, MINIMUM_SOURCES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def executive():
    return SFCExecutive()


@pytest.fixture
def governance(executive):
    return executive.get_division(GovernanceDivision)


def _make_content(
    source_count: int = 2,
    confidence: float = 90.0,
    brand_alignment: float = 85.0,
    status: ContentStatus = ContentStatus.DRAFT,
) -> ContentItem:
    sources = [Source(name=f"Source {i}", url=f"https://source{i}.com") for i in range(source_count)]
    scores = OutputScores(
        confidence_score=confidence,
        risk_score=max(0.0, 100.0 - confidence),
        source_count=source_count,
        brand_alignment_score=brand_alignment,
    )
    return ContentItem(
        title="Test Content",
        body="Body text for test content.",
        content_type="news_article",
        platforms=[Platform.X],
        status=status,
        scores=scores,
        sources=sources,
        division=Division.EDITORIAL,
    )


# ---------------------------------------------------------------------------
# Governance — Verification Policy
# ---------------------------------------------------------------------------

class TestVerificationPolicy:
    def test_content_with_two_sources_passes(self, governance):
        content = _make_content(source_count=2, confidence=90.0)
        review = governance.review_content(content)
        assert review.approved

    def test_content_with_one_source_fails(self, governance):
        content = _make_content(source_count=1)
        review = governance.review_content(content)
        assert not review.approved
        assert any("source" in r.lower() for r in review.reasons)

    def test_content_with_zero_sources_fails(self, governance):
        content = _make_content(source_count=0)
        review = governance.review_content(content)
        assert not review.approved


# ---------------------------------------------------------------------------
# Governance — Confidence Policy
# ---------------------------------------------------------------------------

class TestConfidencePolicy:
    def test_confidence_below_85_is_rejected_and_escalated(self, governance):
        content = _make_content(confidence=70.0)
        review = governance.review_content(content)
        assert not review.approved
        assert review.escalated

    def test_confidence_exactly_85_passes(self, governance):
        content = _make_content(confidence=85.0)
        review = governance.review_content(content)
        assert review.approved

    def test_confidence_above_85_passes(self, governance):
        content = _make_content(confidence=95.0)
        review = governance.review_content(content)
        assert review.approved

    def test_output_scores_escalation_flag(self):
        scores = OutputScores(
            confidence_score=84.9,
            risk_score=15.1,
            source_count=2,
            brand_alignment_score=85.0,
        )
        assert scores.requires_escalation

    def test_output_scores_no_escalation_at_85(self):
        scores = OutputScores(
            confidence_score=85.0,
            risk_score=15.0,
            source_count=2,
            brand_alignment_score=85.0,
        )
        assert not scores.requires_escalation


# ---------------------------------------------------------------------------
# Publishing Policy
# ---------------------------------------------------------------------------

class TestPublishingPolicy:
    def test_unapproved_content_is_not_publishable(self):
        content = _make_content(status=ContentStatus.DRAFT)
        assert not content.is_publishable

    def test_approved_content_with_good_scores_is_publishable(self):
        content = _make_content(confidence=90.0, source_count=2, status=ContentStatus.APPROVED)
        assert content.is_publishable

    def test_approved_but_low_confidence_not_publishable(self):
        content = _make_content(confidence=70.0, source_count=2, status=ContentStatus.APPROVED)
        assert not content.is_publishable

    def test_approved_but_one_source_not_publishable(self):
        content = _make_content(confidence=90.0, source_count=1, status=ContentStatus.APPROVED)
        assert not content.is_publishable


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

class TestEventBus:
    def test_event_is_logged(self, executive):
        async def run():
            await executive.dispatch(
                EventType.TREND_DETECTED,
                source="test",
                payload={"topic": "Al Hilal"},
            )
        asyncio.get_event_loop().run_until_complete(run())
        assert len(executive.event_bus.event_log) > 0

    def test_event_status_processed(self, executive):
        async def run():
            return await executive.dispatch(
                EventType.NEWS_DETECTED,
                source="test",
                payload={"headline": "Test News", "sources": [{"name": "s1"}, {"name": "s2"}]},
            )
        event = asyncio.get_event_loop().run_until_complete(run())
        assert event.status == "processed"


# ---------------------------------------------------------------------------
# Knowledge Graph
# ---------------------------------------------------------------------------

class TestKnowledgeGraph:
    def test_entity_can_be_added_and_retrieved(self, executive):
        from core.knowledge_graph.entities import Entity, EntityType
        player = Entity(entity_type=EntityType.PLAYER, name="Salem AlDossari")
        executive.knowledge_graph.add_entity(player)
        found = executive.knowledge_graph.find_by_name("Salem AlDossari")
        assert found is not None
        assert found.name == "Salem AlDossari"

    def test_relationship_connects_entities(self, executive):
        from core.knowledge_graph.entities import Entity, EntityType
        from core.knowledge_graph.relationships import RelationshipType
        kg = executive.knowledge_graph
        player = Entity(entity_type=EntityType.PLAYER, name="Neymar")
        club = Entity(entity_type=EntityType.CLUB, name="Al Hilal")
        kg.add_entity(player)
        kg.add_entity(club)
        kg.relate(player.entity_id, RelationshipType.PLAYS_FOR, club.entity_id)
        neighbors = kg.get_neighbors(player.entity_id)
        assert any(n.name == "Al Hilal" for n in neighbors)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class TestWorkingMemory:
    def test_context_created_and_released(self, executive):
        wm = executive.working_memory
        with wm.task_scope("test_task") as ctx:
            ctx.set("key", "value")
            assert ctx.get("key") == "value"
            task_id = ctx.task_id
        assert wm.get_task(task_id) is None

    def test_active_count_tracks_correctly(self, executive):
        wm = executive.working_memory
        ctx1 = wm.create_task("task_a")
        ctx2 = wm.create_task("task_b")
        assert wm.active_task_count == 2
        wm.complete_task(ctx1.task_id)
        assert wm.active_task_count == 1
        wm.complete_task(ctx2.task_id)
        assert wm.active_task_count == 0


class TestEpisodicMemory:
    def test_lesson_is_recorded(self, executive):
        em = executive.episodic_memory
        em.record(
            event="Transfer window opened",
            decision="Activate war room",
            result="Coverage increased 40%",
            lesson="Early activation improves reach significantly",
            division=Division.INTELLIGENCE,
        )
        lessons = em.get_lessons(Division.INTELLIGENCE)
        assert len(lessons) >= 1
        assert "Early activation" in lessons[-1]
