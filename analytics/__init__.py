"""analytics — Game analytics and data collection package."""
from analytics.collector import (
    AnalyticsCollector, GameAnalytics, MoveDataPoint, MoveQuality
)

__all__ = [
    "AnalyticsCollector", "GameAnalytics",
    "MoveDataPoint", "MoveQuality",
]
