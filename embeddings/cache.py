"""Persistent embedding cache."""

import hashlib
import numpy as np
from pathlib import Path
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Disk-based embedding cache."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or settings.embedding.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._enabled = settings.embedding.cache_enabled
        self._cache = None

        if self._enabled:
            try:
                import diskcache
                self._cache = diskcache.Cache(str(self.cache_dir / "embeddings"))
                logger.info(f"Embedding cache initialized at {self.cache_dir}")
            except ImportError:
                logger.warning("diskcache not available, using in-memory cache")
                self._cache = {}

    def _key(self, text: str, model: str = "") -> str:
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(self, text: str, model: str = "") -> np.ndarray | None:
        if not self._enabled or self._cache is None:
            return None

        key = self._key(text, model)

        if isinstance(self._cache, dict):
            return self._cache.get(key)

        try:
            result = self._cache.get(key)
            if result is not None:
                return np.frombuffer(result, dtype=np.float32)
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
        return None

    def set(self, text: str, embedding: np.ndarray, model: str = ""):
        if not self._enabled or self._cache is None:
            return

        key = self._key(text, model)

        try:
            if isinstance(self._cache, dict):
                self._cache[key] = embedding
            else:
                self._cache.set(key, embedding.tobytes())
        except Exception as e:
            logger.debug(f"Cache set error: {e}")

    def clear(self):
        if self._cache is None:
            return

        try:
            if isinstance(self._cache, dict):
                self._cache.clear()
            else:
                self._cache.clear()
        except Exception as e:
            logger.debug(f"Cache clear error: {e}")

    def stats(self) -> dict:
        if isinstance(self._cache, dict):
            return {"type": "memory", "size": len(self._cache)}
        elif self._cache:
            return {"type": "disk", "size": len(self._cache)}
        return {"type": "none", "size": 0}