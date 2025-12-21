"""Real-time file watching."""

import asyncio
import time
import logging
from pathlib import Path
from typing import Callable, Awaitable

from config.settings import settings, EXTENSION_MAP

logger = logging.getLogger(__name__)


class FileWatcher:
    """Watch for file changes with debouncing."""

    def __init__(
        self,
        project_root: Path,
        on_change: Callable[[str, str], Awaitable[None]]
    ):
        self.root = project_root
        self.on_change = on_change
        self._running = False
        self._pending: dict[str, tuple[str, float]] = {}
        self._debounce_ms = settings.realtime.debounce_ms
        self._process_task = None

    async def start(self):
        """Start watching for file changes."""
        self._running = True

        # Start debounce processor
        self._process_task = asyncio.create_task(self._process_pending())

        logger.info(f"Watching {self.root} for changes")

        try:
            from watchfiles import awatch, Change

            async for changes in awatch(self.root, stop_event=self._create_stop_event()):
                if not self._running:
                    break

                for change_type, path in changes:
                    if self._should_process(path):
                        change_name = {
                            Change.added: "added",
                            Change.modified: "modified",
                            Change.deleted: "deleted"
                        }.get(change_type, "unknown")

                        self._pending[path] = (change_name, time.time())
                        logger.debug(f"File {change_name}: {path}")

        except ImportError:
            logger.error("watchfiles not installed, file watching disabled")
        except Exception as e:
            logger.error(f"File watcher error: {e}")

    def _create_stop_event(self):
        """Create an event that triggers when watching should stop."""
        import threading
        event = threading.Event()
        return event

    async def _process_pending(self):
        """Process pending file changes with debouncing."""
        while self._running:
            await asyncio.sleep(self._debounce_ms / 1000)

            now = time.time()
            threshold = self._debounce_ms / 1000

            ready = [
                (path, change)
                for path, (change, ts) in list(self._pending.items())
                if now - ts >= threshold
            ]

            for path, change in ready:
                del self._pending[path]
                try:
                    relative = str(Path(path).relative_to(self.root))
                    await self.on_change(relative, change)
                except Exception as e:
                    logger.error(f"Error processing {path}: {e}")

    def _should_process(self, path: str) -> bool:
        """Check if file should be processed."""
        p = Path(path)

        # Check extension
        if p.suffix.lower() not in EXTENSION_MAP:
            return False

        # Check skip directories
        if any(skip in p.parts for skip in settings.parser.skip_dirs):
            return False

        return True

    def stop(self):
        """Stop watching."""
        self._running = False
        if self._process_task:
            self._process_task.cancel()