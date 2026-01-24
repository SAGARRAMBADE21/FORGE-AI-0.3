"""Main code agent combining all capabilities."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Callable

from analyzers.frontend_analyzer import FrontendAnalyzer
from chunking.dynamic_chunker import get_chunker
from config.settings import Language, settings
from context.context_builder import ContextBuilder
from core.types import (
    CallHierarchyResult,
    Chunk,
    DefinitionResult,
    FrontendAnalysis,
    HoverInfo,
    IndexStats,
    NavRequest,
    Position,
    ReferenceResult,
    SearchQuery,
    SearchResponse,
    Symbol,
    SymbolKind,
)
from embeddings.embedder import get_embedder
from indexers.unified_indexer import UnifiedIndexer
from navigation.call_hierarchy import CallHierarchyAnalyzer
from navigation.definition_resolver import DefinitionResolver
from navigation.hover_provider import HoverProvider
from navigation.reference_finder import ReferenceFinder
from parsers.incremental_parser import get_parser
from realtime.sync_manager import SyncManager
from search.hybrid_search import HybridSearch
from vectorstore.store import get_vectorstore

logger = logging.getLogger(__name__)


class CodeAgent:
    """
    Complete code agent providing:
    - Multi-language indexing with incremental parsing
    - Semantic search with embeddings
    - Real-time file watching
    - Navigation (go-to-def, references, call hierarchy)
    - Frontend analysis (APIs, types, forms, auth, components)
    - Context building for LLMs
    """

    def __init__(self, project_root: str | Path):
        self.root = Path(project_root)

        # Core components
        self._parser = get_parser()
        self._chunker = get_chunker()
        self._embedder = get_embedder()
        self._vectorstore = get_vectorstore()

        # Indexer
        self._indexer = UnifiedIndexer(self.root)

        # Search
        self._search: HybridSearch | None = None

        # Real-time
        self._sync: SyncManager | None = None

        # Navigation
        self._def_resolver: DefinitionResolver | None = None
        self._ref_finder: ReferenceFinder | None = None
        self._call_hierarchy: CallHierarchyAnalyzer | None = None
        self._hover: HoverProvider | None = None

        # Frontend analyzer
        self._frontend = FrontendAnalyzer(self.root)

        # Context builder
        self._context: ContextBuilder | None = None

        # State
        self._chunks: list[Chunk] = []
        self._analysis: FrontendAnalysis | None = None
        self._initialized = False

    @property
    def indexer(self) -> UnifiedIndexer:
        return self._indexer

    @property
    def stats(self) -> IndexStats:
        return self._indexer.stats

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ═══════════════════════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════

    async def initialize(
        self,
        progress: Callable[[str, str], None] | None = None,
        force_reindex: bool = False,
    ) -> IndexStats:
        """Initialize the agent."""
        start = time.time()

        # Initialize vector store first to check if index exists
        if progress:
            progress("vectorstore", "Initializing vector store...")
        await self._vectorstore.initialize()

        # Check if we can load existing index
        existing_chunks = self._vectorstore.count()
        if existing_chunks > 0 and not force_reindex:
            if progress:
                progress(
                    "loading", f"Loading cached index ({existing_chunks} chunks)..."
                )

            # Quick index for navigation only
            stats = await self._indexer.index_project(progress)

            # Initialize search with vectorstore (no need to load all chunks)
            self._search = HybridSearch()
            self._search.vectorstore = self._vectorstore

            # Initialize components without re-chunking/embedding
            self._def_resolver = DefinitionResolver(self._indexer)
            self._ref_finder = ReferenceFinder(self._indexer)
            self._call_hierarchy = CallHierarchyAnalyzer(self._indexer)
            self._hover = HoverProvider(self._indexer)
            self._context = ContextBuilder(self._indexer)

            # Update stats with cached chunk count
            stats.total_chunks = existing_chunks
            stats.index_time_ms = (time.time() - start) * 1000
            self._initialized = True

            if progress:
                progress(
                    "complete", f"Loaded cached index in {stats.index_time_ms:.0f}ms!"
                )

            logger.info(
                f"Loaded existing index: {existing_chunks} chunks in {stats.index_time_ms:.0f}ms"
            )
            return stats

        # Full indexing path
        if progress:
            progress("indexing", "Indexing source files...")

        stats = await self._indexer.index_project(progress)

        # 3. Create chunks
        if progress:
            progress("chunking", "Creating code chunks...")

        chunk_start = time.time()
        self._chunks = await self._create_chunks()
        stats.total_chunks = len(self._chunks)
        stats.chunk_time_ms = (time.time() - chunk_start) * 1000

        # 4. Embed chunks
        if progress:
            progress("embedding", "Generating embeddings...")

        embed_start = time.time()
        self._chunks = await self._embedder.embed_chunks(self._chunks)
        await self._vectorstore.add_chunks(self._chunks)
        stats.embed_time_ms = (time.time() - embed_start) * 1000

        # 5. Initialize search
        self._search = HybridSearch()
        self._search.index_chunks(self._chunks)

        # 6. Initialize navigation
        self._def_resolver = DefinitionResolver(self._indexer)
        self._ref_finder = ReferenceFinder(self._indexer)
        self._call_hierarchy = CallHierarchyAnalyzer(self._indexer)
        self._hover = HoverProvider(self._indexer)

        # 7. Initialize context builder
        self._context = ContextBuilder(self._indexer)

        stats.index_time_ms = (time.time() - start) * 1000
        self._initialized = True

        if progress:
            progress("complete", "Initialization complete!")

        logger.info(
            f"Initialized in {stats.index_time_ms:.0f}ms: "
            f"{stats.total_files} files, {stats.total_symbols} symbols, {stats.total_chunks} chunks"
        )

        return stats

    async def _create_chunks(self) -> list[Chunk]:
        """Create chunks for all indexed files."""
        all_chunks = []

        # Build dependency graphs
        symbols_by_file = {}
        contents = {}

        for file_info in self._indexer.file_index.all_files():
            symbols_by_file[file_info.path] = self._indexer.get_file_symbols(
                file_info.path
            )
            contents[file_info.path] = (
                self._indexer.get_file_content(file_info.path) or ""
            )

        self._chunker.build_graphs(symbols_by_file, contents)
        all_symbols = [s for syms in symbols_by_file.values() for s in syms]
        self._chunker.build_call_graph(all_symbols)

        # Create chunks
        for file_info in self._indexer.file_index.all_files():
            content = contents.get(file_info.path, "")
            if not content:
                continue

            symbols = symbols_by_file.get(file_info.path, [])
            chunks = self._chunker.chunk_file(
                content, file_info.path, symbols, file_info.language
            )
            all_chunks.extend(chunks)

        return all_chunks

    # ═══════════════════════════════════════════════════════════════════════
    # REAL-TIME UPDATES
    # ═══════════════════════════════════════════════════════════════════════

    async def start_watching(self):
        """Start real-time file watching."""
        if not settings.realtime.enabled:
            return

        self._sync = SyncManager(self.root, self._update_file, self._remove_file)
        await self._sync.start()
        logger.info("Started real-time watching")

    async def _update_file(self, file: str):
        """Update a single file."""
        full_path = self.root / file

        if not full_path.exists():
            await self._remove_file(file)
            return

        # Re-index
        await self._indexer.update_file(full_path)

        # Re-chunk
        content = self._indexer.get_file_content(file)
        if content:
            symbols = self._indexer.get_file_symbols(file)
            file_info = self._indexer.file_index.get(file)
            lang = file_info.language if file_info else Language.UNKNOWN

            new_chunks = self._chunker.chunk_file(content, file, symbols, lang)

            # Remove old chunks
            self._chunks = [c for c in self._chunks if c.file != file]

            # Embed and add new chunks
            new_chunks = await self._embedder.embed_chunks(new_chunks)
            self._chunks.extend(new_chunks)

            # Update vector store
            await self._vectorstore.delete_file(file)
            await self._vectorstore.add_chunks(new_chunks)

            # Update search index
            if self._search:
                self._search.index_chunks(new_chunks)

        # Invalidate analysis
        self._analysis = None

    async def _remove_file(self, file: str):
        """Remove a file from index."""
        await self._indexer.remove_file(self.root / file)
        self._chunks = [c for c in self._chunks if c.file != file]
        await self._vectorstore.delete_file(file)
        self._analysis = None

    def stop_watching(self):
        """Stop file watching."""
        if self._sync:
            asyncio.create_task(self._sync.stop())

    # ═══════════════════════════════════════════════════════════════════════
    # SEARCH
    # ═══════════════════════════════════════════════════════════════════════

    async def search(
        self,
        query: str,
        top_k: int = 10,
        files: list[str] | None = None,
        languages: list[Language] | None = None,
    ) -> SearchResponse:
        """Search the codebase."""
        if not self._search:
            raise RuntimeError("Not initialized")

        return await self._search.search(
            SearchQuery(
                query=query, top_k=top_k, file_filter=files, language_filter=languages
            )
        )

    async def find_similar(self, file: str, line: int, top_k: int = 5) -> list[Chunk]:
        """Find code similar to chunk at location."""
        chunk = None
        for c in self._chunks:
            if c.file == file and c.start_line <= line <= c.end_line:
                chunk = c
                break

        if not chunk or chunk.embedding is None:
            return []

        results = await self._vectorstore.search(chunk.embedding, top_k + 1)
        return [c for c, _ in results if c.id != chunk.id][:top_k]

    # ═══════════════════════════════════════════════════════════════════════
    # NAVIGATION
    # ═══════════════════════════════════════════════════════════════════════

    async def go_to_definition(
        self, file: str, line: int, col: int
    ) -> DefinitionResult:
        """Go to definition."""
        if not self._def_resolver:
            raise RuntimeError("Not initialized")
        return await self._def_resolver.get_definition(
            NavRequest(file, Position(line, col))
        )

    async def find_references(self, file: str, line: int, col: int) -> ReferenceResult:
        """Find all references."""
        if not self._ref_finder:
            raise RuntimeError("Not initialized")
        return await self._ref_finder.find_references(
            NavRequest(file, Position(line, col))
        )

    async def get_call_hierarchy(
        self, file: str, line: int, col: int
    ) -> CallHierarchyResult | None:
        """Get call hierarchy."""
        if not self._call_hierarchy:
            raise RuntimeError("Not initialized")
        return await self._call_hierarchy.get_hierarchy(
            NavRequest(file, Position(line, col))
        )

    async def get_hover(self, file: str, line: int, col: int) -> HoverInfo | None:
        """Get hover information."""
        if not self._hover:
            raise RuntimeError("Not initialized")
        return await self._hover.get_hover(NavRequest(file, Position(line, col)))

    # ═══════════════════════════════════════════════════════════════════════
    # SYMBOL SEARCH
    # ═══════════════════════════════════════════════════════════════════════

    def search_symbols(self, query: str, max_results: int = 50) -> list[Symbol]:
        """Search symbols by name."""
        return self._indexer.search_symbols(query, max_results)

    def get_file_symbols(self, file: str) -> list[Symbol]:
        """Get all symbols in a file."""
        return self._indexer.get_file_symbols(file)

    def get_symbols_by_kind(self, kind: SymbolKind) -> list[Symbol]:
        """Get all symbols of a kind."""
        return self._indexer.symbol_table.get_by_kind(kind)

    # ═══════════════════════════════════════════════════════════════════════
    # FRONTEND ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════

    async def analyze_frontend(
        self, progress: Callable[[str, str], None] | None = None
    ) -> FrontendAnalysis:
        """Perform frontend analysis."""
        if self._analysis:
            return self._analysis

        if not self._initialized:
            await self.initialize(progress)

        if progress:
            progress("analyzing", "Analyzing frontend...")

        self._analysis = await self._frontend.analyze(self._indexer)
        return self._analysis

    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT BUILDING
    # ═══════════════════════════════════════════════════════════════════════

    async def build_context(
        self,
        query: str,
        current_file: str | None = None,
        selection: tuple[int, int] | None = None,
        top_k: int = 10,
    ) -> str:
        """Build context for LLM query."""
        if not self._context:
            raise RuntimeError("Not initialized")

        # Search for relevant code
        response = await self.search(query, top_k=top_k)

        return await self._context.build_context(
            query, response.results, current_file, selection
        )

    # ═══════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════

    def get_chunks(self) -> list[Chunk]:
        """Get all chunks."""
        return self._chunks

    def get_file_chunks(self, file: str) -> list[Chunk]:
        """Get chunks for a file."""
        return [c for c in self._chunks if c.file == file]

    def get_file_content(self, file: str) -> str | None:
        """Get file content."""
        return self._indexer.get_file_content(file)
