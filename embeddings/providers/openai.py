"""OpenAI embedding provider."""

import asyncio
import logging

import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """OpenAI embeddings provider."""

    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self):
        self.model = settings.embedding.openai_model
        self.api_key = settings.embedding.openai_api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS.get(self.model, 1536)

    async def embed_text(self, text: str) -> np.ndarray:
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []

        try:
            response = await self.client.embeddings.create(
                model=self.model, input=texts
            )
            return [
                np.array(item.embedding, dtype=np.float32) for item in response.data
            ]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            # Return zero vectors on error
            return [np.zeros(self.dimensions, dtype=np.float32) for _ in texts]
