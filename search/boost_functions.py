"""Boost functions for search result scoring."""

import re
from datetime import datetime, timedelta

from core.types import SearchResult, SearchQuery, ChunkType
from config.settings import settings


def apply_boosts(results: list[SearchResult], query: SearchQuery) -> list[SearchResult]:
    """Apply various boosts to search results."""
    query_lower = query.query.lower()
    query_words = set(re.findall(r'\w+', query_lower))

    for result in results:
        boost = 1.0
        chunk = result.chunk

        # Path match boost
        if query_lower in chunk.file.lower():
            boost *= (1 + settings.search.path_boost)

        # Symbol name match boost
        if chunk.symbol_name:
            symbol_lower = chunk.symbol_name.lower()
            if query_lower in symbol_lower:
                boost *= (1 + settings.search.symbol_boost)
            elif any(w in symbol_lower for w in query_words):
                boost *= (1 + settings.search.symbol_boost * 0.5)

        # Function/class boost (more important than random code)
        important_types = {ChunkType.FUNCTION, ChunkType.CLASS, ChunkType.METHOD, ChunkType.COMPONENT}
        if chunk.chunk_type in important_types:
            boost *= 1.1

        # Exported symbols boost
        if chunk.symbol_kind and chunk.symbol_name:
            # Assume capitalized names are likely exported/public
            if chunk.symbol_name[0].isupper():
                boost *= 1.05

        # Recency boost (if we have created_at)
        if hasattr(chunk, 'created_at') and chunk.created_at:
            age_days = (datetime.utcnow() - chunk.created_at).days
            recency_factor = max(0.8, 1.0 - age_days * 0.002)  # Decay over time
            boost *= (1 + settings.search.recency_boost * (recency_factor - 0.8))

        # Keyword density boost
        content_lower = chunk.content.lower()
        keyword_hits = sum(1 for w in query_words if w in content_lower)
        if keyword_hits > 0:
            density_boost = min(0.2, keyword_hits * 0.05)
            boost *= (1 + density_boost)

        result.score *= boost

    # Sort by boosted scores
    results.sort(key=lambda x: -x.score)

    return results


def compute_bm25_score(query_words: set[str], content: str, avg_doc_length: float = 500) -> float:
    """Compute BM25-like score."""
    k1 = 1.5
    b = 0.75

    content_lower = content.lower()
    doc_length = len(content)

    score = 0.0
    for word in query_words:
        tf = content_lower.count(word)
        if tf > 0:
            # Simplified BM25
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_length / avg_doc_length)
            score += numerator / denominator

    return score