"""Local embedding provider using sentence-transformers."""

import asyncio
import logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from config.settings import settings

logger = logging.getLogger(__name__)


class LocalEmbedder:
    """Local embeddings using sentence-transformers."""

    DIMENSIONS = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "multi-qa-mpnet-base-dot-v1": 768,
        "paraphrase-multilingual-MiniLM-L12-v2": 384,
    }

    def __init__(self):
        self.model_name = settings.embedding.local_model
        self._model = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._device = self._get_device()

    def _get_device(self) -> str:
        """Detect and return the best available device (cuda, mps, or cpu)."""
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"
                logger.info("Apple Silicon GPU (MPS) detected")
            else:
                device = "cpu"
                logger.info("Using CPU (no GPU detected)")
            return device
        except ImportError:
            logger.warning("PyTorch not found, defaulting to CPU")
            return "cpu"

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading local embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name, device=self._device)
            logger.info(f"Model loaded on device: {self._device}")
        return self._model

    @property
    def dimensions(self) -> int:
        if self._model:
            return self._model.get_sentence_embedding_dimension()
        return self.DIMENSIONS.get(self.model_name, 384)

    async def embed_text(self, text: str) -> np.ndarray:
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._embed_sync, texts)

    def _embed_sync(self, texts: list[str]) -> list[np.ndarray]:
        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            return [emb.astype(np.float32) for emb in embeddings]
        except Exception as e:
            logger.error(f"Local embedding error: {e}")
            return [np.zeros(self.dimensions, dtype=np.float32) for _ in texts]