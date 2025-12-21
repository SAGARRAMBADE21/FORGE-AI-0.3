"""Unified vector store interface."""

import logging
import numpy as np

from core.types import Chunk
from config.settings import settings, VectorStoreBackend

logger = logging.getLogger(__name__)


class VectorStore:
    """Unified vector store with multiple backends."""

    def __init__(self):
        self._backend = None
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return

        backend_type = settings.vectorstore.backend

        if backend_type == VectorStoreBackend.CHROMADB:
            from vectorstore.backends.chromadb import ChromaDBBackend
            self._backend = ChromaDBBackend()
        elif backend_type == VectorStoreBackend.QDRANT:
            from vectorstore.backends.qdrant import QdrantBackend
            self._backend = QdrantBackend()
        else:
            from vectorstore.backends.memory import MemoryBackend
            self._backend = MemoryBackend()

        await self._backend.initialize()
        self._initialized = True
        logger.info(f"Vector store initialized: {backend_type.value}")

    async def add_chunks(self, chunks: list[Chunk]):
        if not self._initialized:
            await self.initialize()
        await self._backend.add_chunks(chunks)

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        if not self._initialized:
            await self.initialize()
        return await self._backend.search(query_embedding, top_k, filters)

    async def delete_file(self, file: str):
        if self._initialized:
            await self._backend.delete_file(file)

    async def delete_chunks(self, ids: list[str]):
        if self._initialized and hasattr(self._backend, 'delete_chunks'):
            await self._backend.delete_chunks(ids)

    async def clear(self):
        if self._initialized:
            await self._backend.clear()

    def count(self) -> int:
        return self._backend.count() if self._backend else 0

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        if self._backend and hasattr(self._backend, 'get_chunk'):
            return self._backend.get_chunk(chunk_id)
        return None


_store: VectorStore | None = None


def get_vectorstore() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store