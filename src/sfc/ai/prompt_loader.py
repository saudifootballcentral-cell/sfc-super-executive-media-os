"""Load prompts from disk, cache in memory."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("sfc.ai.prompt_loader")


def _find_repo_root() -> Path:
    """Locate repo root by env var, then by searching upward for prompts/.

    Strategy (tried in order):
    1. SFC_REPO_ROOT env var — always correct in Docker / Railway.
    2. Walk upward from __file__ looking for a dir that contains prompts/.
       Works from /app/src/sfc/ai/ AND from a venv site-packages path.
    3. Walk upward from CWD for the same sentinel.
    4. parents[3] — last resort, only correct from src/ layout.
    """
    env_root = os.environ.get("SFC_REPO_ROOT", "")
    if env_root:
        candidate = Path(env_root)
        if candidate.is_dir():
            return candidate

    for ancestor in Path(__file__).parents:
        if (ancestor / "prompts").is_dir():
            return ancestor

    cwd = Path(os.getcwd())
    if (cwd / "prompts").is_dir():
        return cwd
    for ancestor in cwd.parents:
        if (ancestor / "prompts").is_dir():
            return ancestor

    logger.warning(
        "[PromptLoader] Could not locate repo root via prompts/ sentinel — "
        "falling back to parents[3]. Set SFC_REPO_ROOT if prompts are missing."
    )
    return Path(__file__).parents[3]


class PromptLoader:
    """Loads and caches prompt assets from prompts/ directories."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], str] = {}
        self._repo_root = _find_repo_root()

    def load(self, category: str, name: str) -> str:
        """Load prompt.

        Args:
            category: One of divisions|personas|war_rooms|infrastructure|operations|
                      persona_infrastructure
            name: Filename without .md extension

        Returns:
            Prompt string, or a brief fallback system prompt if file not found.
        """
        cache_key = (category, name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Map category aliases
        category_dirs = {
            "divisions": "prompts/divisions",
            "personas": "prompts/personas",
            "war_rooms": "prompts/war_rooms",
            "infrastructure": "prompts/infrastructure",
            "operations": "prompts/operations",
            "persona_infrastructure": "prompts/persona_infrastructure",
        }

        dir_path = category_dirs.get(category, f"prompts/{category}")
        file_path = self._repo_root / dir_path / f"{name}.md"

        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
                self._cache[cache_key] = content
                logger.debug("[PromptLoader] Loaded %s/%s (%d chars)", category, name, len(content))
                return content
            except Exception as exc:
                logger.warning("[PromptLoader] Error reading %s: %s", file_path, exc)

        # Fallback: return a brief system prompt so the node still works
        fallback = (
            f"You are an AI assistant for the SFC Super Executive Media OS, "
            f"specializing in {category}/{name}. "
            "Respond in JSON format as instructed."
        )
        logger.warning(
            "[PromptLoader] Prompt not found: %s/%s — using fallback system prompt",
            category,
            name,
        )
        self._cache[cache_key] = fallback
        return fallback

    def load_constitution(self) -> str:
        """Load constitution/OFFICIAL_CONSTITUTION.md."""
        cache_key = ("_constitution", "OFFICIAL_CONSTITUTION")
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._repo_root / "constitution" / "OFFICIAL_CONSTITUTION.md"
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                self._cache[cache_key] = content
                return content
            except Exception as exc:
                logger.warning("[PromptLoader] Error reading constitution: %s", exc)

        fallback = "You are the SFC Super Executive AI. Follow constitutional rules strictly."
        self._cache[cache_key] = fallback
        return fallback

    def list_available(self, category: str) -> list[str]:
        """List available prompt names for a category (without .md extension)."""
        category_dirs = {
            "divisions": "prompts/divisions",
            "personas": "prompts/personas",
            "war_rooms": "prompts/war_rooms",
            "infrastructure": "prompts/infrastructure",
            "operations": "prompts/operations",
            "persona_infrastructure": "prompts/persona_infrastructure",
        }
        dir_path = category_dirs.get(category, f"prompts/{category}")
        folder = self._repo_root / dir_path
        if not folder.exists():
            return []
        return [p.stem for p in sorted(folder.glob("*.md"))]


# Process-level singleton
_instance: PromptLoader | None = None


def get_prompt_loader() -> PromptLoader:
    """Return process-level singleton PromptLoader."""
    global _instance
    if _instance is None:
        _instance = PromptLoader()
    return _instance
