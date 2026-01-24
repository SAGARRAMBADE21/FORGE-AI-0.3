"""File index for tracking indexed files."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator

from config.settings import EXTENSION_MAP, Language
from core.types import FileInfo
from core.utils import compute_hash

logger = logging.getLogger(__name__)


class FileIndex:
    """Index of all tracked files."""

    def __init__(self):
        self._files: dict[str, FileInfo] = {}

    def add(self, info: FileInfo):
        """Add or update file info."""
        self._files[info.path] = info

    def get(self, path: str) -> FileInfo | None:
        """Get file info by path."""
        return self._files.get(path)

    def remove(self, path: str) -> FileInfo | None:
        """Remove file from index."""
        return self._files.pop(path, None)

    def has(self, path: str) -> bool:
        """Check if file is indexed."""
        return path in self._files

    def update_stats(
        self, path: str, symbols: int = 0, chunks: int = 0, has_errors: bool = False
    ):
        """Update file statistics."""
        if path in self._files:
            self._files[path].symbols = symbols
            self._files[path].chunks = chunks
            self._files[path].has_errors = has_errors
            self._files[path].indexed = datetime.utcnow()

    def needs_reindex(self, path: str, content: str) -> bool:
        """Check if file needs re-indexing based on content hash."""
        info = self._files.get(path)
        if info is None:
            return True
        return info.hash != compute_hash(content)

    def all_files(self) -> Iterator[FileInfo]:
        """Iterate over all files."""
        return iter(self._files.values())

    def files_by_language(self, language: Language) -> list[FileInfo]:
        """Get all files of a specific language."""
        return [f for f in self._files.values() if f.language == language]

    def get_paths(self) -> list[str]:
        """Get all file paths."""
        return list(self._files.keys())

    def clear(self):
        """Clear all files."""
        self._files.clear()

    def __len__(self) -> int:
        return len(self._files)

    def stats(self) -> dict:
        """Get statistics about indexed files."""
        by_language: dict[str, int] = {}
        total_size = 0
        error_count = 0

        for info in self._files.values():
            lang = info.language.value
            by_language[lang] = by_language.get(lang, 0) + 1
            total_size += info.size
            if info.has_errors:
                error_count += 1

        return {
            "total_files": len(self._files),
            "total_size": total_size,
            "by_language": by_language,
            "files_with_errors": error_count,
        }


def create_file_info(path: str, content: str, root: Path) -> FileInfo:
    """Create FileInfo from file content."""
    relative_path = str(Path(path).relative_to(root)) if root else path
    ext = Path(path).suffix.lower()
    language = EXTENSION_MAP.get(ext, Language.UNKNOWN)

    return FileInfo(
        path=relative_path,
        language=language,
        size=len(content),
        hash=compute_hash(content),
        last_modified=datetime.utcnow(),
    )
