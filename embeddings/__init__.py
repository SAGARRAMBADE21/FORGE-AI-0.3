"""Embeddings module."""
from embeddings.embedder import Embedder, get_embedder
from embeddings.cache import EmbeddingCache

__all__ = ["Embedder", "get_embedder", "EmbeddingCache"]