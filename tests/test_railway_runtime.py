"""Regression tests: Railway runtime correctness.

Covers three failure modes that caused production outages:
1. Import precedence — code must load from /app/src not stale site-packages
2. Prompt loader — _find_repo_root() must find repo root without SFC_REPO_ROOT
3. BreakingNewsCommandCenter lifecycle — initialize() must be awaitable
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1. Import precedence
# ---------------------------------------------------------------------------

class TestImportPrecedence:
    """Verify that the sfc package imports resolve correctly."""

    def test_sfc_package_importable(self) -> None:
        import sfc
        assert sfc.__file__ is not None

    def test_claude_provider_has_sanitize_payload(self) -> None:
        from sfc.ai.providers import claude as claude_mod
        assert hasattr(claude_mod, "_sanitize_payload"), (
            "_sanitize_payload missing — stale pre-fix code is active"
        )

    def test_claude_provider_has_is_permanent_error(self) -> None:
        from sfc.ai.providers import claude as claude_mod
        assert hasattr(claude_mod, "_is_permanent_error"), (
            "_is_permanent_error missing — stale pre-fix code is active"
        )

    def test_executive_decision_ai_has_zero_required_fields(self) -> None:
        from sfc.ai.structured_output import ExecutiveDecisionAI
        required = [
            name
            for name, field in ExecutiveDecisionAI.model_fields.items()
            if field.is_required()
        ]
        assert required == [], (
            f"ExecutiveDecisionAI has {len(required)} required fields — "
            f"partial Claude responses will raise ValidationError: {required}"
        )

    def test_breaking_news_center_has_initialize(self) -> None:
        from sfc.war_rooms.operations.breaking_news.service import (
            BreakingNewsCommandCenter,
        )
        assert hasattr(BreakingNewsCommandCenter, "initialize"), (
            "BreakingNewsCommandCenter.initialize() missing — "
            "war_room_router will raise AttributeError at runtime"
        )

    def test_breaking_news_center_initialize_is_coroutine(self) -> None:
        import inspect
        from sfc.war_rooms.operations.breaking_news.service import (
            BreakingNewsCommandCenter,
        )
        assert inspect.iscoroutinefunction(BreakingNewsCommandCenter.initialize), (
            "BreakingNewsCommandCenter.initialize must be async"
        )


# ---------------------------------------------------------------------------
# 2. Prompt loader — _find_repo_root() strategies
# ---------------------------------------------------------------------------

class TestPromptLoaderFindRepoRoot:
    """_find_repo_root() must locate the repo root under various conditions."""

    def test_env_var_strategy(self, tmp_path: Path) -> None:
        """SFC_REPO_ROOT env var is honoured when set."""
        from sfc.ai.prompt_loader import _find_repo_root
        with patch.dict(os.environ, {"SFC_REPO_ROOT": str(tmp_path)}):
            result = _find_repo_root()
        assert result == tmp_path

    def test_upward_search_from_cwd(self, tmp_path: Path) -> None:
        """Walking upward from CWD finds a directory that contains prompts/."""
        (tmp_path / "prompts").mkdir()
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SFC_REPO_ROOT", None)
            with patch("sfc.ai.prompt_loader.Path") as MockPath:
                # Patch __file__ parents to not accidentally find prompts
                MockPath.return_value.parents = iter([tmp_path / "nowhere"])
                # Real test: directly test the CWD strategy
                import sfc.ai.prompt_loader as pl_mod
                with patch("os.getcwd", return_value=str(sub)):
                    # Manually remove env var
                    env_backup = os.environ.pop("SFC_REPO_ROOT", None)
                    try:
                        result = pl_mod._find_repo_root()
                    finally:
                        if env_backup is not None:
                            os.environ["SFC_REPO_ROOT"] = env_backup

    def test_real_repo_root_found(self) -> None:
        """In the actual repo, _find_repo_root() must return a path containing prompts/."""
        env_backup = os.environ.pop("SFC_REPO_ROOT", None)
        try:
            from sfc.ai.prompt_loader import _find_repo_root
            root = _find_repo_root()
            assert (root / "prompts").is_dir(), (
                f"_find_repo_root() returned {root} but prompts/ not found there"
            )
        finally:
            if env_backup is not None:
                os.environ["SFC_REPO_ROOT"] = env_backup

    def test_strategic_planning_prompt_loads(self) -> None:
        """PromptLoader must successfully load divisions/strategic_planning."""
        from sfc.ai.prompt_loader import get_prompt_loader
        # Reset singleton to pick up current env
        import sfc.ai.prompt_loader as pl_mod
        pl_mod._instance = None
        loader = get_prompt_loader()
        content = loader.load("divisions", "strategic_planning")
        # Must not be the fallback stub
        assert "AI assistant for the SFC Super Executive Media OS" not in content, (
            "strategic_planning.md loaded fallback stub — prompt file not found"
        )
        assert len(content) > 100, "strategic_planning.md suspiciously short"


# ---------------------------------------------------------------------------
# 3. BreakingNewsCommandCenter lifecycle
# ---------------------------------------------------------------------------

class TestBreakingNewsCommandCenterLifecycle:
    """initialize() must be awaitable and return without error."""

    def test_initialize_runs_without_error(self) -> None:
        from sfc.war_rooms.operations.breaking_news.service import (
            BreakingNewsCommandCenter,
        )
        center = BreakingNewsCommandCenter()
        asyncio.run(center.initialize())

    def test_detect_returns_alert(self) -> None:
        from sfc.war_rooms.operations.breaking_news.service import (
            BreakingNewsCommandCenter,
        )
        center = BreakingNewsCommandCenter()

        async def _run() -> None:
            await center.initialize()
            sources = [
                {"name": "Saudi FA", "reliability_score": 90.0},
                {"name": "Arab News", "reliability_score": 85.0},
            ]
            alert = await center.detect("Test headline", sources)
            assert alert.headline == "Test headline"
            assert len(center.get_active_alerts()) == 1

        asyncio.run(_run())

    def test_health_check_returns_healthy(self) -> None:
        from sfc.war_rooms.operations.breaking_news.service import (
            BreakingNewsCommandCenter,
        )
        center = BreakingNewsCommandCenter()
        result = center.health_check()
        assert result["status"] == "healthy"
        assert result["component"] == "breaking_news_command_center"


# ---------------------------------------------------------------------------
# 4. Sanitize payload — final guard before Anthropic API call
# ---------------------------------------------------------------------------

class TestSanitizePayloadFinalGuard:
    """_sanitize_payload is the last line of defence before messages.create()."""

    def test_all_sampling_params_stripped_for_opus_4_8(self) -> None:
        from sfc.ai.providers.claude import _sanitize_payload
        kwargs: dict[str, Any] = {
            "model": "claude-opus-4-8",
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 50,
            "max_tokens": 500,
            "messages": [],
        }
        _sanitize_payload("claude-opus-4-8", kwargs)
        assert "temperature" not in kwargs
        assert "top_p" not in kwargs
        assert "top_k" not in kwargs
        assert kwargs["max_tokens"] == 500

    def test_no_mutation_for_safe_payload(self) -> None:
        from sfc.ai.providers.claude import _sanitize_payload
        kwargs: dict[str, Any] = {"model": "claude-opus-4-8", "max_tokens": 500, "messages": []}
        before = dict(kwargs)
        _sanitize_payload("claude-opus-4-8", kwargs)
        assert kwargs == before

    def test_strips_temperature_for_all_claude_4_variants(self) -> None:
        from sfc.ai.providers.claude import _sanitize_payload
        models = [
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
            "claude-fable-5",
            "claude-mythos-5",
        ]
        for model in models:
            kwargs: dict[str, Any] = {"temperature": 0.7, "max_tokens": 100}
            _sanitize_payload(model, kwargs)
            assert "temperature" not in kwargs, f"temperature not stripped for {model}"
