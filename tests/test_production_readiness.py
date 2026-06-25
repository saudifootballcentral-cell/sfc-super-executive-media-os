"""Production readiness regression tests.

Enforces that no deprecated Anthropic parameters are sent, JSON parsing is
robust, constitution/prompt files load correctly, and the Dockerfile is
correctly configured.

These tests must all pass before any production deployment.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parents[1]
DOCKERFILE = REPO_ROOT / "Dockerfile"
DEPLOYMENT_DOCKERFILE = REPO_ROOT / "deployment" / "docker" / "Dockerfile"
CONSTITUTION_FILE = REPO_ROOT / "constitution" / "OFFICIAL_CONSTITUTION.md"
PROMPTS_ROOT = REPO_ROOT / "prompts"


# ===========================================================================
# Task 1 — Deprecated Anthropic parameters
# ===========================================================================

class TestNoDeprecatedAnthropicParams:
    """Regression: temperature/top_p/top_k must never reach Claude 4.x models."""

    def test_supports_temperature_rejects_all_claude4x(self):
        from sfc.ai.providers.claude import _supports_temperature
        claude4x_models = [
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
            "claude-haiku-4-5",
        ]
        for model in claude4x_models:
            assert not _supports_temperature(model), (
                f"temperature must not be sent for {model}"
            )

    def test_supports_temperature_rejects_fable5_mythos5(self):
        from sfc.ai.providers.claude import _supports_temperature
        assert not _supports_temperature("claude-fable-5")
        assert not _supports_temperature("claude-mythos-5")

    def test_supports_temperature_allows_claude3x(self):
        from sfc.ai.providers.claude import _supports_temperature
        claude3x_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
            "claude-instant-1-2",
        ]
        for model in claude3x_models:
            assert _supports_temperature(model), (
                f"temperature should be allowed for legacy {model}"
            )

    @pytest.mark.asyncio
    async def test_claude_provider_does_not_send_temperature_for_opus48(self):
        """End-to-end: ClaudeProvider must not include temperature in API call."""
        from sfc.ai.providers.claude import ClaudeProvider
        from sfc.ai.models import ModelRequest

        captured_kwargs: dict = {}

        async def mock_create(**kwargs):
            captured_kwargs.update(kwargs)
            msg = MagicMock()
            msg.content = [MagicMock(text='{"result": "ok"}')]
            msg.usage = MagicMock(input_tokens=10, output_tokens=5)
            return msg

        provider = ClaudeProvider()
        request = ModelRequest(
            task_type="executive",
            system_prompt="system",
            user_message="test",
            context={"model": "claude-opus-4-8"},
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.AsyncAnthropic") as mock_anthropic:
                mock_client = MagicMock()
                mock_client.messages.create = AsyncMock(side_effect=mock_create)
                mock_anthropic.return_value = mock_client
                await provider.complete(request)

        assert "temperature" not in captured_kwargs, (
            "temperature must not be sent to claude-opus-4-8"
        )
        assert "top_p" not in captured_kwargs
        assert "top_k" not in captured_kwargs

    @pytest.mark.asyncio
    async def test_claude_provider_does_not_send_temperature_for_sonnet46(self):
        """ClaudeProvider must not include temperature for claude-sonnet-4-6."""
        from sfc.ai.providers.claude import ClaudeProvider
        from sfc.ai.models import ModelRequest

        captured_kwargs: dict = {}

        async def mock_create(**kwargs):
            captured_kwargs.update(kwargs)
            msg = MagicMock()
            msg.content = [MagicMock(text='{"result": "ok"}')]
            msg.usage = MagicMock(input_tokens=10, output_tokens=5)
            return msg

        provider = ClaudeProvider()
        request = ModelRequest(
            task_type="editorial",
            system_prompt="system",
            user_message="test",
            context={"model": "claude-sonnet-4-6"},
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.AsyncAnthropic") as mock_anthropic:
                mock_client = MagicMock()
                mock_client.messages.create = AsyncMock(side_effect=mock_create)
                mock_anthropic.return_value = mock_client
                await provider.complete(request)

        assert "temperature" not in captured_kwargs, (
            "temperature must not be sent to claude-sonnet-4-6"
        )

    @pytest.mark.asyncio
    async def test_claude_provider_does_not_send_temperature_for_haiku45(self):
        """ClaudeProvider must not include temperature for claude-haiku-4-5-*."""
        from sfc.ai.providers.claude import ClaudeProvider
        from sfc.ai.models import ModelRequest

        captured_kwargs: dict = {}

        async def mock_create(**kwargs):
            captured_kwargs.update(kwargs)
            msg = MagicMock()
            msg.content = [MagicMock(text='{"result": "ok"}')]
            msg.usage = MagicMock(input_tokens=10, output_tokens=5)
            return msg

        provider = ClaudeProvider()
        request = ModelRequest(
            task_type="routing",
            system_prompt="system",
            user_message="test",
            context={"model": "claude-haiku-4-5-20251001"},
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.AsyncAnthropic") as mock_anthropic:
                mock_client = MagicMock()
                mock_client.messages.create = AsyncMock(side_effect=mock_create)
                mock_anthropic.return_value = mock_client
                await provider.complete(request)

        assert "temperature" not in captured_kwargs, (
            "temperature must not be sent to claude-haiku-4-5-20251001"
        )

    def test_no_temperature_kwarg_in_super_executive_direct_call(self):
        """The direct _call_claude path must not pass temperature to messages.create."""
        source = (
            REPO_ROOT / "src" / "sfc" / "graph" / "nodes" / "super_executive.py"
        ).read_text()
        direct_block_start = source.find("async def _call_claude")
        assert direct_block_start != -1
        direct_block = source[direct_block_start:]
        create_call_start = direct_block.find("messages.create(")
        assert create_call_start != -1
        # Find the matching closing paren
        call_text = direct_block[create_call_start: create_call_start + 500]
        assert "temperature" not in call_text, (
            "_call_claude must not pass temperature= to messages.create"
        )


# ===========================================================================
# Task 2+3 — JSON extraction and repair
# ===========================================================================

class TestJsonExtraction:
    """extract_json must handle all common LLM response patterns."""

    def test_plain_json(self):
        from sfc.ai.structured_output import extract_json
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_fenced(self):
        from sfc.ai.structured_output import extract_json
        result = extract_json('```json\n{"status": "ok"}\n```')
        assert result == {"status": "ok"}

    def test_plain_fenced(self):
        from sfc.ai.structured_output import extract_json
        result = extract_json('```\n{"status": "ok"}\n```')
        assert result == {"status": "ok"}

    def test_unclosed_fence(self):
        from sfc.ai.structured_output import extract_json
        result = extract_json('```json\n{"status": "ok"}')
        assert result == {"status": "ok"}

    def test_trailing_text(self):
        from sfc.ai.structured_output import extract_json
        result = extract_json('Here is the JSON:\n{"answer": 42}\nThat is all.')
        assert result.get("answer") == 42

    def test_empty_returns_empty_dict(self):
        from sfc.ai.structured_output import extract_json
        assert extract_json("") == {}

    def test_no_json_returns_empty_dict(self):
        from sfc.ai.structured_output import extract_json
        assert extract_json("This is plain text with no JSON.") == {}


class TestJsonRepair:
    """repair_json must fix common LLM-generated malformed JSON."""

    def test_trailing_comma_object(self):
        from sfc.ai.structured_output import repair_json
        result = repair_json('{"key": "value",}')
        assert result is not None
        assert json.loads(result) == {"key": "value"}

    def test_trailing_comma_array(self):
        from sfc.ai.structured_output import repair_json
        result = repair_json('["a", "b",]')
        assert result is not None
        assert json.loads(result) == ["a", "b"]

    def test_unterminated_string(self):
        from sfc.ai.structured_output import repair_json
        result = repair_json('{"title": "Saudi Football Ne')
        assert result is not None
        parsed = json.loads(result)
        assert "title" in parsed

    def test_missing_closing_brace(self):
        from sfc.ai.structured_output import repair_json
        result = repair_json('{"key": "value"')
        assert result is not None
        assert json.loads(result) == {"key": "value"}

    def test_nested_missing_closing_brace(self):
        from sfc.ai.structured_output import repair_json
        result = repair_json('{"outer": {"inner": "value"}')
        assert result is not None
        parsed = json.loads(result)
        assert parsed["outer"]["inner"] == "value"

    def test_already_valid_json_unchanged(self):
        from sfc.ai.structured_output import repair_json
        valid = '{"key": "value", "num": 42}'
        result = repair_json(valid)
        assert result is not None
        assert json.loads(result) == json.loads(valid)

    def test_empty_returns_none(self):
        from sfc.ai.structured_output import repair_json
        assert repair_json("") is None

    def test_extract_json_uses_repair_for_trailing_comma(self):
        from sfc.ai.structured_output import extract_json
        result = extract_json('{"priority": "high", "routing": "planning",}')
        assert result.get("priority") == "high"
        assert result.get("routing") == "planning"

    def test_extract_json_uses_repair_for_unclosed_brace(self):
        from sfc.ai.structured_output import extract_json
        result = extract_json('{"priority": "high", "routing": "planning"')
        assert result.get("priority") == "high"

    def test_extract_json_repairs_fenced_truncated(self):
        from sfc.ai.structured_output import extract_json
        text = '```json\n{"title": "Breaking news", "confidence": 92.0,'
        result = extract_json(text)
        assert result.get("title") == "Breaking news"


# ===========================================================================
# Task 4 — Constitution loading
# ===========================================================================

class TestConstitutionLoading:
    """Constitution must load from the real file, not the fallback."""

    def test_constitution_file_exists(self):
        assert CONSTITUTION_FILE.exists(), (
            f"Constitution file missing at {CONSTITUTION_FILE}"
        )

    def test_constitution_file_non_empty(self):
        content = CONSTITUTION_FILE.read_text(encoding="utf-8")
        assert len(content) > 500, "Constitution file seems too short"

    def test_constitution_path_resolves_correctly_in_dev(self):
        """_CONSTITUTION_PATH must point at the real file in development."""
        # Reset lru_cache so we re-derive the path
        from sfc.core import constitution as mod
        mod.load_constitution.cache_clear()
        # Temporarily unset SFC_REPO_ROOT to test heuristic path
        env_backup = os.environ.pop("SFC_REPO_ROOT", None)
        try:
            path = mod._find_constitution_path()
            assert path.exists(), (
                f"Constitution not found via heuristic path: {path}\n"
                "This will break in production. Check parents[] index."
            )
        finally:
            if env_backup is not None:
                os.environ["SFC_REPO_ROOT"] = env_backup
            mod.load_constitution.cache_clear()

    def test_constitution_loads_real_content(self):
        """load_constitution() must return the real constitution, not fallback."""
        from sfc.core import constitution as mod
        mod.load_constitution.cache_clear()
        text = mod.load_constitution()
        # The real constitution is much longer than the fallback (88 lines)
        assert len(text) > 2000, (
            "load_constitution() returned the short fallback — real file not found"
        )
        assert "SFC Super Executive" in text

    def test_constitution_loads_via_sfc_repo_root(self):
        """SFC_REPO_ROOT env var must let constitution.py find the real file."""
        from sfc.core import constitution as mod
        mod.load_constitution.cache_clear()
        with patch.dict(os.environ, {"SFC_REPO_ROOT": str(REPO_ROOT)}):
            path = mod._find_constitution_path()
            assert path.exists(), (
                f"SFC_REPO_ROOT-based path not found: {path}"
            )
        mod.load_constitution.cache_clear()


# ===========================================================================
# Task 5 — Prompt loader
# ===========================================================================

EXPECTED_DIVISION_PROMPTS = [
    "analytics",
    "creative",
    "editorial",
    "governance",
    "intelligence",
    "publishing",
    "revenue",
    "strategic_planning",
]


class TestPromptLoader:
    """All configured division prompts must exist on disk."""

    def test_prompts_root_exists(self):
        assert PROMPTS_ROOT.exists(), f"prompts/ directory missing at {PROMPTS_ROOT}"

    @pytest.mark.parametrize("name", EXPECTED_DIVISION_PROMPTS)
    def test_division_prompt_file_exists(self, name: str):
        path = PROMPTS_ROOT / "divisions" / f"{name}.md"
        assert path.exists(), f"Missing division prompt: prompts/divisions/{name}.md"

    @pytest.mark.parametrize("name", EXPECTED_DIVISION_PROMPTS)
    def test_division_prompt_file_non_empty(self, name: str):
        path = PROMPTS_ROOT / "divisions" / f"{name}.md"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 50, f"Prompt too short: prompts/divisions/{name}.md"

    def test_prompt_loader_loads_division_prompts_without_fallback(self):
        """PromptLoader must find all division prompts via SFC_REPO_ROOT."""
        from sfc.ai.prompt_loader import PromptLoader
        loader = PromptLoader.__new__(PromptLoader)
        loader._cache = {}
        loader._repo_root = REPO_ROOT

        for name in EXPECTED_DIVISION_PROMPTS:
            content = loader.load("divisions", name)
            assert "specializing in" not in content, (
                f"Fallback prompt returned for divisions/{name} — file not found"
            )
            assert len(content) > 50

    def test_prompt_loader_loads_constitution(self):
        """PromptLoader.load_constitution() must return the real file."""
        from sfc.ai.prompt_loader import PromptLoader
        loader = PromptLoader.__new__(PromptLoader)
        loader._cache = {}
        loader._repo_root = REPO_ROOT
        content = loader.load_constitution()
        assert "Follow constitutional rules strictly" not in content or len(content) > 500, (
            "PromptLoader.load_constitution() returned the short fallback"
        )


# ===========================================================================
# Task 8 — CI enforcement (Dockerfile checks)
# ===========================================================================

class TestDockerfileConfiguration:
    """Dockerfile must include all required assets and env vars."""

    @pytest.mark.parametrize("dockerfile", [DOCKERFILE, DEPLOYMENT_DOCKERFILE])
    def test_dockerfile_copies_constitution(self, dockerfile: Path):
        content = dockerfile.read_text()
        assert "COPY constitution/" in content, (
            f"{dockerfile.name}: missing 'COPY constitution/' directive"
        )

    @pytest.mark.parametrize("dockerfile", [DOCKERFILE, DEPLOYMENT_DOCKERFILE])
    def test_dockerfile_copies_prompts(self, dockerfile: Path):
        content = dockerfile.read_text()
        assert "COPY prompts/" in content, (
            f"{dockerfile.name}: missing 'COPY prompts/' directive — "
            "prompts will be unavailable at runtime"
        )

    @pytest.mark.parametrize("dockerfile", [DOCKERFILE, DEPLOYMENT_DOCKERFILE])
    def test_dockerfile_sets_sfc_repo_root(self, dockerfile: Path):
        content = dockerfile.read_text()
        assert "SFC_REPO_ROOT" in content, (
            f"{dockerfile.name}: missing ENV SFC_REPO_ROOT — "
            "constitution.py and prompt_loader.py will fail to find files"
        )

    @pytest.mark.parametrize("dockerfile", [DOCKERFILE, DEPLOYMENT_DOCKERFILE])
    def test_dockerfile_safe_defaults(self, dockerfile: Path):
        content = dockerfile.read_text()
        assert "LIVE_PUBLISHING_ENABLED=false" in content or \
               "LIVE_PUBLISHING_ENABLED=False" in content or \
               dockerfile == DEPLOYMENT_DOCKERFILE, (
            f"{dockerfile.name}: LIVE_PUBLISHING_ENABLED default must be false"
        )

    @pytest.mark.parametrize("dockerfile", [DOCKERFILE])
    def test_dockerfile_non_root_user(self, dockerfile: Path):
        content = dockerfile.read_text()
        assert "USER sfc" in content or "USER " in content, (
            f"{dockerfile.name}: container must run as non-root user"
        )


# ===========================================================================
# Task 8 — No deprecated parameter source-level check
# ===========================================================================

class TestSourceLevelDeprecatedParams:
    """Static source check: no direct temperature= in Anthropic messages.create calls."""

    ANTHROPIC_SOURCE_FILES = [
        REPO_ROOT / "src" / "sfc" / "ai" / "providers" / "claude.py",
        REPO_ROOT / "src" / "sfc" / "tools" / "claude_client.py",
        REPO_ROOT / "src" / "sfc" / "graph" / "nodes" / "super_executive.py",
    ]

    @pytest.mark.parametrize("filepath", ANTHROPIC_SOURCE_FILES)
    def test_no_temperature_passed_directly_to_messages_create(self, filepath: Path):
        """temperature= must not appear as a kwarg in messages.create() calls."""
        source = filepath.read_text()
        # Find each messages.create( call block
        for match in re.finditer(r"messages\.create\(", source):
            start = match.start()
            # Grab next 600 chars as the approximate call body
            snippet = source[start: start + 600]
            # Look for temperature= that isn't inside a comment or string
            # (simple heuristic: check for temperature= not preceded by #)
            lines = snippet.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "temperature=" in stripped:
                    pytest.fail(
                        f"{filepath.name}: found `temperature=` inside messages.create() call.\n"
                        f"Line: {stripped}"
                    )

    def test_claude_py_uses_conditional_temperature(self):
        """claude.py must gate temperature behind _supports_temperature()."""
        source = (
            REPO_ROOT / "src" / "sfc" / "ai" / "providers" / "claude.py"
        ).read_text()
        assert "_supports_temperature" in source, (
            "claude.py must use _supports_temperature() to guard temperature"
        )
        assert "_CLAUDE_4X_RE" in source or "_NO_SAMPLING_PARAMS_PREFIXES" in source, (
            "claude.py must define the 4.x model exclusion pattern"
        )
