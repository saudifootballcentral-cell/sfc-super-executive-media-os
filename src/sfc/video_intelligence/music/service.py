"""Background music selection service for Video Intelligence clips.

Selects a royalty-free music track from a local library based on clip theme.
No generative music API is used — the library is operator-supplied.

Library layout (recommended):
    $MUSIC_LIBRARY_PATH/
        energetic/   ← goals, saves, penalties, celebrations, skills
        calm/        ← interviews, press conferences, key quotes
        upbeat/      ← highlights, training, general
        *.mp3        ← fallback pool (used when no theme folder found)

Config:
    MUSIC_ENABLED            — master switch (default: false)
    MUSIC_LIBRARY_PATH       — root directory of the music library (required)
    MUSIC_VOLUME             — mix volume 0.0–1.0 (default: 0.12)
"""

from __future__ import annotations

import logging
import os
import random
from pathlib import Path

from sfc.video_intelligence.rendering.models import AudioTrack, AudioTrackType

logger = logging.getLogger("sfc.video_intelligence.music")

# Clip type → theme subdirectory
_THEME_MAP: dict[str, str] = {
    "goal": "energetic",
    "save": "energetic",
    "penalty": "energetic",
    "celebration": "energetic",
    "skill": "energetic",
    "controversial": "energetic",
    "red_card": "energetic",
    "near_miss": "energetic",
    "interview": "calm",
    "press_conference": "calm",
    "key_quote": "calm",
    "highlight": "upbeat",
    "training": "upbeat",
    "var_review": "upbeat",
}

_AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"}


def _is_enabled() -> bool:
    return os.environ.get("MUSIC_ENABLED", "false").lower() == "true"


def _library_path() -> Path | None:
    raw = os.environ.get("MUSIC_LIBRARY_PATH", "")
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def _music_volume() -> float:
    try:
        return float(os.environ.get("MUSIC_VOLUME", "0.12"))
    except ValueError:
        return 0.12


class MusicLibraryService:
    """Selects a background music track for a clip from the local library."""

    def __init__(self) -> None:
        self._library = _library_path()
        self._volume = _music_volume()
        # In-process rotation state: avoid repeating the same track too often
        self._last_picks: list[str] = []

    def select(self, clip_type: str) -> AudioTrack | None:
        """Return an AudioTrack for the given clip type, or None if unavailable."""
        if not _is_enabled():
            return None

        library = _library_path()
        if library is None:
            logger.debug("[Music] MUSIC_LIBRARY_PATH not set or not a directory")
            return None

        theme = _THEME_MAP.get(clip_type, "upbeat")
        track_path = self._pick_track(library, theme)
        if track_path is None:
            return None

        logger.info(
            "[Music] Selected %s track=%s for clip_type=%s",
            theme, track_path.name, clip_type,
        )
        return AudioTrack(
            track_type=AudioTrackType.MUSIC,
            local_path=str(track_path),
            volume=self._volume,
            start_offset_seconds=0.0,
        )

    def _pick_track(self, library: Path, theme: str) -> Path | None:
        # Try theme subdirectory first
        theme_dir = library / theme
        tracks = self._list_audio(theme_dir) if theme_dir.is_dir() else []

        # Fall back to root library pool
        if not tracks:
            tracks = self._list_audio(library)

        if not tracks:
            logger.warning("[Music] No audio files found in library: %s", library)
            return None

        # Avoid repeating recent picks; shuffle when list is short
        candidates = [t for t in tracks if str(t) not in self._last_picks]
        if not candidates:
            candidates = tracks
            self._last_picks.clear()

        pick = random.choice(candidates)  # noqa: S311 — non-security random selection
        self._last_picks.append(str(pick))
        if len(self._last_picks) > max(1, len(tracks) // 2):
            self._last_picks.pop(0)

        return pick

    def _list_audio(self, directory: Path) -> list[Path]:
        try:
            return [
                p for p in directory.iterdir()
                if p.is_file() and p.suffix.lower() in _AUDIO_EXTENSIONS
            ]
        except Exception:
            return []


_singleton: MusicLibraryService | None = None


def get_music_library_service() -> MusicLibraryService:
    global _singleton
    if _singleton is None:
        _singleton = MusicLibraryService()
    return _singleton
