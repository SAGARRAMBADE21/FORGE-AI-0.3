"""Background indexer for async file processing."""

import asyncio
import logging
from typing import Awaitable, Callable

from config.settings import settings

logger = logging.getLogger(__name__)


class BackgroundIndexer:
    """Process file changes in background workers."""

    def __init__(self, index_fn: Callable[[str], Awaitable[None]]):
        self._index_fn = index_fn
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._workers: list[asyncio.Task] = []

    async def start(self):
        """Start background workers."""
        self._running = True

        for i in range(settings.realtime.workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        logger.info(f"Started {len(self._workers)} background indexing workers")

    async def _worker(self, worker_id: int):
        """Process files from queue."""
        while self._running:
            try:
                priority, file_path = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )

                logger.debug(f"Worker {worker_id}: indexing {file_path}")
                await self._index_fn(file_path)
                self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

    async def enqueue(self, file_path: str, priority: int = 5):
        """
        Add file to indexing queue.
        Lower priority number = processed first.
        """
        await self._queue.put((priority, file_path))

    async def enqueue_many(self, file_paths: list[str], priority: int = 5):
        """Add multiple files to queue."""
        for path in file_paths:
            await self._queue.put((priority, path))

    @property
    def pending_count(self) -> int:
        """Get number of pending files."""
        return self._queue.qsize()

    async def wait_until_empty(self):
        """Wait until queue is empty."""
        await self._queue.join()

    async def stop(self):
        """Stop background workers."""
        self._running = False

        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("Background indexer stopped")
