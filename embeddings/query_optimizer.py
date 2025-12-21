"""Query optimization for embeddings."""

import re
from config.settings import settings


class QueryOptimizer:
    """Optimize queries for better retrieval."""

    def __init__(self):
        self.query_prefix = settings.embedding.query_prefix
        self.doc_prefix = settings.embedding.doc_prefix

    def optimize_query(self, query: str) -> str:
        """Optimize a search query."""
        # Add query prefix for asymmetric search
        optimized = f"{self.query_prefix}{query}"
        return optimized

    def optimize_document(self, text: str) -> str:
        """Optimize a document for indexing."""
        if self.doc_prefix:
            return f"{self.doc_prefix}{text}"
        return text

    def expand_query(self, query: str) -> list[str]:
        """Expand query with synonyms and variations."""
        queries = [query]

        # Extract identifiers and create variations
        identifiers = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', query)

        for ident in identifiers:
            # camelCase to space-separated
            spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', ident)
            if spaced != ident:
                queries.append(query.replace(ident, spaced))

            # snake_case to space-separated
            if '_' in ident:
                spaced = ident.replace('_', ' ')
                queries.append(query.replace(ident, spaced))

        return list(set(queries))[:3]  # Limit to 3 variations