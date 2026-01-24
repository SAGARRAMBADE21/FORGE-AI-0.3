"""Voyage AI embedding provider (code-optimized)."""

import asyncio
import logging

import httpx
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


class VoyageEmbedder:
    """Voyage AI embeddings (optimized for code)."""

    DIMENSIONS = {
        "voyage-code-2": 1536,
        "voyage-code-3": 1024,
        "voyage-2": 1024,
        "voyage-large-2": 1536,
    }

    def __init__(self):
        self.model = settings.embedding.voyage_model
        self.api_key = settings.embedding.voyage_api_key
        self._base_url = "https://api.voyageai.com/v1"

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS.get(self.model, 1536)

    async def embed_text(self, text: str) -> np.ndarray:
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(
        self, texts: list[str], input_type: str = "document"
    ) -> list[np.ndarray]:
        if not texts:
            return []

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "input": texts,
                        "input_type": input_type,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return [
                    np.array(item["embedding"], dtype=np.float32)
                    for item in data["data"]
                ]
            except Exception as e:
                logger.error(f"Voyage embedding error: {e}")
                return [np.zeros(self.dimensions, dtype=np.float32) for _ in texts]

    async def embed_query(self, query: str) -> np.ndarray:
        """Embed query with query-specific optimization."""
        embeddings = await self.embed_texts([query], input_type="query")
        return embeddings[0]
