"""Track file changes and determine what needs re-indexing."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.utils import compute_hash

logger = logging.getLogger(__name__)


@dataclass
class FileState:
    """State of a tracked file."""

    path: str
    hash: str
    size: int
    modified: datetime
    indexed: datetime = field(default_factory=datetime.utcnow)


class ChangeTracker:
    """Track file changes for incremental updates."""

    def __init__(self):
        self._states: dict[str, FileState] = {}

    def track_file(self, path: str, content: str):
        """Track a file's state."""
        file_hash = compute_hash(content)
        self._states[path] = FileState(
            path=path, hash=file_hash, size=len(content), modified=datetime.utcnow()
        )

    def has_changed(self, path: str, content: str) -> bool:
        """Check if file has changed since last tracking."""
        if path not in self._states:
            return True

        current_hash = compute_hash(content)
        return self._states[path].hash != current_hash

    def remove_file(self, path: str):
        """Remove file from tracking."""
        self._states.pop(path, None)

    def get_state(self, path: str) -> FileState | None:
        """Get tracked state for a file."""
        return self._states.get(path)

    def get_all_tracked(self) -> list[str]:
        """Get all tracked file paths."""
        return list(self._states.keys())

    def clear(self):
        """Clear all tracking data."""
        self._states.clear()

    def get_stale_files(self, root: Path, max_age_hours: int = 24) -> list[str]:
        """Get files that haven't been re-indexed recently."""
        cutoff = datetime.utcnow()
        stale = []

        for path, state in self._states.items():
            full_path = root / path
            if not full_path.exists():
                stale.append(path)
            elif (cutoff - state.indexed).total_seconds() > max_age_hours * 3600:
                stale.append(path)

        return stale
