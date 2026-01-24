# generation/cache_manager.py
"""
LLM Response Cache Manager - Caches LLM responses to reduce API costs and latency.
"""

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached LLM response entry."""

    response: str
    model: str
    provider: str
    timestamp: float
    token_count: int = 0

    def is_expired(self, ttl_hours: float = 24.0) -> bool:
        """Check if cache entry has expired."""
        age_hours = (time.time() - self.timestamp) / 3600
        return age_hours > ttl_hours


class LLMResponseCache:
    """
    Disk-based cache for LLM responses.

    Reduces API costs by caching identical or similar prompts.
    Uses content-based hashing for cache keys.
    """

    def __init__(self, cache_dir: Path | None = None, ttl_hours: float = 24.0):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory for cache storage
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.cache_dir = cache_dir or Path.home() / ".code_indexer" / "llm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._enabled = True

        # Statistics
        self.hits = 0
        self.misses = 0

        logger.info(f"LLM cache initialized at {self.cache_dir}")

    def _generate_key(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        provider: str,
        temperature: float,
    ) -> str:
        """Generate a unique cache key from prompt content."""
        content = json.dumps(
            {
                "system": system_prompt,
                "user": user_prompt,
                "model": model,
                "provider": provider,
                "temperature": temperature,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for a cache key."""
        # Use first 2 chars as subdirectory for better file distribution
        subdir = self.cache_dir / key[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key}.json"

    def get(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        provider: str,
        temperature: float = 0.1,
    ) -> Optional[str]:
        """
        Retrieve cached response if available.

        Args:
            system_prompt: System prompt used
            user_prompt: User prompt used
            model: Model name
            provider: Provider name
            temperature: Temperature setting

        Returns:
            Cached response string or None if not found/expired
        """
        if not self._enabled:
            return None

        # Skip cache for high-temperature requests (non-deterministic)
        if temperature > 0.5:
            return None

        key = self._generate_key(
            system_prompt, user_prompt, model, provider, temperature
        )

        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired(self.ttl_hours):
                self.hits += 1
                logger.debug(f"Cache hit (memory): {key[:8]}...")
                return entry.response
            else:
                del self._memory_cache[key]

        # Check disk cache
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                entry = CacheEntry(**data)

                if not entry.is_expired(self.ttl_hours):
                    # Promote to memory cache
                    self._memory_cache[key] = entry
                    self.hits += 1
                    logger.debug(f"Cache hit (disk): {key[:8]}...")
                    return entry.response
                else:
                    # Clean up expired entry
                    cache_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")

        self.misses += 1
        return None

    def set(
        self,
        system_prompt: str,
        user_prompt: str,
        response: str,
        model: str,
        provider: str,
        temperature: float = 0.1,
        token_count: int = 0,
    ):
        """
        Store a response in the cache.

        Args:
            system_prompt: System prompt used
            user_prompt: User prompt used
            response: LLM response to cache
            model: Model name
            provider: Provider name
            temperature: Temperature setting
            token_count: Number of tokens used
        """
        if not self._enabled:
            return

        # Don't cache high-temperature responses
        if temperature > 0.5:
            return

        key = self._generate_key(
            system_prompt, user_prompt, model, provider, temperature
        )

        entry = CacheEntry(
            response=response,
            model=model,
            provider=provider,
            timestamp=time.time(),
            token_count=token_count,
        )

        # Store in memory
        self._memory_cache[key] = entry

        # Store on disk
        cache_path = self._get_cache_path(key)
        try:
            cache_path.write_text(json.dumps(asdict(entry), indent=2))
            logger.debug(f"Cached response: {key[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    def clear(self):
        """Clear all cached entries."""
        self._memory_cache.clear()

        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for file in subdir.glob("*.json"):
                    try:
                        file.unlink()
                    except Exception:
                        pass

        logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        removed = 0

        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for file in subdir.glob("*.json"):
                    try:
                        data = json.loads(file.read_text())
                        entry = CacheEntry(**data)
                        if entry.is_expired(self.ttl_hours):
                            file.unlink()
                            removed += 1
                    except Exception:
                        pass

        # Clean memory cache
        expired_keys = [
            k for k, v in self._memory_cache.items() if v.is_expired(self.ttl_hours)
        ]
        for key in expired_keys:
            del self._memory_cache[key]
            removed += 1

        logger.info(f"Cleaned up {removed} expired cache entries")
        return removed

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        disk_size = sum(
            f.stat().st_size
            for subdir in self.cache_dir.iterdir()
            if subdir.is_dir()
            for f in subdir.glob("*.json")
        )

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "memory_entries": len(self._memory_cache),
            "disk_size_mb": f"{disk_size / 1024 / 1024:.2f}",
            "enabled": self._enabled,
        }

    def enable(self):
        """Enable caching."""
        self._enabled = True

    def disable(self):
        """Disable caching."""
        self._enabled = False


# Global cache instance
_cache_instance: Optional[LLMResponseCache] = None


def get_cache() -> LLMResponseCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMResponseCache()
    return _cache_instance
