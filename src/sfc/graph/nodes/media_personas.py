"""Media & Platform Persona LangGraph nodes — standalone, not wired into main graph."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.media_personas")


async def tiktok_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.tiktok.service import TikTokPersona
    persona = TikTokPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "tiktok_persona_complete"}


async def instagram_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.instagram.service import InstagramPersona
    persona = InstagramPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "instagram_persona_complete"}


async def youtube_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.youtube.service import YouTubePersona
    persona = YouTubePersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "youtube_persona_complete"}


async def x_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.x.service import XPersona
    persona = XPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "x_persona_complete"}


async def shorts_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.shorts.service import ShortsPersona
    persona = ShortsPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "shorts_persona_complete"}


async def documentary_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.documentary.service import DocumentaryPersona
    persona = DocumentaryPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "documentary_persona_complete"}


async def thumbnail_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.thumbnail.service import ThumbnailPersona
    persona = ThumbnailPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "thumbnail_persona_complete"}


async def poster_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.poster.service import PosterPersona
    persona = PosterPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "poster_persona_complete"}


async def graphics_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.graphics.service import GraphicsPersona
    persona = GraphicsPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "graphics_persona_complete"}


async def podcast_host_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.podcast_host.service import PodcastHostPersona
    persona = PodcastHostPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "podcast_host_persona_complete"}


async def podcast_producer_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.podcast_producer.service import PodcastProducerPersona
    persona = PodcastProducerPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "podcast_producer_persona_complete"}


async def seo_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.seo.service import SEOPersona
    persona = SEOPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "seo_persona_complete"}


async def newsletter_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.newsletter.service import NewsletterPersona
    persona = NewsletterPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "newsletter_persona_complete"}


async def whatsapp_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.whatsapp.service import WhatsAppPersona
    persona = WhatsAppPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "whatsapp_persona_complete"}


async def telegram_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.media.telegram.service import TelegramPersona
    persona = TelegramPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {"media_persona_insight": insight.model_dump(), "pipeline_stage": "telegram_persona_complete"}
