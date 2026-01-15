"""Unified indexer combining all indexing capabilities."""

import asyncio
import time
import logging
from pathlib import Path
from typing import Callable, Iterator

from core.types import Symbol, SymbolKind, FileInfo, IndexStats, ParseError
from core.utils import compute_hash
from config.settings import settings, Language, EXTENSION_MAP
from parsers.incremental_parser import get_parser
from indexers.symbol_table import SymbolTable
from indexers.file_index import FileIndex, create_file_info
from indexers.dependency_graph import DependencyGraph

logger = logging.getLogger(__name__)


class UnifiedIndexer:
    """
    Unified code indexer that:
    - Discovers and indexes source files
    - Builds symbol tables
    - Tracks file dependencies
    - Supports incremental updates
    """

    def __init__(self, project_root: Path):
        self.root = project_root
        self._parser = get_parser()
        self.symbol_table = SymbolTable()
        self.file_index = FileIndex()
        self.dependency_graph = DependencyGraph()
        
        # Caches
        self._contents: dict[str, str] = {}
        self._stats = IndexStats()

    @property
    def stats(self) -> IndexStats:
        return self._stats

    async def index_project(
        self, 
        progress: Callable[[str, str], None] | None = None
    ) -> IndexStats:
        """Index the entire project."""
        start = time.time()
        
        # Discover files
        files = list(self._discover_files())
        self._stats.total_files = len(files)
        
        if progress:
            progress("discovery", f"Found {len(files)} files")
        
        # Parse files
        parse_start = time.time()
        symbols_by_file: dict[str, list[Symbol]] = {}
        languages: dict[str, Language] = {}
        errors: list[ParseError] = []
        
        for i, file_path in enumerate(files):
            if progress and i % 50 == 0:
                progress("parsing", f"Parsing {i}/{len(files)} files")
            
            result = await self._index_file(file_path)
            if result:
                file_info, file_symbols, file_errors = result
                symbols_by_file[file_info.path] = file_symbols
                languages[file_info.path] = file_info.language
                errors.extend(file_errors)
        
        self._stats.parse_time_ms = (time.time() - parse_start) * 1000
        self._stats.total_symbols = len(self.symbol_table)
        
        # Build dependency graph
        if progress:
            progress("dependencies", "Building dependency graph")
        
        self.dependency_graph.build_from_files(self._contents, languages)
        self.dependency_graph.build_call_graph(self.symbol_table.all_symbols())
        self.dependency_graph.build_type_refs(self.symbol_table.all_symbols())
        
        # Calculate stats
        self._calculate_stats()
        self._stats.index_time_ms = (time.time() - start) * 1000
        
        logger.info(
            f"Indexed {self._stats.total_files} files, {self._stats.total_symbols} symbols "
            f"in {self._stats.index_time_ms:.0f}ms"
        )
        
        return self._stats

    async def _index_file(self, file_path: Path) -> tuple[FileInfo, list[Symbol], list[ParseError]] | None:
        """Index a single file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.debug(f"Failed to read {file_path}: {e}")
            return None
        
        # Check file size
        if len(content) > settings.parser.max_file_size:
            logger.debug(f"Skipping large file: {file_path}")
            return None
        
        # Create file info
        relative_path = str(file_path.relative_to(self.root))
        file_info = create_file_info(str(file_path), content, self.root)
        
        # Parse
        result = self._parser.parse_content(content, relative_path)
        
        # Store
        self._contents[relative_path] = content
        self.file_index.add(file_info)
        self.symbol_table.add_many(result.symbols)
        
        # Update file info
        self.file_index.update_stats(
            relative_path,
            symbols=len(result.symbols),
            has_errors=len(result.errors) > 0
        )
        
        return file_info, result.symbols, result.errors

    async def update_file(self, file_path: Path) -> bool:
        """Update a single file in the index."""
        if not file_path.exists():
            await self.remove_file(file_path)
            return False
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return False
        
        relative_path = str(file_path.relative_to(self.root))
        
        # Check if actually changed
        if not self.file_index.needs_reindex(relative_path, content):
            return False
        
        # Remove old data
        self.symbol_table.remove_file(relative_path)
        
        # Re-parse
        result = self._parser.parse_content(content, relative_path)
        
        # Update stores
        self._contents[relative_path] = content
        file_info = create_file_info(str(file_path), content, self.root)
        self.file_index.add(file_info)
        self.symbol_table.add_many(result.symbols)
        
        self.file_index.update_stats(
            relative_path,
            symbols=len(result.symbols),
            has_errors=len(result.errors) > 0
        )
        
        # Update dependency graph for this file
        self.dependency_graph.build_from_files(
            {relative_path: content},
            {relative_path: file_info.language}
        )
        
        return True

    async def remove_file(self, file_path: Path):
        """Remove a file from the index."""
        try:
            relative_path = str(file_path.relative_to(self.root))
        except ValueError:
            relative_path = str(file_path)
        
        self.symbol_table.remove_file(relative_path)
        self.file_index.remove(relative_path)
        self._contents.pop(relative_path, None)
        self._parser.invalidate(relative_path)

    def get_file_content(self, file: str) -> str | None:
        """Get cached file content."""
        return self._contents.get(file)

    def get_file_symbols(self, file: str) -> list[Symbol]:
        """Get symbols for a file."""
        return self.symbol_table.get_by_file(file)

    def search_symbols(self, query: str, max_results: int = 50) -> list[Symbol]:
        """Search symbols by name."""
        return self.symbol_table.search(query, max_results=max_results)

    def detect_language(self) -> Language:
        """Detect primary language of the project."""
        stats = self.file_index.stats()
        by_lang = stats.get("by_language", {})
        if not by_lang:
            return Language.UNKNOWN
        
        # Get most common language
        return Language(max(by_lang.items(), key=lambda x: x[1])[0])

    def _discover_files(self) -> Iterator[Path]:
        """Discover all source files in the project."""
        for path in self.root.rglob('*'):
            if not path.is_file():
                continue
            
            # Skip directories
            if any(skip in path.parts for skip in settings.parser.skip_dirs):
                continue
            
            # Check extension
            if path.suffix.lower() in EXTENSION_MAP:
                yield path

    def _calculate_stats(self):
        """Calculate index statistics."""
        for info in self.file_index.all_files():
            lang = info.language.value
            self._stats.languages[lang] = self._stats.languages.get(lang, 0) + 1

    def clear(self):
        """Clear all index data."""
        self.symbol_table.clear()
        self.file_index.clear()
        self.dependency_graph.clear()
        self._contents.clear()
        self._parser.clear()
        self._stats = IndexStats()