"""
Smart Weather Caching System
- Reduces API calls
- Serves stale data if APIs fail
- Pre-fetches popular locations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import hashlib
import json

logger = logging.getLogger('weather_cache')


@dataclass
class CacheEntry:
    """Single cache entry"""
    data: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


class WeatherCache:
    """
    Smart caching for weather data with TTL and stale-while-revalidate.
    """

    # Default TTL in seconds
    DEFAULT_TTL = 600  # 10 minutes
    STALE_TTL = 1800   # 30 minutes (serve stale if fresh fails)

    def __init__(self, default_ttl: int = DEFAULT_TTL):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "stale_hits": 0,
            "errors_avoided": 0
        }

    def _make_key(self, prefix: str, lat: float, lon: float, **kwargs) -> str:
        """Generate cache key from location and params"""
        key_data = f"{prefix}:{lat:.4f}:{lon:.4f}"
        if kwargs:
            key_data += ":" + hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()[:8]
        return key_data

    def get(self, key: str, allow_stale: bool = True) -> Optional[Any]:
        """Get item from cache"""
        entry = self.cache.get(key)

        if entry is None:
            self.stats["misses"] += 1
            return None

        now = datetime.now()
        entry.last_accessed = now
        entry.hit_count += 1

        # Fresh data
        if now < entry.expires_at:
            self.stats["hits"] += 1
            return entry.data

        # Stale but usable
        if allow_stale and now < entry.created_at + timedelta(seconds=self.STALE_TTL):
            self.stats["stale_hits"] += 1
            logger.debug(f"Serving stale cache for {key}")
            return entry.data

        # Too old
        self.stats["misses"] += 1
        return None

    def set(self, key: str, data: Any, ttl: int = None) -> None:
        """Store item in cache"""
        ttl = ttl or self.default_ttl
        now = datetime.now()

        self.cache[key] = CacheEntry(
            data=data,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            last_accessed=now
        )

    def invalidate(self, key: str) -> None:
        """Remove item from cache"""
        self.cache.pop(key, None)

    def clear(self) -> None:
        """Clear entire cache"""
        self.cache.clear()

    def cleanup(self) -> int:
        """Remove expired entries, return count removed"""
        now = datetime.now()
        stale_threshold = now - timedelta(seconds=self.STALE_TTL)

        expired = [k for k, v in self.cache.items() if v.created_at < stale_threshold]
        for key in expired:
            del self.cache[key]

        return len(expired)

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"] + self.stats["stale_hits"]
        hit_rate = (self.stats["hits"] + self.stats["stale_hits"]) / max(1, total_requests)

        return {
            **self.stats,
            "total_entries": len(self.cache),
            "hit_rate": round(hit_rate, 2),
            "memory_entries": len(self.cache)
        }

    async def get_or_fetch(self, key: str, fetch_func: Callable, ttl: int = None) -> Any:
        """Get from cache or fetch if missing"""
        # Try cache first
        cached = self.get(key, allow_stale=False)
        if cached is not None:
            return cached

        # Try to fetch fresh data
        try:
            data = await fetch_func()
            if data:
                self.set(key, data, ttl)
            return data
        except Exception as e:
            logger.warning(f"Fetch failed for {key}: {e}")

            # Try stale cache as fallback
            stale = self.get(key, allow_stale=True)
            if stale is not None:
                self.stats["errors_avoided"] += 1
                logger.info(f"Serving stale cache after fetch error for {key}")
                return stale

            raise


# Popular locations to pre-fetch
PREFETCH_LOCATIONS = [
    {"name": "Tel Aviv", "lat": 32.0853, "lon": 34.7818},
    {"name": "Jerusalem", "lat": 31.7683, "lon": 35.2137},
    {"name": "Haifa", "lat": 32.7940, "lon": 34.9896},
    {"name": "Eilat", "lat": 29.5577, "lon": 34.9519},
]


# Global cache instance
weather_cache = WeatherCache()
