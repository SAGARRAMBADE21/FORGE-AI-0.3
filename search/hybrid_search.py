"""Hybrid search combining semantic and keyword search."""

import re
import time
import logging
from collections import defaultdict

from core.types import Chunk, SearchQuery, SearchResult, SearchResponse
from search.semantic_search import SemanticSearch
from search.reranker import Reranker
from search.boost_functions import apply_boosts
from config.settings import settings

logger = logging.getLogger(__name__)


class HybridSearch:
    """Hybrid semantic + keyword search with reranking."""

    def __init__(self):
        self._semantic = SemanticSearch()
        self._reranker = Reranker() if settings.search.rerank else None

        # Keyword index
        self._keyword_index: dict[str, set[str]] = defaultdict(set)
        self._chunks: dict[str, Chunk] = {}

    def index_chunks(self, chunks: list[Chunk]):
        """Build keyword index for BM25-style search."""
        for chunk in chunks:
            self._chunks[chunk.id] = chunk

            # Extract words from content
            words = set(re.findall(r'\w+', chunk.content.lower()))
            words.update(w.lower() for w in chunk.keywords)

            # Add symbol name
            if chunk.symbol_name:
                words.add(chunk.symbol_name.lower())
                # Also add camelCase parts
                parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)', chunk.symbol_name)
                words.update(p.lower() for p in parts)

            for word in words:
                if len(word) > 2:
                    self._keyword_index[word].add(chunk.id)

    def clear_index(self):
        """Clear keyword index."""
        self._keyword_index.clear()
        self._chunks.clear()

    async def search(self, query: SearchQuery) -> SearchResponse:
        start = time.time()
        alpha = settings.search.hybrid_alpha

        # Semantic search
        semantic_resp = await self._semantic.search(SearchQuery(
            query=query.query,
            top_k=settings.search.retrieval_k,
            file_filter=query.file_filter,
            language_filter=query.language_filter,
            threshold=0.3  # Lower threshold for initial retrieval
        ))
        semantic_scores = {r.chunk.id: r.score for r in semantic_resp.results}

        # Keyword search
        keyword_scores = self._keyword_search(query.query)

        # Combine scores
        all_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())
        combined = {}

        for chunk_id in all_ids:
            sem = semantic_scores.get(chunk_id, 0)
            key = keyword_scores.get(chunk_id, 0)
            combined[chunk_id] = alpha * sem + (1 - alpha) * key

        # Build results
        results = []
        for chunk_id in sorted(combined.keys(), key=lambda x: -combined[x]):
            chunk = self._chunks.get(chunk_id)
            if chunk:
                results.append(SearchResult(
                    chunk=chunk,
                    score=combined[chunk_id]
                ))

        # Apply boosts
        results = apply_boosts(results, query)

        # Rerank if enabled
        if self._reranker and len(results) > query.top_k:
            results = await self._reranker.rerank(
                query.query,
                results,
                top_k=settings.search.rerank_k
            )

        results = results[:query.top_k]

        return SearchResponse(
            query=query.query,
            results=results,
            total_count=len(results),
            search_time_ms=(time.time() - start) * 1000
        )

    def _keyword_search(self, query: str) -> dict[str, float]:
        """BM25-style keyword search."""
        words = re.findall(r'\w+', query.lower())
        scores: dict[str, float] = {}

        for word in words:
            if word in self._keyword_index:
                matches = self._keyword_index[word]
                # IDF-like weight
                idf = 1.0 / (1.0 + len(matches))

                for chunk_id in matches:
                    if chunk_id not in scores:
                        scores[chunk_id] = 0

                    chunk = self._chunks.get(chunk_id)
                    if chunk:
                        # TF-like score
                        tf = chunk.content.lower().count(word)
                        scores[chunk_id] += tf * idf

        # Normalize
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: v / max_score for k, v in scores.items()}

        return scores