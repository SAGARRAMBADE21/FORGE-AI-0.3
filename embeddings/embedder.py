"""Unified embedder with caching and query optimization."""

import asyncio
import logging

import numpy as np

from config.settings import EmbeddingProvider, settings
from core.types import Chunk
from embeddings.cache import EmbeddingCache
from embeddings.query_optimizer import QueryOptimizer

logger = logging.getLogger(__name__)


class Embedder:
    """
    Unified embedder with:
    - Multiple providers (OpenAI, Voyage, Local)
    - Persistent caching
    - Query vs document optimization
    - Batch processing
    """

    def __init__(self):
        self._provider = None
        self._cache = EmbeddingCache()
        self._optimizer = QueryOptimizer()
        self._dimensions: int | None = None

    @property
    def provider(self):
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    @property
    def dimensions(self) -> int:
        if self._dimensions is None:
            self._dimensions = self.provider.dimensions
        return self._dimensions

    def _create_provider(self):
        provider_type = settings.embedding.provider

        if provider_type == EmbeddingProvider.OPENAI:
            from embeddings.providers.openai import OpenAIEmbedder

            return OpenAIEmbedder()
        elif provider_type == EmbeddingProvider.VOYAGE:
            from embeddings.providers.voyage import VoyageEmbedder

            return VoyageEmbedder()
        else:
            raise ValueError(f"Unknown embedding provider: {provider_type}. Supported: OPENAI, VOYAGE")

    async def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Embed chunks with caching."""
        if not chunks:
            return chunks

        texts = []
        indices = []
        model = getattr(self.provider, "model", "unknown")

        for i, chunk in enumerate(chunks):
            text = chunk.to_embedding_text()
            cached = self._cache.get(text, model)

            if cached is not None:
                chunk.embedding = cached
            else:
                texts.append(self._optimizer.optimize_document(text))
                indices.append(i)

        if texts:
            cached_count = len(chunks) - len(texts)
            logger.info(f"Embedding {len(texts)} chunks (cached: {cached_count})")

            embeddings = await self._batch_embed(texts)

            for idx, text, emb in zip(indices, texts, embeddings):
                original_text = chunks[idx].to_embedding_text()
                chunks[idx].embedding = emb
                self._cache.set(original_text, emb, model)

        return chunks

    async def embed_query(self, query: str) -> np.ndarray:
        """Embed a search query with optimization."""
        optimized = self._optimizer.optimize_query(query)

        # For Voyage, use query-specific embedding
        if hasattr(self.provider, "embed_query"):
            return await self.provider.embed_query(query)

        return await self.provider.embed_text(optimized)

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text."""
        model = getattr(self.provider, "model", "unknown")
        cached = self._cache.get(text, model)
        if cached is not None:
            return cached

        emb = await self.provider.embed_text(text)
        self._cache.set(text, emb, model)
        return emb

    async def _batch_embed(self, texts: list[str]) -> list[np.ndarray]:
        """Batch embed texts."""
        batch_size = settings.embedding.batch_size
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await self.provider.embed_texts(batch)
            all_embeddings.extend(embeddings)

            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)  # Rate limiting

        return all_embeddings


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
