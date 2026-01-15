"""Cross-encoder reranker for search results."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from core.types import SearchResult
from config.settings import settings

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker for improving search accuracy."""

    def __init__(self):
        self._model = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._device = self._get_device()

    def _get_device(self) -> str:
        """Detect best available device for reranking."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        except ImportError:
            return "cpu"

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading reranker: {settings.search.rerank_model}")
                self._model = CrossEncoder(settings.search.rerank_model, device=self._device)
                logger.info(f"Reranker loaded on {self._device.upper()}")
            except Exception as e:
                logger.error(f"Failed to load reranker: {e}")
                self._model = False  # Mark as failed

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None
    ) -> list[SearchResult]:
        """Rerank search results using cross-encoder."""
        if not results:
            return results

        top_k = top_k or settings.search.rerank_k

        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            self._executor,
            self._rerank_sync,
            query,
            [r.chunk.content for r in results]
        )

        if scores is None:
            return results

        # Update scores
        for result, score in zip(results, scores):
            # Combine original score with reranker score
            result.score = 0.3 * result.score + 0.7 * float(score)

        # Sort by new scores
        results.sort(key=lambda x: -x.score)

        return results[:top_k]

    def _rerank_sync(self, query: str, contents: list[str]) -> list[float] | None:
        self._load_model()

        if self._model is False:
            return None

        try:
            pairs = [(query, c[:1000]) for c in contents]  # Limit content length
            scores = self._model.predict(pairs)
            return scores.tolist()
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return None