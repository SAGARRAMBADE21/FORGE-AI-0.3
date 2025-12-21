"""Embedding providers."""
from embeddings.providers.openai import OpenAIEmbedder
from embeddings.providers.local import LocalEmbedder

__all__ = ["OpenAIEmbedder", "LocalEmbedder"]