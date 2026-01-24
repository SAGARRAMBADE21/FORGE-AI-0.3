"""Qdrant vector store backend."""

import logging
from typing import Any

import numpy as np

from config.settings import Language, settings
from core.types import Chunk, ChunkType, SymbolKind

logger = logging.getLogger(__name__)


class QdrantBackend:
    """Qdrant vector store backend."""

    def __init__(self):
        self._client = None
        self._collection = settings.vectorstore.collection

    async def initialize(self):
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import Distance, VectorParams

        self._client = QdrantClient(
            path=str(settings.vectorstore.persist_dir / "qdrant")
        )

        # Create collection if not exists
        collections = self._client.get_collections().collections
        exists = any(c.name == self._collection for c in collections)

        if not exists:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )

        logger.info(f"Qdrant initialized: {self._collection}")

    async def add_chunks(self, chunks: list[Chunk]):
        if not chunks:
            return

        from qdrant_client.http.models import PointStruct

        points = []
        for chunk in chunks:
            if chunk.embedding is None:
                continue

            points.append(
                PointStruct(
                    id=chunk.id,
                    vector=chunk.embedding.tolist(),
                    payload={
                        "content": chunk.content,
                        "file": chunk.file,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "chunk_type": (
                            chunk.chunk_type
                            if isinstance(chunk.chunk_type, str)
                            else chunk.chunk_type.value
                        ),
                        "symbol_id": chunk.symbol_id or "",
                        "symbol_name": chunk.symbol_name or "",
                        "symbol_kind": (
                            chunk.symbol_kind.value if chunk.symbol_kind else ""
                        ),
                        "language": (
                            chunk.language
                            if isinstance(chunk.language, str)
                            else chunk.language.value
                        ),
                        "tokens": chunk.tokens,
                        "keywords": chunk.keywords,
                    },
                )
            )

        if points:
            self._client.upsert(collection_name=self._collection, points=points)

    async def search(
        self, query_embedding: np.ndarray, top_k: int = 10, filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        query_filter = None
        if filters:
            conditions = []
            if "file" in filters:
                conditions.append(
                    FieldCondition(key="file", match=MatchValue(value=filters["file"]))
                )
            if "language" in filters:
                lang = filters["language"]
                if isinstance(lang, dict) and "$in" in lang:
                    # Qdrant doesn't support $in directly, skip for now
                    pass
                else:
                    conditions.append(
                        FieldCondition(key="language", match=MatchValue(value=lang))
                    )
            if conditions:
                query_filter = Filter(must=conditions)

        results = self._client.search(
            collection_name=self._collection,
            query_vector=query_embedding.tolist(),
            limit=top_k,
            query_filter=query_filter,
        )

        chunks_with_scores = []
        for hit in results:
            payload = hit.payload
            chunk = Chunk(
                id=hit.id,
                content=payload.get("content", ""),
                chunk_type=(
                    ChunkType(payload["chunk_type"])
                    if payload.get("chunk_type")
                    else ChunkType.CODE_BLOCK
                ),
                file=payload.get("file", ""),
                start_line=payload.get("start_line", 0),
                end_line=payload.get("end_line", 0),
                tokens=payload.get("tokens", 0),
                symbol_id=payload.get("symbol_id") or None,
                symbol_name=payload.get("symbol_name") or None,
                symbol_kind=(
                    SymbolKind(payload["symbol_kind"])
                    if payload.get("symbol_kind")
                    else None
                ),
                language=(
                    Language(payload["language"])
                    if payload.get("language")
                    else Language.UNKNOWN
                ),
                keywords=payload.get("keywords", []),
            )
            chunks_with_scores.append((chunk, hit.score))

        return chunks_with_scores

    async def delete_file(self, file: str):
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="file", match=MatchValue(value=file))]
            ),
        )

    async def clear(self):
        self._client.delete_collection(self._collection)
        from qdrant_client.http.models import Distance, VectorParams

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

    def count(self) -> int:
        try:
            info = self._client.get_collection(self._collection)
            return info.points_count
        except Exception:
            return 0
