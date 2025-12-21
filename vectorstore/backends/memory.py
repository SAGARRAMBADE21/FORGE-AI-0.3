"""In-memory vector store backend."""

import numpy as np
import logging
from typing import Any

from core.types import Chunk, ChunkType, SymbolKind, CrossFileContext
from config.settings import Language

logger = logging.getLogger(__name__)


class MemoryBackend:
    """Simple in-memory vector store."""

    def __init__(self):
        self._chunks: dict[str, Chunk] = {}
        self._embeddings: np.ndarray | None = None
        self._ids: list[str] = []

    async def initialize(self):
        logger.info("Initialized in-memory vector store")

    async def add_chunks(self, chunks: list[Chunk]):
        if not chunks:
            return

        for chunk in chunks:
            if chunk.embedding is not None:
                self._chunks[chunk.id] = chunk

        self._rebuild_index()
        logger.debug(f"Added {len(chunks)} chunks, total: {len(self._chunks)}")

    def _rebuild_index(self):
        if not self._chunks:
            self._embeddings = None
            self._ids = []
            return

        self._ids = []
        embeddings = []

        for chunk_id, chunk in self._chunks.items():
            if chunk.embedding is not None:
                self._ids.append(chunk_id)
                embeddings.append(chunk.embedding)

        if embeddings:
            self._embeddings = np.stack(embeddings)
        else:
            self._embeddings = None

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        if self._embeddings is None or len(self._ids) == 0:
            return []

        # Normalize query
        query = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # Normalize embeddings
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True) + 1e-8
        normalized = self._embeddings / norms

        # Compute cosine similarities
        similarities = np.dot(normalized, query)

        # Apply filters
        valid_indices = list(range(len(self._ids)))
        if filters:
            valid_indices = [
                i for i in valid_indices
                if self._matches_filter(self._chunks[self._ids[i]], filters)
            ]

        if not valid_indices:
            return []

        # Get top-k
        valid_sims = [(i, similarities[i]) for i in valid_indices]
        valid_sims.sort(key=lambda x: -x[1])
        top_indices = valid_sims[:top_k]

        results = []
        for idx, score in top_indices:
            chunk = self._chunks[self._ids[idx]]
            results.append((chunk, float(score)))

        return results

    def _matches_filter(self, chunk: Chunk, filters: dict) -> bool:
        for key, value in filters.items():
            chunk_value = getattr(chunk, key, None)
            if chunk_value is None:
                return False

            if isinstance(value, dict):
                if "$in" in value:
                    if hasattr(chunk_value, 'value'):
                        chunk_value = chunk_value.value
                    if chunk_value not in value["$in"]:
                        return False
            else:
                if hasattr(chunk_value, 'value'):
                    chunk_value = chunk_value.value
                if chunk_value != value:
                    return False
        return True

    async def delete_file(self, file: str):
        to_delete = [cid for cid, c in self._chunks.items() if c.file == file]
        for cid in to_delete:
            del self._chunks[cid]
        self._rebuild_index()

    async def delete_chunks(self, ids: list[str]):
        for cid in ids:
            self._chunks.pop(cid, None)
        self._rebuild_index()

    async def clear(self):
        self._chunks.clear()
        self._embeddings = None
        self._ids = []

    def count(self) -> int:
        return len(self._chunks)

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        return self._chunks.get(chunk_id)