"""Semantic search implementation."""

import logging
import time

import numpy as np

from config.settings import settings
from core.types import Chunk, SearchQuery, SearchResponse, SearchResult
from embeddings.embedder import get_embedder
from vectorstore.store import get_vectorstore

logger = logging.getLogger(__name__)


class SemanticSearch:
    """Pure semantic search over code chunks."""

    def __init__(self):
        self._embedder = get_embedder()
        self._store = get_vectorstore()

    async def search(self, query: SearchQuery) -> SearchResponse:
        start = time.time()

        # Embed query
        query_emb = await self._embedder.embed_query(query.query)

        # Build filters
        filters = {}
        if query.file_filter:
            filters["file"] = {"$in": query.file_filter}
        if query.language_filter:
            filters["language"] = {"$in": [l.value for l in query.language_filter]}
        if query.symbol_kind_filter:
            filters["symbol_kind"] = {
                "$in": [sk.value for sk in query.symbol_kind_filter]
            }

        # Search
        results = await self._store.search(
            query_emb,
            top_k=query.top_k * 2,  # Get more for filtering
            filters=filters if filters else None,
        )

        # Filter by threshold and build results
        search_results = []
        for chunk, score in results:
            if score >= query.threshold:
                search_results.append(SearchResult(chunk=chunk, score=score))

        search_results = search_results[: query.top_k]

        return SearchResponse(
            query=query.query,
            results=search_results,
            total_count=len(search_results),
            search_time_ms=(time.time() - start) * 1000,
        )

    async def search_similar(self, chunk: Chunk, top_k: int = 5) -> list[SearchResult]:
        """Find chunks similar to a given chunk."""
        if chunk.embedding is None:
            return []

        results = await self._store.search(chunk.embedding, top_k + 1)

        # Filter out the source chunk
        return [
            SearchResult(chunk=c, score=s, match_type="similar")
            for c, s in results
            if c.id != chunk.id
        ][:top_k]
