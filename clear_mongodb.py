"""Clear MongoDB Atlas collection."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def clear_mongodb():
    """Clear all documents from MongoDB Atlas."""
    
    mongodb_uri = os.getenv("MONGODB_URI", "")
    if not mongodb_uri or "YOUR_USERNAME" in mongodb_uri:
        print("❌ MONGODB_URI not configured")
        return
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client[os.getenv("MONGODB_DATABASE", "code_indexer")]
        collection = db[os.getenv("MONGODB_COLLECTION", "code_chunks")]
        
        # Get current count
        count = await collection.count_documents({})
        print(f"Current documents: {count:,}")
        
        if count > 0:
            # Delete all
            result = await collection.delete_many({})
            print(f"✓ Deleted {result.deleted_count:,} documents")
        else:
            print("Collection is already empty")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(clear_mongodb())
