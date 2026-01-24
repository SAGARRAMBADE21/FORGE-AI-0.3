"""Clear vector database."""

import asyncio

from vectorstore import get_vectorstore


async def main():
    store = get_vectorstore()
    await store.initialize()

    count = store.count()
    print(f"Current chunk count: {count}")

    if count > 0:
        print("Clearing vector database...")
        await store.clear()
        print("✓ Vector database cleared successfully!")
    else:
        print("Vector database is already empty.")


if __name__ == "__main__":
    asyncio.run(main())
