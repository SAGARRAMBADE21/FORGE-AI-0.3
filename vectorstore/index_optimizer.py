"""Index optimization utilities."""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class IndexOptimizer:
    """Optimize vector index for better performance."""

    @staticmethod
    def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
        """L2 normalize embeddings for cosine similarity."""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / (norms + 1e-8)

    @staticmethod
    def deduplicate_chunks(chunks: list, threshold: float = 0.95) -> list:
        """Remove near-duplicate chunks based on content similarity."""
        if len(chunks) <= 1:
            return chunks

        unique = [chunks[0]]
        for chunk in chunks[1:]:
            is_duplicate = False
            for existing in unique:
                if chunk.embedding is not None and existing.embedding is not None:
                    sim = np.dot(chunk.embedding, existing.embedding)
                    if sim > threshold:
                        is_duplicate = True
                        break
            if not is_duplicate:
                unique.append(chunk)

        removed = len(chunks) - len(unique)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate chunks")

        return unique

    @staticmethod
    def cluster_embeddings(embeddings: np.ndarray, n_clusters: int = 10):
        """Cluster embeddings for faster search."""
        try:
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=min(n_clusters, len(embeddings)), random_state=42)
            labels = kmeans.fit_predict(embeddings)
            centroids = kmeans.cluster_centers_
            return labels, centroids
        except ImportError:
            logger.warning("sklearn not available for clustering")
            return None, None