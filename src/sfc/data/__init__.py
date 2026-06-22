"""Package 10A — Real Data Layer for SFC intelligence services."""

from sfc.data.models import DataBatch, DataPoint, IngestionResult
from sfc.data.confidence import SourceConfidenceScorer
from sfc.data.freshness import DataFreshnessScorer
from sfc.data.deduplication import ContentDeduplicator
from sfc.data.normalizer import DataNormalizer
from sfc.data.cache import DataCache

__all__ = [
    "DataPoint",
    "DataBatch",
    "IngestionResult",
    "SourceConfidenceScorer",
    "DataFreshnessScorer",
    "ContentDeduplicator",
    "DataNormalizer",
    "DataCache",
]
