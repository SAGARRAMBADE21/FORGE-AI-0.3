"""ChromaDB vector store backend."""

import logging

import numpy as np

from config.settings import Language, settings
from core.types import Chunk, ChunkType, CrossFileContext, SymbolKind

logger = logging.getLogger(__name__)


class ChromaDBBackend:
    """ChromaDB vector store backend."""

    def __init__(self):
        self._client = None
        self._collection = None

    async def initialize(self):
        import chromadb
        from chromadb.config import Settings

        persist_dir = settings.vectorstore.persist_dir
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(persist_dir), settings=Settings(anonymized_telemetry=False)
        )

        self._collection = self._client.get_or_create_collection(
            name=settings.vectorstore.collection, metadata={"hnsw:space": "cosine"}
        )

        logger.info(f"ChromaDB initialized with {self.count()} chunks")

    async def add_chunks(self, chunks: list[Chunk]):
        if not chunks:
            return

        valid_chunks = [c for c in chunks if c.embedding is not None]
        if not valid_chunks:
            return

        ids = [c.id for c in valid_chunks]
        documents = [c.content for c in valid_chunks]
        embeddings = [c.embedding.tolist() for c in valid_chunks]

        metadatas = []
        for c in valid_chunks:
            metadatas.append(
                {
                    "file": c.file,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "chunk_type": (
                        c.chunk_type
                        if isinstance(c.chunk_type, str)
                        else c.chunk_type.value
                    ),
                    "symbol_id": c.symbol_id or "",
                    "symbol_name": c.symbol_name or "",
                    "symbol_kind": c.symbol_kind.value if c.symbol_kind else "",
                    "language": (
                        c.language if isinstance(c.language, str) else c.language.value
                    ),
                    "tokens": c.tokens,
                    "parent_context": c.parent_context,
                    "keywords": ",".join(c.keywords[:20]),
                }
            )

        # Add in batches
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            self._collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
            )

        logger.debug(f"Added {len(valid_chunks)} chunks to ChromaDB")

    async def search(
        self, query_embedding: np.ndarray, top_k: int = 10, filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        where = None
        if filters:
            where = {}
            if "file" in filters:
                where["file"] = filters["file"]
            if "language" in filters:
                if (
                    isinstance(filters["language"], dict)
                    and "$in" in filters["language"]
                ):
                    where["language"] = {"$in": filters["language"]["$in"]}
                else:
                    where["language"] = filters["language"]
            if "chunk_type" in filters:
                where["chunk_type"] = filters["chunk_type"]

        results = self._collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )

        chunks_with_scores = []

        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                doc = results["documents"][0][i]
                dist = results["distances"][0][i]
                score = 1 - dist  # Convert distance to similarity

                chunk = Chunk(
                    id=chunk_id,
                    content=doc,
                    chunk_type=meta.get("chunk_type", "code"),
                    file=meta.get("file", ""),
                    start_line=meta.get("start_line", 0),
                    end_line=meta.get("end_line", 0),
                    language=meta.get("language", "unknown"),
                    metadata={
                        "tokens": meta.get("tokens", 0),
                        "symbol_id": meta.get("symbol_id"),
                        "symbol_name": meta.get("symbol_name"),
                        "symbol_kind": meta.get("symbol_kind"),
                        "parent_context": meta.get("parent_context", ""),
                        "keywords": (
                            meta.get("keywords", "").split(",")
                            if meta.get("keywords")
                            else []
                        ),
                    },
                )

                chunks_with_scores.append((chunk, score))

        return chunks_with_scores

    async def delete_file(self, file: str):
        try:
            self._collection.delete(where={"file": file})
        except Exception as e:
            logger.debug(f"Delete file error: {e}")

    async def delete_chunks(self, ids: list[str]):
        if ids:
            try:
                self._collection.delete(ids=ids)
            except Exception as e:
                logger.debug(f"Delete chunks error: {e}")

    async def clear(self):
        try:
            self._client.delete_collection(settings.vectorstore.collection)
            self._collection = self._client.create_collection(
                name=settings.vectorstore.collection, metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Clear error: {e}")

    def count(self) -> int:
        try:
            return self._collection.count() if self._collection else 0
        except Exception:
            return 0

    async def get_all_chunks(self) -> list[Chunk]:
        """Get all chunks from ChromaDB."""
        try:
            # Get all chunks in batches
            all_chunks = []
            batch_size = 1000
            offset = 0

            while True:
                result = self._collection.get(
                    limit=batch_size,
                    offset=offset,
                    include=["documents", "metadatas", "embeddings"],
                )

                if not result or "ids" not in result or len(result["ids"]) == 0:
                    break

                for i, chunk_id in enumerate(result["ids"]):
                    try:
                        meta = (
                            result["metadatas"][i]
                            if i < len(result["metadatas"])
                            else {}
                        )
                        doc = (
                            result["documents"][i]
                            if i < len(result["documents"])
                            else ""
                        )
                        emb_list = (
                            result["embeddings"][i]
                            if result.get("embeddings")
                            and i < len(result["embeddings"])
                            else None
                        )

                        chunk = Chunk(
                            id=chunk_id,
                            content=doc,
                            chunk_type=meta.get("chunk_type", "code"),
                            file=meta.get("file", ""),
                            start_line=meta.get("start_line", 0),
                            end_line=meta.get("end_line", 0),
                            language=meta.get("language", "unknown"),
                            tokens=meta.get("tokens", 0),
                            embedding=(
                                np.array(emb_list, dtype=np.float32)
                                if emb_list is not None and len(emb_list) > 0
                                else None
                            ),
                            metadata={
                                "symbol_id": meta.get("symbol_id", ""),
                                "symbol_name": meta.get("symbol_name", ""),
                                "symbol_kind": meta.get("symbol_kind", ""),
                                "parent_context": meta.get("parent_context", ""),
                                "keywords": (
                                    meta.get("keywords", "").split(",")
                                    if meta.get("keywords")
                                    else []
                                ),
                            },
                        )
                        all_chunks.append(chunk)
                    except Exception as e:
                        logger.debug(f"Error processing chunk {chunk_id}: {e}")
                        continue

                if len(result["ids"]) < batch_size:
                    break

                offset += batch_size

            logger.info(f"Loaded {len(all_chunks)} chunks from ChromaDB")
            return all_chunks
        except Exception as e:
            logger.error(f"Error loading chunks: {e}", exc_info=True)
            return []

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        try:
            result = self._collection.get(
                ids=[chunk_id], include=["documents", "metadatas"]
            )
            if result["ids"]:
                meta = result["metadatas"][0]
                doc = result["documents"][0]
                return Chunk(
                    id=chunk_id,
                    content=doc,
                    chunk_type=(
                        ChunkType(meta["chunk_type"])
                        if meta.get("chunk_type")
                        else ChunkType.CODE_BLOCK
                    ),
                    file=meta.get("file", ""),
                    start_line=meta.get("start_line", 0),
                    end_line=meta.get("end_line", 0),
                    tokens=meta.get("tokens", 0),
                    language=(
                        Language(meta["language"])
                        if meta.get("language")
                        else Language.UNKNOWN
                    ),
                )
        except Exception:
            pass
        return None
