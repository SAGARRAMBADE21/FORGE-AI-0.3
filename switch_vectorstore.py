"""Helper script to switch vector store backends."""

import asyncio
import sys
from pathlib import Path

from config.settings import settings, VectorStoreBackend
from vectorstore import get_vectorstore


async def main():
    """Show current backend and allow switching."""
    
    print("=" * 60)
    print("FORGE 0.3 - Vector Store Backend Manager")
    print("=" * 60)
    print()
    
    # Show current backend
    current = settings.vectorstore.backend
    print(f"Current backend: {current.value}")
    print()
    
    # Show backend options
    print("Available backends:")
    print("  1. memory    - In-memory storage (fast, not persistent)")
    print("  2. chromadb  - Local ChromaDB (persistent, fast)")
    print("  3. qdrant    - Qdrant (local or cloud)")
    print("  4. mongodb   - MongoDB Atlas Vector Search (cloud)")
    print()
    
    # Show backend-specific info
    if current == VectorStoreBackend.CHROMADB:
        print(f"ChromaDB location: {settings.vectorstore.persist_dir}")
        print(f"Collection: {settings.vectorstore.collection}")
    elif current == VectorStoreBackend.MONGODB:
        mongodb_uri = settings.vectorstore.mongodb_uri
        if mongodb_uri:
            # Hide password in display
            safe_uri = mongodb_uri.split('@')[1] if '@' in mongodb_uri else "not configured"
            print(f"MongoDB Atlas: {safe_uri}")
            print(f"Database: {settings.vectorstore.mongodb_database}")
            print(f"Collection: {settings.vectorstore.mongodb_collection}")
            print(f"Index: {settings.vectorstore.mongodb_index}")
        else:
            print("⚠️  MongoDB URI not configured!")
            print("   Set MONGODB_URI in .env file")
    elif current == VectorStoreBackend.QDRANT:
        print(f"Collection: {settings.vectorstore.collection}")
    
    print()
    
    # Get chunk count
    try:
        store = get_vectorstore()
        await store.initialize()
        count = store.count()
        print(f"Current chunks: {count:,}")
    except Exception as e:
        print(f"⚠️  Could not connect to backend: {e}")
    
    print()
    print("=" * 60)
    print()
    
    # Interactive menu
    if len(sys.argv) > 1:
        choice = sys.argv[1].lower()
    else:
        print("To switch backend, run:")
        print("  python switch_vectorstore.py memory")
        print("  python switch_vectorstore.py chromadb")
        print("  python switch_vectorstore.py qdrant")
        print("  python switch_vectorstore.py mongodb")
        print()
        print("Note: Switching backend doesn't migrate data!")
        print("      You'll need to re-index your codebase.")
        return
    
    # Validate choice
    backend_map = {
        "memory": VectorStoreBackend.MEMORY,
        "chromadb": VectorStoreBackend.CHROMADB,
        "qdrant": VectorStoreBackend.QDRANT,
        "mongodb": VectorStoreBackend.MONGODB,
    }
    
    if choice not in backend_map:
        print(f"❌ Invalid backend: {choice}")
        print(f"   Valid options: {', '.join(backend_map.keys())}")
        return
    
    new_backend = backend_map[choice]
    
    # Check MongoDB configuration
    if new_backend == VectorStoreBackend.MONGODB:
        if not settings.vectorstore.mongodb_uri:
            print("❌ Cannot switch to MongoDB: MONGODB_URI not configured")
            print()
            print("Steps to configure MongoDB Atlas:")
            print("  1. Create MongoDB Atlas account and cluster")
            print("  2. Create vector search index (see MONGODB_ATLAS_SETUP.md)")
            print("  3. Add MONGODB_URI to .env file")
            print("  4. Run: pip install motor pymongo")
            print()
            print("See MONGODB_ATLAS_SETUP.md for detailed instructions.")
            return
    
    # Update config file
    config_path = Path(__file__).parent / "config" / "settings.py"
    
    print(f"✓ Backend will be set to: {new_backend.value}")
    print()
    print("⚠️  WARNING: This doesn't migrate your existing chunks!")
    print("   You need to re-index your codebase with:")
    print(f"   python main.py index run \"path/to/codebase\"")
    print()
    
    # Note: In production, you'd want to update this programmatically
    # For now, just inform the user
    print("To make this permanent, update config/settings.py:")
    print(f"  backend: VectorStoreBackend = VectorStoreBackend.{new_backend.name}")
    print()
    print("Or use environment variable:")
    print(f"  set VECTORSTORE_BACKEND={new_backend.value}")


if __name__ == "__main__":
    asyncio.run(main())
