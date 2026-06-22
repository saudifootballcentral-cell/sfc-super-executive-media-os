"""Shared constants for the Video Intelligence layer."""

import os

# Master switch — set to "true" to enable real video processing
def is_video_processing_enabled() -> bool:
    return os.environ.get("VIDEO_PROCESSING_ENABLED", "false").lower() == "true"


# Storage paths
VIDEO_STORAGE_ROOT = os.environ.get("VIDEO_STORAGE_PATH", "./artifacts/video")
CLIP_STORAGE_ROOT = os.environ.get("VIDEO_CLIP_STORAGE_PATH", "./artifacts/video/clips")

# Clip constraints
MIN_CLIP_DURATION = float(os.environ.get("VIDEO_MIN_CLIP_DURATION", "5"))
MAX_CLIP_DURATION = float(os.environ.get("VIDEO_MAX_CLIP_DURATION", "90"))
CLIP_QUALITY_THRESHOLD = float(os.environ.get("VIDEO_CLIP_QUALITY_THRESHOLD", "70.0"))

# Frame sampling
FRAME_SAMPLE_RATE = float(os.environ.get("VIDEO_FRAME_SAMPLE_RATE", "1.0"))  # fps

# Transcription
WHISPER_API_KEY = os.environ.get("VIDEO_WHISPER_API_KEY") or os.environ.get("OPENAI_API_KEY")

# Platform clip durations (seconds)
PLATFORM_MAX_DURATION = {
    "youtube_short": 60,
    "instagram_reel": 90,
    "tiktok": 180,
    "x_video": 140,
    "youtube_video": 3600,
    "podcast": 7200,
}

# Platform aspect ratios
PLATFORM_ASPECT_RATIO = {
    "youtube_short": "9:16",
    "instagram_reel": "9:16",
    "tiktok": "9:16",
    "x_video": "16:9",
    "youtube_video": "16:9",
}

# Event type weights for highlight scoring
EVENT_HIGHLIGHT_WEIGHTS = {
    "goal": 1.0,
    "save": 0.85,
    "penalty": 0.90,
    "red_card": 0.75,
    "var_review": 0.70,
    "skill": 0.80,
    "celebration": 0.75,
    "controversial": 0.70,
    "near_miss": 0.65,
    "crowd_reaction": 0.55,
    "coach_reaction": 0.50,
    "tactical_moment": 0.60,
    "yellow_card": 0.45,
    "substitution": 0.40,
    "injury": 0.50,
    "free_kick": 0.55,
    "corner": 0.35,
}
