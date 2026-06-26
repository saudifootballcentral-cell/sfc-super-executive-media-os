"""Video Rendering Service — FFmpeg-based clip branding, concat, and export.

Capabilities
------------
* render_clip()       — brand a single enhanced clip: logo, subtitles, voice-over mix
* render_compilation() — concat N ordered clips into a highlight reel with intro/outro
* Dry-run mode when VIDEO_PROCESSING_ENABLED=false or FFmpeg is not on PATH
* All FFmpeg commands are logged for debugging

Environment variables
---------------------
VIDEO_PROCESSING_ENABLED   "true" to enable real FFmpeg processing
VIDEO_CLIP_STORAGE_PATH    root directory for all output files (default: ./artifacts/video/clips)
BRAND_LOGO_PATH            optional absolute path to SFC logo PNG
BRAND_INTRO_PATH           optional absolute path to branded intro .mp4
BRAND_OUTRO_PATH           optional absolute path to branded outro .mp4
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from sfc.video_intelligence.captioning.models import CaptioningResult, SubtitleTrack
from sfc.video_intelligence.clipping.models import VideoClip
from sfc.video_intelligence.enhancement.models import EnhancedClipVariant
from sfc.video_intelligence.rendering.models import (
    PLATFORM_SPECS,
    AudioMixConfig,
    AudioTrack,
    AudioTrackType,
    LogoPosition,
    PlatformRenderSpec,
    RenderMode,
    RenderStatus,
    RenderTemplate,
    RenderedVideo,
    SubtitleStyle,
    _DEFAULT_SPEC,
)
from sfc.video_intelligence.shared.constants import (
    CLIP_STORAGE_ROOT,
    is_video_processing_enabled,
)

logger = logging.getLogger("sfc.video_intelligence.rendering")

_singleton: "VideoRenderingService | None" = None

# FFmpeg subprocess timeout per render job (seconds)
_RENDER_TIMEOUT = int(os.environ.get("VIDEO_RENDER_TIMEOUT", "600"))


def get_video_rendering_service() -> "VideoRenderingService":
    global _singleton
    if _singleton is None:
        _singleton = VideoRenderingService()
    return _singleton


def _default_template() -> RenderTemplate:
    """Build a RenderTemplate from env vars, falling back to safe defaults."""
    return RenderTemplate(
        logo_path=os.environ.get("BRAND_LOGO_PATH", ""),
        intro_path=os.environ.get("BRAND_INTRO_PATH", ""),
        outro_path=os.environ.get("BRAND_OUTRO_PATH", ""),
    )


class VideoRenderingService:
    """Produces platform-ready video files from extracted clips."""

    def __init__(self) -> None:
        self._render_root = Path(CLIP_STORAGE_ROOT) / "rendered"
        self._render_root.mkdir(parents=True, exist_ok=True)
        self._ffmpeg = shutil.which("ffmpeg")
        self._ffprobe = shutil.which("ffprobe")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def render_clip(
        self,
        clip: VideoClip,
        variant: EnhancedClipVariant,
        captioning: CaptioningResult | None = None,
        audio_tracks: list[AudioTrack] | None = None,
        template: RenderTemplate | None = None,
    ) -> RenderedVideo:
        """Brand a single clip variant and produce a platform-ready file.

        Steps:
        1. Validate inputs and FFmpeg availability
        2. Overlay logo (if logo_path configured)
        3. Burn Arabic subtitles (if available and burn_in=True)
        4. Mix audio tracks (original, voice-over, music)
        5. Encode to platform spec
        """
        tmpl = template or _default_template()
        spec = PLATFORM_SPECS.get(variant.platform, _DEFAULT_SPEC)
        result = RenderedVideo(
            mode=RenderMode.SINGLE_CLIP,
            platform=variant.platform,
            source_clip_ids=[clip.clip_id],
        )

        if not is_video_processing_enabled() or not self._ffmpeg:
            return self._dry_run(result, spec, [clip])

        if not variant.local_path or not Path(variant.local_path).exists():
            result.status = RenderStatus.FAILED
            result.error_message = f"Variant file not found: {variant.local_path}"
            return result

        output_path = self._render_root / f"{clip.clip_id}_{variant.platform}_rendered.mp4"

        subtitle_track = self._best_subtitle(captioning, prefer_language="arabic")
        sidecar: dict[str, str] = {}
        if captioning:
            for track in captioning.tracks:
                if track.local_path:
                    sidecar[track.language] = track.local_path

        try:
            cmd = self._build_single_clip_cmd(
                input_path=variant.local_path,
                output_path=str(output_path),
                spec=spec,
                template=tmpl,
                subtitle_track=subtitle_track,
                audio_tracks=audio_tracks or [],
            )
            result.ffmpeg_cmd = cmd
            logger.info("[Render] Single clip: %s → %s", clip.clip_id, output_path.name)
            self._run(cmd)

            result = self._populate_result(result, output_path, sidecar)
        except Exception as exc:
            logger.error("[Render] Single clip failed clip_id=%s: %s", clip.clip_id, exc)
            result.status = RenderStatus.FAILED
            result.error_message = str(exc)

        return result

    async def render_compilation(
        self,
        clips: list[VideoClip],
        platform: str,
        captioning_results: list[CaptioningResult] | None = None,
        audio_tracks: list[AudioTrack] | None = None,
        template: RenderTemplate | None = None,
        compilation_id: str | None = None,
    ) -> RenderedVideo:
        """Concatenate multiple clips into a highlight reel with intro/outro.

        Steps:
        1. Filter clips that have local files ready
        2. Prepend intro if template.intro_path exists
        3. Concat all clip files via FFmpeg concat demuxer
        4. Append outro if template.outro_path exists
        5. Overlay logo, mix audio, burn subtitles
        6. Encode to platform spec
        """
        tmpl = template or _default_template()
        spec = PLATFORM_SPECS.get(platform, _DEFAULT_SPEC)
        comp_id = compilation_id or f"comp_{'_'.join(c.clip_id[:6] for c in clips[:3])}"
        result = RenderedVideo(
            mode=RenderMode.COMPILATION,
            platform=platform,
            source_clip_ids=[c.clip_id for c in clips],
        )

        if not is_video_processing_enabled() or not self._ffmpeg:
            return self._dry_run(result, spec, clips)

        ready_clips = [c for c in clips if c.is_file_ready]
        if not ready_clips:
            result.status = RenderStatus.FAILED
            result.error_message = "No clip files available for compilation"
            return result

        output_path = self._render_root / f"{comp_id}_{platform}_compilation.mp4"
        sidecar: dict[str, str] = {}

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)

                # Build ordered input list: [intro?] + clips + [outro?]
                segments: list[str] = []
                if tmpl.intro_path and Path(tmpl.intro_path).exists():
                    segments.append(tmpl.intro_path)

                # Re-encode each clip to a normalised intermediate to avoid
                # codec/resolution mismatches that break concat
                for i, clip in enumerate(ready_clips):
                    norm_path = tmp / f"norm_{i:03d}.mp4"
                    self._normalise_segment(clip.local_path, str(norm_path), spec)
                    segments.append(str(norm_path))

                if tmpl.outro_path and Path(tmpl.outro_path).exists():
                    segments.append(tmpl.outro_path)

                concat_file = tmp / "concat.txt"
                self._write_concat_list(segments, concat_file)

                # Merge subtitle tracks into one for the whole compilation
                merged_srt = self._merge_subtitles(ready_clips, captioning_results, tmp)
                if merged_srt:
                    sidecar["arabic"] = str(merged_srt)

                subtitle_track_path = merged_srt if tmpl.subtitle_style.burn_in else None

                cmd = self._build_compilation_cmd(
                    concat_file=str(concat_file),
                    output_path=str(output_path),
                    spec=spec,
                    template=tmpl,
                    subtitle_path=str(subtitle_track_path) if subtitle_track_path else "",
                    audio_tracks=audio_tracks or [],
                )
                result.ffmpeg_cmd = cmd
                logger.info(
                    "[Render] Compilation: %d clips → %s", len(ready_clips), output_path.name
                )
                self._run(cmd)

        except Exception as exc:
            logger.error("[Render] Compilation failed: %s", exc)
            result.status = RenderStatus.FAILED
            result.error_message = str(exc)
            return result

        return self._populate_result(result, output_path, sidecar)

    # ------------------------------------------------------------------
    # FFmpeg command builders
    # ------------------------------------------------------------------

    def _build_single_clip_cmd(
        self,
        input_path: str,
        output_path: str,
        spec: PlatformRenderSpec,
        template: RenderTemplate,
        subtitle_track: SubtitleTrack | None,
        audio_tracks: list[AudioTrack],
    ) -> list[str]:
        """Build the FFmpeg command for a single branded clip."""
        cmd: list[str] = [self._ffmpeg, "-y"]

        # Primary video input
        cmd += ["-i", input_path]

        # Additional audio inputs (voice-over, music)
        extra_audio = [t for t in audio_tracks if t.track_type != AudioTrackType.ORIGINAL]
        for track in extra_audio:
            if track.local_path and Path(track.local_path).exists():
                cmd += ["-i", track.local_path]

        # Logo overlay input
        has_logo = bool(template.logo_path and Path(template.logo_path).exists())
        if has_logo:
            cmd += ["-i", template.logo_path]

        n_inputs = 1 + len(extra_audio) + (1 if has_logo else 0)
        logo_idx = 1 + len(extra_audio) if has_logo else -1

        filter_parts: list[str] = []
        current_video = "0:v"
        current_audio = "0:a"

        # Audio mixing
        audio_out = self._build_audio_filter(
            base_audio=current_audio,
            extra_audio=extra_audio,
            mix=template.audio_mix,
            start_idx=1,
        )
        if audio_out["filter"]:
            filter_parts.append(audio_out["filter"])
            current_audio = audio_out["label"]

        # Logo overlay
        if has_logo:
            logo_filter, current_video = self._build_logo_filter(
                video_in=current_video,
                logo_idx=logo_idx,
                position=template.logo_position,
                scale_px=template.logo_scale_px,
                opacity=template.logo_opacity,
                spec=spec,
            )
            filter_parts.append(logo_filter)

        # Lower-third text overlay
        if template.lower_third_text:
            lt_filter, current_video = self._build_lower_third_filter(
                video_in=current_video,
                text=template.lower_third_text,
                spec=spec,
            )
            filter_parts.append(lt_filter)

        # Subtitle burn-in
        if subtitle_track and subtitle_track.local_path and template.subtitle_style.burn_in:
            sub_filter, current_video = self._build_subtitle_filter(
                video_in=current_video,
                srt_path=subtitle_track.local_path,
                style=template.subtitle_style,
            )
            filter_parts.append(sub_filter)

        if filter_parts:
            cmd += ["-filter_complex", ";".join(filter_parts)]
            cmd += ["-map", f"[{current_video}]"] if "[" in current_video else ["-map", current_video]
            cmd += ["-map", f"[{current_audio}]"] if "[" in current_audio else ["-map", current_audio]
        else:
            cmd += ["-map", "0:v", "-map", "0:a"]

        cmd += self._encoding_flags(spec)
        cmd.append(output_path)
        return cmd

    def _build_compilation_cmd(
        self,
        concat_file: str,
        output_path: str,
        spec: PlatformRenderSpec,
        template: RenderTemplate,
        subtitle_path: str,
        audio_tracks: list[AudioTrack],
    ) -> list[str]:
        """Build the FFmpeg command for a multi-clip compilation."""
        cmd: list[str] = [self._ffmpeg, "-y"]

        # Concat input
        cmd += ["-f", "concat", "-safe", "0", "-i", concat_file]

        # Additional audio
        extra_audio = [t for t in audio_tracks if t.track_type != AudioTrackType.ORIGINAL]
        for track in extra_audio:
            if track.local_path and Path(track.local_path).exists():
                cmd += ["-i", track.local_path]

        # Logo
        has_logo = bool(template.logo_path and Path(template.logo_path).exists())
        if has_logo:
            cmd += ["-i", template.logo_path]

        logo_idx = 1 + len(extra_audio) if has_logo else -1

        filter_parts: list[str] = []
        current_video = "0:v"
        current_audio = "0:a"

        audio_out = self._build_audio_filter(
            base_audio=current_audio,
            extra_audio=extra_audio,
            mix=template.audio_mix,
            start_idx=1,
        )
        if audio_out["filter"]:
            filter_parts.append(audio_out["filter"])
            current_audio = audio_out["label"]

        if has_logo:
            logo_filter, current_video = self._build_logo_filter(
                video_in=current_video,
                logo_idx=logo_idx,
                position=template.logo_position,
                scale_px=template.logo_scale_px,
                opacity=template.logo_opacity,
                spec=spec,
            )
            filter_parts.append(logo_filter)

        if template.lower_third_text:
            lt_filter, current_video = self._build_lower_third_filter(
                video_in=current_video,
                text=template.lower_third_text,
                spec=spec,
            )
            filter_parts.append(lt_filter)

        if subtitle_path and template.subtitle_style.burn_in:
            sub_filter, current_video = self._build_subtitle_filter(
                video_in=current_video,
                srt_path=subtitle_path,
                style=template.subtitle_style,
            )
            filter_parts.append(sub_filter)

        if filter_parts:
            cmd += ["-filter_complex", ";".join(filter_parts)]
            cmd += ["-map", f"[{current_video}]"] if "[" in current_video else ["-map", current_video]
            cmd += ["-map", f"[{current_audio}]"] if "[" in current_audio else ["-map", current_audio]
        else:
            cmd += ["-map", "0:v", "-map", "0:a"]

        cmd += self._encoding_flags(spec)
        cmd.append(output_path)
        return cmd

    # ------------------------------------------------------------------
    # FFmpeg filter helpers
    # ------------------------------------------------------------------

    def _build_audio_filter(
        self,
        base_audio: str,
        extra_audio: list[AudioTrack],
        mix: AudioMixConfig,
        start_idx: int,
    ) -> dict[str, str]:
        """Build amix filter for multi-track audio. Returns {"filter": ..., "label": ...}."""
        inputs: list[str] = []

        # Original (base) audio
        orig_label = "orig_a"
        inputs.append(f"[{base_audio}]volume={mix.original_volume:.2f}[{orig_label}]")
        mix_inputs = [f"[{orig_label}]"]

        for i, track in enumerate(extra_audio):
            if not track.local_path or not Path(track.local_path).exists():
                continue
            idx = start_idx + i
            vol = (
                mix.voiceover_volume
                if track.track_type == AudioTrackType.VOICEOVER
                else mix.music_volume
            )
            label = f"audio_{track.track_type.value}_{i}"
            inputs.append(f"[{idx}:a]volume={vol:.2f}[{label}]")
            mix_inputs.append(f"[{label}]")

        if len(mix_inputs) == 1 and mix.original_volume == 1.0:
            # No mixing needed — pass through unchanged
            return {"filter": "", "label": base_audio}

        out_label = "mixed_a"
        n = len(mix_inputs)
        amix = f"{''.join(mix_inputs)}amix=inputs={n}:duration=first:dropout_transition=0[{out_label}]"
        full_filter = ";".join(inputs) + ";" + amix
        return {"filter": full_filter, "label": out_label}

    def _build_logo_filter(
        self,
        video_in: str,
        logo_idx: int,
        position: LogoPosition,
        scale_px: int,
        opacity: float,
        spec: PlatformRenderSpec,
    ) -> tuple[str, str]:
        """Overlay a PNG logo at the specified corner. Returns (filter, out_label)."""
        out_label = "v_logo"
        scale_filter = f"[{logo_idx}:v]scale={scale_px}:-1,format=rgba,colorchannelmixer=aa={opacity:.2f}[logo]"

        margin = 14
        if position == LogoPosition.BOTTOM_RIGHT:
            xy = f"W-w-{margin}:H-h-{margin}"
        elif position == LogoPosition.BOTTOM_LEFT:
            xy = f"{margin}:H-h-{margin}"
        elif position == LogoPosition.TOP_RIGHT:
            xy = f"W-w-{margin}:{margin}"
        else:  # TOP_LEFT
            xy = f"{margin}:{margin}"

        overlay = f"[{video_in}][logo]overlay={xy}[{out_label}]"
        return f"{scale_filter};{overlay}", out_label

    def _build_lower_third_filter(
        self,
        video_in: str,
        text: str,
        spec: PlatformRenderSpec,
    ) -> tuple[str, str]:
        """Burn a lower-third text bar. Returns (filter, out_label)."""
        out_label = "v_lt"
        safe_text = text.replace("'", "\\'").replace(":", "\\:")
        y = int(spec.height * 0.88)
        drawtext = (
            f"[{video_in}]drawtext="
            f"text='{safe_text}':"
            f"fontsize=22:fontcolor=white:x=(w-text_w)/2:y={y}:"
            f"box=1:boxcolor=black@0.55:boxborderw=8"
            f"[{out_label}]"
        )
        return drawtext, out_label

    def _build_subtitle_filter(
        self,
        video_in: str,
        srt_path: str,
        style: SubtitleStyle,
    ) -> tuple[str, str]:
        """Burn SRT subtitles into the video. Returns (filter, out_label)."""
        out_label = "v_sub"
        safe_path = srt_path.replace(":", "\\:").replace("'", "\\'")
        force_style = (
            f"Fontname={style.font_name},"
            f"FontSize={style.font_size},"
            f"PrimaryColour={style.primary_colour},"
            f"OutlineColour={style.outline_colour},"
            f"Outline={style.outline_width},"
            f"Shadow={style.shadow}"
        )
        vpos = "(h-text_h-20)" if style.vertical_position == "bottom" else "20"
        sub_filter = (
            f"[{video_in}]subtitles='{safe_path}':"
            f"force_style='{force_style}'[{out_label}]"
        )
        return sub_filter, out_label

    # ------------------------------------------------------------------
    # Segment normalisation and concat
    # ------------------------------------------------------------------

    def _normalise_segment(
        self, input_path: str, output_path: str, spec: PlatformRenderSpec
    ) -> None:
        """Re-encode a segment to a uniform codec/resolution for concat."""
        w, h = spec.width, spec.height
        cmd = [
            self._ffmpeg, "-y", "-i", input_path,
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                   f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", spec.video_codec,
            "-preset", spec.preset,
            "-b:v", f"{spec.video_bitrate_kbps}k",
            "-r", str(int(spec.fps)),
            "-pix_fmt", spec.pixel_format,
            "-c:a", spec.audio_codec,
            "-b:a", f"{spec.audio_bitrate_kbps}k",
            "-ar", "48000",
            "-ac", "2",
            output_path,
        ]
        self._run(cmd, timeout=120)

    def _write_concat_list(self, segments: list[str], dest: Path) -> None:
        lines = "\n".join(f"file '{seg}'" for seg in segments)
        dest.write_text(lines, encoding="utf-8")

    # ------------------------------------------------------------------
    # Subtitle merge for compilations
    # ------------------------------------------------------------------

    def _merge_subtitles(
        self,
        clips: list[VideoClip],
        captioning_results: list[CaptioningResult] | None,
        workdir: Path,
    ) -> Path | None:
        """Merge SRT files from multiple clips into one, adjusting timestamps."""
        if not captioning_results:
            return None

        index_map: dict[str, CaptioningResult] = {
            c.clip_id: c for c in captioning_results
        }
        merged_lines: list[str] = []
        global_offset = 0.0
        entry_index = 1

        for clip in clips:
            result = index_map.get(clip.clip_id)
            if not result:
                global_offset += clip.duration_seconds
                continue

            track = result.track_for("arabic") or (result.tracks[0] if result.tracks else None)
            if not track or not track.entries:
                global_offset += clip.duration_seconds
                continue

            for entry in track.entries:
                start_s = self._srt_time_to_seconds(entry.start_time) + global_offset
                end_s = self._srt_time_to_seconds(entry.end_time) + global_offset
                merged_lines.extend([
                    str(entry_index),
                    f"{self._seconds_to_srt_time(start_s)} --> {self._seconds_to_srt_time(end_s)}",
                    entry.text,
                    "",
                ])
                entry_index += 1

            global_offset += clip.duration_seconds

        if not merged_lines:
            return None

        out = workdir / "merged_arabic.srt"
        out.write_text("\n".join(merged_lines), encoding="utf-8")
        return out

    # ------------------------------------------------------------------
    # Encoding and output flags
    # ------------------------------------------------------------------

    def _encoding_flags(self, spec: PlatformRenderSpec) -> list[str]:
        return [
            "-c:v", spec.video_codec,
            "-preset", spec.preset,
            "-b:v", f"{spec.video_bitrate_kbps}k",
            "-r", str(int(spec.fps)),
            "-pix_fmt", spec.pixel_format,
            "-c:a", spec.audio_codec,
            "-b:a", f"{spec.audio_bitrate_kbps}k",
            "-ar", "48000",
            "-ac", "2",
            "-movflags", "+faststart",
        ]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _run(self, cmd: list[str], timeout: int = _RENDER_TIMEOUT) -> None:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg exited {result.returncode}: {result.stderr[-800:]}"
            )

    def _populate_result(
        self,
        result: RenderedVideo,
        output_path: Path,
        sidecar: dict[str, str],
    ) -> RenderedVideo:
        if not output_path.exists():
            result.status = RenderStatus.FAILED
            result.error_message = "Output file not created"
            return result

        result.local_path = str(output_path)
        result.file_size_bytes = output_path.stat().st_size
        result.checksum_sha256 = self._sha256(output_path)
        result.sidecar_subtitle_paths = sidecar
        result.status = RenderStatus.COMPLETE

        probe = self._probe(str(output_path))
        if probe:
            result.duration_seconds = probe.get("duration", 0.0)
            result.width = probe.get("width", 0)
            result.height = probe.get("height", 0)
            result.fps = probe.get("fps", 0.0)

        logger.info(
            "[Render] Complete: %s | %dx%d %.1fs %d bytes",
            output_path.name,
            result.width,
            result.height,
            result.duration_seconds,
            result.file_size_bytes,
        )
        return result

    def _dry_run(
        self,
        result: RenderedVideo,
        spec: PlatformRenderSpec,
        clips: list[VideoClip],
    ) -> RenderedVideo:
        total = sum(c.duration_seconds for c in clips)
        result.status = RenderStatus.DRY_RUN
        result.dry_run = True
        result.duration_seconds = min(total, spec.max_duration_seconds)
        result.width = spec.width
        result.height = spec.height
        result.fps = spec.fps
        result.local_path = ""
        logger.info(
            "[Render] DRY_RUN platform=%s clips=%d estimated_duration=%.1fs",
            result.platform,
            len(clips),
            result.duration_seconds,
        )
        return result

    def _best_subtitle(
        self,
        captioning: CaptioningResult | None,
        prefer_language: str = "arabic",
    ) -> SubtitleTrack | None:
        if not captioning or not captioning.tracks:
            return None
        return captioning.track_for(prefer_language) or captioning.tracks[0]

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _probe(self, path: str) -> dict[str, Any] | None:
        if not self._ffprobe:
            return None
        try:
            r = subprocess.run(
                [
                    self._ffprobe, "-v", "quiet", "-print_format", "json",
                    "-show_streams", "-show_format", path,
                ],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0:
                return None
            data = json.loads(r.stdout)
            fmt = data.get("format", {})
            vs = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {},
            )
            rfr = vs.get("r_frame_rate", "30/1")
            num, den = (int(x) for x in rfr.split("/"))
            return {
                "duration": float(fmt.get("duration", 0)),
                "width": vs.get("width", 0),
                "height": vs.get("height", 0),
                "fps": num / max(den, 1),
            }
        except Exception:
            return None

    @staticmethod
    def _srt_time_to_seconds(t: str) -> float:
        """Convert "00:01:23,456" → seconds float."""
        t = t.replace(",", ".")
        parts = t.split(":")
        try:
            h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
            return h * 3600 + m * 60 + s
        except Exception:
            return 0.0

    @staticmethod
    def _seconds_to_srt_time(s: float) -> str:
        """Convert seconds float → "00:01:23,456"."""
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = s % 60
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{int(sec):02d},{ms:03d}"
