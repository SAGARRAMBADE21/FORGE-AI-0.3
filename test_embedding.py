"""Test script to verify Voyage Code-3 embeddings are working."""

import asyncio
from embeddings.embedder import Embedder
from config.settings import settings


async def test_embedding():
    print("Testing Voyage Code-3 Embeddings...")
    print(f"Provider: {settings.embedding.provider}")
    print(f"Model: {settings.embedding.voyage_model}")
    print(f"API Key set: {'Yes' if settings.embedding.voyage_api_key else 'No'}")
    print()
    
    embedder = Embedder()
    
    # Test document embedding
    test_text = "def calculate_sum(a, b): return a + b"
    print(f"Testing document embedding for: '{test_text}'")
    
    try:
        embedding = await embedder.embed_text(test_text)
        print(f"✓ Success! Embedding dimensions: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        print()
    except Exception as e:
        print(f"✗ Failed: {e}")
        return
    
    # Test query embedding
    test_query = "find function that adds two numbers"
    print(f"Testing query embedding for: '{test_query}'")
    
    try:
        query_embedding = await embedder.embed_query(test_query)
        print(f"✓ Success! Query embedding dimensions: {len(query_embedding)}")
        print(f"  First 5 values: {query_embedding[:5]}")
        print()
        print("All tests passed! ✓")
    except Exception as e:
        print(f"✗ Failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_embedding())
