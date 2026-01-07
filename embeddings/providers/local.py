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
        "microsoft/graphcodebert-base": 768,
        "microsoft/unixcoder-base": 768,
        "microsoft/codebert-base": 768,
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
            import warnings
            
            # Suppress CUDA compatibility warnings
            warnings.filterwarnings('ignore', category=UserWarning, module='torch.cuda')
            
            if torch.cuda.is_available():
                # Check GPU compatibility first
                try:
                    device_capability = torch.cuda.get_device_capability(0)
                    compute_capability = device_capability[0] * 10 + device_capability[1]
                    gpu_name = torch.cuda.get_device_name(0)
                    
                    # RTX 50-series (Blackwell) has sm_120, not yet supported by PyTorch
                    if compute_capability >= 120:
                        logger.info(f"GPU detected: {gpu_name} (sm_{compute_capability})")
                        logger.warning(
                            f"RTX 50-series GPUs (sm_{compute_capability}) not yet supported by PyTorch. "
                            f"Using CPU mode. Check pytorch.org for updates."
                        )
                        return "cpu"
                    elif compute_capability > 90:
                        logger.info(f"GPU detected: {gpu_name} (sm_{compute_capability})")
                        logger.warning(
                            f"GPU compute capability sm_{compute_capability} may have limited PyTorch support. "
                            f"Will attempt GPU but may fall back to CPU."
                        )
                        return "cuda"
                    else:
                        logger.info(f"GPU detected: {gpu_name} (sm_{compute_capability})")
                        return "cuda"
                except Exception as e:
                    logger.debug(f"GPU capability check failed: {e}, defaulting to CPU")
                    return "cpu"
                    
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"
                logger.info("Apple Silicon GPU (MPS) detected")
                return device
            else:
                logger.info("Using CPU (no GPU detected)")
                return "cpu"
        except ImportError:
            logger.warning("PyTorch not found, defaulting to CPU")
            return "cpu"

    @property
    def model(self):
        if self._model is None:
            import warnings
            import os
            import logging as transformers_logging
            from sentence_transformers import SentenceTransformer
            
            # Suppress all transformers warnings
            os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
            os.environ['TOKENIZERS_PARALLELISM'] = 'false'
            transformers_logging.getLogger('transformers').setLevel(transformers_logging.ERROR)
            transformers_logging.getLogger('sentence_transformers').setLevel(transformers_logging.ERROR)
            warnings.filterwarnings('ignore', category=UserWarning)
            warnings.filterwarnings('ignore', category=FutureWarning)
            
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
        except RuntimeError as e:
            # Handle CUDA errors by falling back to CPU
            if "CUDA" in str(e) and self._device == "cuda":
                logger.warning(f"CUDA error encountered: {e}")
                logger.info("Switching to CPU mode...")
                self._device = "cpu"
                self._model = None  # Force model reload on CPU
                # Retry on CPU
                try:
                    embeddings = self.model.encode(
                        texts,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False
                    )
                    return [emb.astype(np.float32) for emb in embeddings]
                except Exception as e2:
                    logger.error(f"CPU fallback failed: {e2}")
                    return [np.zeros(self.dimensions, dtype=np.float32) for _ in texts]
            else:
                logger.error(f"Embedding error: {e}")
                return [np.zeros(self.dimensions, dtype=np.float32) for _ in texts]
        except Exception as e:
            logger.error(f"Local embedding error: {e}")
            return [np.zeros(self.dimensions, dtype=np.float32) for _ in texts]