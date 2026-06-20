"""Media & Platform Personas — SFC Super Executive Media OS."""
from __future__ import annotations

from sfc.personas.media.tiktok.service import TikTokPersona
from sfc.personas.media.instagram.service import InstagramPersona
from sfc.personas.media.youtube.service import YouTubePersona
from sfc.personas.media.x.service import XPersona
from sfc.personas.media.shorts.service import ShortsPersona
from sfc.personas.media.documentary.service import DocumentaryPersona
from sfc.personas.media.thumbnail.service import ThumbnailPersona
from sfc.personas.media.poster.service import PosterPersona
from sfc.personas.media.graphics.service import GraphicsPersona
from sfc.personas.media.podcast_host.service import PodcastHostPersona
from sfc.personas.media.podcast_producer.service import PodcastProducerPersona
from sfc.personas.media.seo.service import SEOPersona
from sfc.personas.media.newsletter.service import NewsletterPersona
from sfc.personas.media.whatsapp.service import WhatsAppPersona
from sfc.personas.media.telegram.service import TelegramPersona

_ALL_MEDIA_PERSONAS = [
    TikTokPersona, InstagramPersona, YouTubePersona, XPersona, ShortsPersona,
    DocumentaryPersona, ThumbnailPersona, PosterPersona, GraphicsPersona,
    PodcastHostPersona, PodcastProducerPersona, SEOPersona,
    NewsletterPersona, WhatsAppPersona, TelegramPersona,
]


def register_media_personas(registry) -> int:
    """Register all 15 media personas with the PersonaRegistry. Returns new count."""
    count = 0
    for cls in _ALL_MEDIA_PERSONAS:
        persona = cls()
        if registry.get(persona.PERSONA_ID) is None:
            registry.register(persona.profile)
            count += 1
    return count


__all__ = [
    "TikTokPersona", "InstagramPersona", "YouTubePersona", "XPersona", "ShortsPersona",
    "DocumentaryPersona", "ThumbnailPersona", "PosterPersona", "GraphicsPersona",
    "PodcastHostPersona", "PodcastProducerPersona", "SEOPersona",
    "NewsletterPersona", "WhatsAppPersona", "TelegramPersona",
    "register_media_personas",
]
