from __future__ import annotations
from sfc.events.types import BaseEvent


class TikTokOpportunityDetected(BaseEvent):
    event_type: str = "tiktok_opportunity_detected"


class InstagramOpportunityDetected(BaseEvent):
    event_type: str = "instagram_opportunity_detected"


class YouTubeOpportunityDetected(BaseEvent):
    event_type: str = "youtube_opportunity_detected"


class ThreadGenerated(BaseEvent):
    event_type: str = "thread_generated"


class ThumbnailCreated(BaseEvent):
    event_type: str = "thumbnail_created"


class PosterCreated(BaseEvent):
    event_type: str = "poster_created"


class GraphicCreated(BaseEvent):
    event_type: str = "graphic_created"


class PodcastGenerated(BaseEvent):
    event_type: str = "podcast_generated"


class SEORecommendationGenerated(BaseEvent):
    event_type: str = "seo_recommendation_generated"


class NewsletterGenerated(BaseEvent):
    event_type: str = "newsletter_generated"
