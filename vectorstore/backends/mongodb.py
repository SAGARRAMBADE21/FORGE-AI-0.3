"""MongoDB Atlas Vector Search backend."""

import logging
import numpy as np
from typing import Any

from core.types import Chunk, ChunkType, SymbolKind
from config.settings import settings, Language

logger = logging.getLogger(__name__)


class MongoDBBackend:
    """MongoDB Atlas Vector Search backend."""

    def __init__(self):
        self._client = None
        self._db = None
        self._collection = None
        self._initialized = False

    async def initialize(self):
        """Initialize MongoDB connection and ensure vector search index exists."""
        if self._initialized:
            return

        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError:
            raise ImportError(
                "motor package is required for MongoDB backend. "
                "Install it with: pip install motor pymongo"
            )

        mongodb_uri = settings.vectorstore.mongodb_uri
        if not mongodb_uri:
            raise ValueError(
                "MongoDB URI not configured. Set MONGODB_URI environment variable."
            )

        # Create async MongoDB client
        self._client = AsyncIOMotorClient(mongodb_uri)
        
        # Get database and collection
        db_name = settings.vectorstore.mongodb_database
        collection_name = settings.vectorstore.mongodb_collection
        
        self._db = self._client[db_name]
        self._collection = self._db[collection_name]

        # Test connection
        try:
            await self._client.admin.command('ping')
            logger.info(f"MongoDB Atlas connected: {db_name}.{collection_name}")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise

        # Create indexes
        await self._ensure_indexes()

        count = await self.count()
        logger.info(f"MongoDB Atlas initialized with {count} chunks")
        self._initialized = True

    async def _ensure_indexes(self):
        """Ensure necessary indexes exist."""
        # Create text index for basic search fallback
        try:
            await self._collection.create_index([("file", 1)])
            await self._collection.create_index([("language", 1)])
            await self._collection.create_index([("chunk_type", 1)])
        except Exception as e:
            logger.debug(f"Index creation warning: {e}")

        # Note: Vector Search index must be created via Atlas UI or MongoDB CLI
        # The index should be created on the 'embedding' field with the following config:
        # {
        #   "fields": [{
        #     "type": "vector",
        #     "path": "embedding",
        #     "numDimensions": 768,  // GraphCodeBERT dimensions
        #     "similarity": "cosine"
        #   }]
        # }
        logger.info(
            f"Ensure vector search index '{settings.vectorstore.mongodb_index}' "
            f"exists on 'embedding' field in Atlas UI"
        )

    async def add_chunks(self, chunks: list[Chunk]):
        """Add chunks to MongoDB collection."""
        if not chunks:
            return

        valid_chunks = [c for c in chunks if c.embedding is not None]
        if not valid_chunks:
            return

        # Prepare documents
        documents = []
        for chunk in valid_chunks:
            doc = {
                "_id": chunk.id,
                "content": chunk.content,
                "embedding": chunk.embedding.tolist(),
                "file": chunk.file,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_type": chunk.chunk_type if isinstance(chunk.chunk_type, str) else chunk.chunk_type.value,
                "symbol_id": chunk.symbol_id or "",
                "symbol_name": chunk.symbol_name or "",
                "symbol_kind": chunk.symbol_kind.value if chunk.symbol_kind else "",
                "language": chunk.language if isinstance(chunk.language, str) else chunk.language.value,
                "tokens": chunk.tokens,
                "parent_context": chunk.parent_context or "",
                "keywords": chunk.keywords[:20] if chunk.keywords else [],
            }
            documents.append(doc)

        # Insert in batches to avoid memory issues
        batch_size = 500
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                # Use replace_one with upsert to handle duplicates
                for doc in batch:
                    await self._collection.replace_one(
                        {"_id": doc["_id"]},
                        doc,
                        upsert=True
                    )
            except Exception as e:
                logger.error(f"Error inserting batch: {e}")
                # Try individual inserts for failed batch
                for doc in batch:
                    try:
                        await self._collection.replace_one(
                            {"_id": doc["_id"]},
                            doc,
                            upsert=True
                        )
                    except Exception as e2:
                        logger.error(f"Error inserting chunk {doc['_id']}: {e2}")

        logger.debug(f"Added {len(valid_chunks)} chunks to MongoDB")

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        """Search using MongoDB Atlas Vector Search."""
        
        # Build the vector search pipeline
        pipeline = []

        # Vector search stage
        vector_search = {
            "$vectorSearch": {
                "index": settings.vectorstore.mongodb_index,
                "path": "embedding",
                "queryVector": query_embedding.tolist(),
                "numCandidates": top_k * 10,  # Overrequest for better results
                "limit": top_k
            }
        }

        # Add filters if provided
        if filters:
            filter_conditions = []
            
            if "file" in filters:
                filter_conditions.append({"file": filters["file"]})
            
            if "language" in filters:
                if isinstance(filters["language"], dict) and "$in" in filters["language"]:
                    filter_conditions.append({"language": {"$in": filters["language"]["$in"]}})
                else:
                    filter_conditions.append({"language": filters["language"]})
            
            if "chunk_type" in filters:
                filter_conditions.append({"chunk_type": filters["chunk_type"]})
            
            if filter_conditions:
                vector_search["$vectorSearch"]["filter"] = {
                    "$and": filter_conditions
                } if len(filter_conditions) > 1 else filter_conditions[0]

        pipeline.append(vector_search)

        # Add score projection
        pipeline.append({
            "$project": {
                "_id": 1,
                "content": 1,
                "file": 1,
                "start_line": 1,
                "end_line": 1,
                "chunk_type": 1,
                "symbol_id": 1,
                "symbol_name": 1,
                "symbol_kind": 1,
                "language": 1,
                "tokens": 1,
                "parent_context": 1,
                "keywords": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        })

        # Execute search
        try:
            cursor = self._collection.aggregate(pipeline)
            results = await cursor.to_list(length=top_k)
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            logger.info("Falling back to empty results. Ensure vector index is created in Atlas.")
            return []

        # Convert to chunks
        chunks_with_scores = []
        for result in results:
            chunk = Chunk(
                id=str(result["_id"]),
                content=result.get("content", ""),
                chunk_type=result.get("chunk_type", "code"),
                file=result.get("file", ""),
                start_line=result.get("start_line", 0),
                end_line=result.get("end_line", 0),
                language=result.get("language", "unknown"),
                metadata={
                    "tokens": result.get("tokens", 0),
                    "symbol_id": result.get("symbol_id"),
                    "symbol_name": result.get("symbol_name"),
                    "symbol_kind": result.get("symbol_kind"),
                    "parent_context": result.get("parent_context", ""),
                    "keywords": result.get("keywords", [])
                }
            )
            
            score = result.get("score", 0.0)
            chunks_with_scores.append((chunk, score))

        return chunks_with_scores

    async def delete_file(self, file: str):
        """Delete all chunks from a specific file."""
        try:
            result = await self._collection.delete_many({"file": file})
            logger.debug(f"Deleted {result.deleted_count} chunks from {file}")
        except Exception as e:
            logger.debug(f"Delete file error: {e}")

    async def delete_chunks(self, ids: list[str]):
        """Delete specific chunks by ID."""
        if not ids:
            return
        
        try:
            result = await self._collection.delete_many({"_id": {"$in": ids}})
            logger.debug(f"Deleted {result.deleted_count} chunks")
        except Exception as e:
            logger.debug(f"Delete chunks error: {e}")

    async def clear(self):
        """Clear all chunks from the collection."""
        try:
            result = await self._collection.delete_many({})
            logger.info(f"Cleared {result.deleted_count} chunks from MongoDB")
        except Exception as e:
            logger.error(f"Clear error: {e}")

    async def count(self) -> int:
        """Get the total number of chunks."""
        try:
            return await self._collection.count_documents({})
        except Exception:
            return 0

    def count_sync(self) -> int:
        """Synchronous count for compatibility."""
        # This is a fallback that won't work in async context
        # We need to return 0 and let async count handle it
        return 0

    async def get_chunk(self, chunk_id: str) -> Chunk | None:
        """Get a specific chunk by ID."""
        try:
            doc = await self._collection.find_one({"_id": chunk_id})
            if doc:
                return Chunk(
                    id=str(doc["_id"]),
                    content=doc.get("content", ""),
                    chunk_type=ChunkType(doc["chunk_type"]) if doc.get("chunk_type") else ChunkType.CODE_BLOCK,
                    file=doc.get("file", ""),
                    start_line=doc.get("start_line", 0),
                    end_line=doc.get("end_line", 0),
                    tokens=doc.get("tokens", 0),
                    language=Language(doc["language"]) if doc.get("language") else Language.UNKNOWN,
                )
        except Exception as e:
            logger.debug(f"Get chunk error: {e}")
        
        return None

    async def close(self):
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")
