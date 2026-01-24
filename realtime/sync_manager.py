"""Sync manager for coordinating real-time updates."""

import asyncio
import logging
from pathlib import Path
from typing import Awaitable, Callable

from config.settings import settings
from realtime.background_indexer import BackgroundIndexer
from realtime.change_tracker import ChangeTracker
from realtime.file_watcher import FileWatcher

logger = logging.getLogger(__name__)


class SyncManager:
    """Coordinate real-time file watching and indexing."""

    def __init__(
        self,
        project_root: Path,
        update_file_fn: Callable[[str], Awaitable[None]],
        remove_file_fn: Callable[[str], Awaitable[None]],
    ):
        self.root = project_root
        self._update_fn = update_file_fn
        self._remove_fn = remove_file_fn

        self._tracker = ChangeTracker()
        self._watcher: FileWatcher | None = None
        self._indexer: BackgroundIndexer | None = None
        self._running = False

    async def start(self):
        """Start real-time synchronization."""
        if not settings.realtime.enabled:
            logger.info("Real-time sync disabled")
            return

        self._running = True

        # Start background indexer
        self._indexer = BackgroundIndexer(self._process_file)
        await self._indexer.start()

        # Start file watcher
        self._watcher = FileWatcher(self.root, self._on_file_change)
        asyncio.create_task(self._watcher.start())

        logger.info("Real-time sync started")

    async def _on_file_change(self, file: str, change_type: str):
        """Handle file change event."""
        if change_type == "deleted":
            await self._remove_fn(file)
            self._tracker.remove_file(file)
        else:
            # Priority: 1 for modified, 3 for added
            priority = 1 if change_type == "modified" else 3
            await self._indexer.enqueue(file, priority)

    async def _process_file(self, file: str):
        """Process a file update."""
        full_path = self.root / file

        if not full_path.exists():
            await self._remove_fn(file)
            self._tracker.remove_file(file)
            return

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")

            # Check if actually changed
            if not self._tracker.has_changed(file, content):
                logger.debug(f"File unchanged, skipping: {file}")
                return

            await self._update_fn(file)
            self._tracker.track_file(file, content)

        except Exception as e:
            logger.error(f"Error processing {file}: {e}")

    def track_file(self, path: str, content: str):
        """Track a file that was indexed."""
        self._tracker.track_file(path, content)

    async def stop(self):
        """Stop real-time synchronization."""
        self._running = False

        if self._watcher:
            self._watcher.stop()

        if self._indexer:
            await self._indexer.stop()

        logger.info("Real-time sync stopped")

    @property
    def pending_count(self) -> int:
        """Get number of files pending processing."""
        return self._indexer.pending_count if self._indexer else 0
