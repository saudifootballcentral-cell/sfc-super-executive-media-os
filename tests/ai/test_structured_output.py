"""Tests for JSON extraction and Pydantic validation — no API calls."""

from __future__ import annotations

import pytest

from sfc.ai.structured_output import (
    ContentDraftAI,
    CreativeBriefAI,
    ExecutiveDecisionAI,
    IntelligenceReportAI,
    LearningExtractionAI,
    extract_json,
    validate_output,
)


class TestStructuredOutput:
    def test_extract_json_from_plain_text(self):
        """Extract JSON from plain text response."""
        text = '{"key": "value", "number": 42}'
        result = extract_json(text)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_from_markdown_fenced(self):
        """Extract JSON from markdown code fence."""
        text = "Here is the result:\n```\n{\"key\": \"value\"}\n```"
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_from_json_fenced(self):
        """Extract JSON from ```json ... ``` code fence."""
        text = "```json\n{\"status\": \"ok\", \"count\": 3}\n```"
        result = extract_json(text)
        assert result == {"status": "ok", "count": 3}

    def test_extract_json_returns_empty_dict_on_failure(self):
        """extract_json returns {} when no valid JSON found."""
        result = extract_json("This is just plain text with no JSON.")
        assert result == {}

    def test_extract_json_handles_empty_string(self):
        """extract_json handles empty string gracefully."""
        result = extract_json("")
        assert result == {}

    def test_extract_json_finds_embedded_json(self):
        """extract_json finds JSON embedded in text."""
        text = 'The result is: {"answer": 42} and that is final.'
        result = extract_json(text)
        assert result.get("answer") == 42

    def test_validate_executive_decision_valid(self):
        """Validate a valid ExecutiveDecisionAI JSON."""
        text = """{
            "task_analysis": "Transfer news detected.",
            "priority": "high",
            "risk_level": "medium",
            "recommended_divisions": ["intelligence", "editorial"],
            "content_strategy": "Full pipeline.",
            "routing": "planning",
            "rationale": "Standard transfer coverage.",
            "estimated_reach": 50000,
            "revenue_opportunity": true
        }"""
        instance, error = validate_output(text, ExecutiveDecisionAI)
        assert instance is not None
        assert error is None
        assert instance.priority == "high"
        assert instance.routing == "planning"
        assert instance.revenue_opportunity is True

    def test_validate_executive_decision_partial_response_uses_defaults(self):
        """Partial Claude response validates successfully — missing fields use defaults.

        Background: ExecutiveDecisionAI fields all have defaults so a response
        that omits some fields (e.g. sonnet fallback with different field names)
        still produces a valid instance with routing='planning' default.
        """
        text = '{"priority": "high"}'
        instance, error = validate_output(text, ExecutiveDecisionAI)
        assert instance is not None, "Partial response should validate with field defaults"
        assert error is None
        assert instance.priority == "high"
        assert instance.routing == "planning"   # default

    def test_validate_executive_decision_invalid_non_json_returns_none(self):
        """Non-JSON text still returns None + error (not recoverable)."""
        text = "This is plain text with no JSON at all."
        instance, error = validate_output(text, ExecutiveDecisionAI)
        assert instance is None
        assert error is not None

    def test_validate_intelligence_report_valid(self):
        """Validate a valid IntelligenceReportAI JSON."""
        text = """{
            "summary": "Match analysis complete.",
            "key_facts": ["Al Hilal won 2-1", "Ronaldo scored"],
            "confidence_score": 88.5,
            "is_rumor": false
        }"""
        instance, error = validate_output(text, IntelligenceReportAI)
        assert instance is not None
        assert error is None
        assert instance.confidence_score == 88.5
        assert len(instance.key_facts) == 2

    def test_validate_content_draft_valid(self):
        """Validate a valid ContentDraftAI JSON."""
        text = """{
            "title": "Al Hilal Clinches Title",
            "body": "In a dramatic finish...",
            "content_type": "article",
            "key_messages": ["Historic win", "Season recap"],
            "tone": "celebratory",
            "cta": "Read full match report"
        }"""
        instance, error = validate_output(text, ContentDraftAI)
        assert instance is not None
        assert error is None
        assert instance.title == "Al Hilal Clinches Title"

    def test_validate_extra_fields_ignored_defaults_fill_in(self):
        """Valid JSON with unrecognised fields still validates — defaults fill required fields.

        Pydantic ignores extra fields by default; all ExecutiveDecisionAI fields
        have defaults, so any JSON object (however wrong its keys) produces a
        valid instance with all defaults intact.
        """
        text = '{"title": "some title", "body": "some body"}'
        instance, error = validate_output(text, ExecutiveDecisionAI)
        assert instance is not None
        assert error is None
        assert instance.routing == "planning"   # default applied

    def test_validate_creative_brief_valid(self):
        """Validate a valid CreativeBriefAI JSON."""
        text = """{
            "concept": "Saudi football heritage meets modern digital storytelling.",
            "visual_direction": "Bold, kinetic style with gold accents.",
            "key_elements": ["Team badge", "Action photography", "Score overlay"],
            "color_palette": ["#006C35", "#FFFFFF"],
            "format_specs": {"aspect_ratio": "9:16"}
        }"""
        instance, error = validate_output(text, CreativeBriefAI)
        assert instance is not None
        assert error is None

    def test_validate_learning_extraction_valid(self):
        """Validate a valid LearningExtractionAI JSON."""
        text = """{
            "lessons": ["Source count matters", "Confidence threshold enforced"],
            "patterns": ["High-confidence transfer stories perform best"],
            "recommendations": ["Expand source network"]
        }"""
        instance, error = validate_output(text, LearningExtractionAI)
        assert instance is not None
        assert error is None
        assert len(instance.lessons) == 2

    def test_validate_output_handles_empty_text(self):
        """validate_output handles empty text gracefully."""
        instance, error = validate_output("", ExecutiveDecisionAI)
        assert instance is None
        assert error is not None
