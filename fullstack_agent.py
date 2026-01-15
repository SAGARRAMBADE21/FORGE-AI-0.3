"""Unified full-stack agent combining indexer and backend generator."""

import asyncio
import logging
from pathlib import Path
from typing import Callable

from core.types import (
    Symbol, SymbolKind, Chunk, SearchQuery, SearchResponse,
    FrontendAnalysis, GenerationResult, IndexStats,
    NavRequest, Position, DefinitionResult, ReferenceResult,
    InferredModel, ApiResourceContract
)
from config.settings import Language
from config.templates_config import TemplateConfig
from agent import CodeAgent
from backend_agent import BackendAgent

logger = logging.getLogger(__name__)


class FullStackAgent:
    """
    Unified agent for full-stack development.
    
    Combines:
    - Code indexing and semantic search
    - Frontend analysis
    - Backend generation
    - Real-time synchronization
    - Navigation capabilities
    """

    def __init__(
        self, 
        project_root: str | Path,
        backend_config: TemplateConfig | None = None
    ):
        self.root = Path(project_root)
        
        # Initialize sub-agents
        self._code_agent = CodeAgent(project_root)
        self._backend_agent = BackendAgent(self.root, backend_config)
        
        # State
        self._initialized = False
        self._watching = False

    # ═══════════════════════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════

    async def initialize(
        self,
        progress: Callable[[str, str], None] | None = None,
        force_reindex: bool = False
    ) -> IndexStats:
        """Initialize the full-stack agent."""
        # Skip if already initialized and not forcing reindex
        if self._initialized and not force_reindex:
            if progress:
                progress("ready", "Using existing index")
            # Return cached stats
            return self._code_agent.indexer.get_stats()
        
        # Initialize code agent (indexer)
        if progress:
            progress("indexing", "Initializing code indexer...")

        stats = await self._code_agent.initialize(progress)

        # Initialize backend agent
        if progress:
            progress("backend", "Initializing backend agent...")

        await self._backend_agent.initialize(
            self._code_agent.indexer,
            progress
        )

        self._initialized = True

        if progress:
            progress("ready", "Full-stack agent ready")

        return stats

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def backend_agent(self) -> BackendAgent:
        """Expose the backend agent for external access."""
        return self._backend_agent

    # ═══════════════════════════════════════════════════════════════════════
    # CODE INDEXING & SEARCH
    # ═══════════════════════════════════════════════════════════════════════

    async def search(
        self,
        query: str,
        top_k: int = 10,
        files: list[str] | None = None,
        languages: list[Language] | None = None
    ) -> SearchResponse:
        """Semantic search over codebase."""
        return await self._code_agent.search(query, top_k, files, languages)

    def search_symbols(self, query: str, max_results: int = 50) -> list[Symbol]:
        """Search symbols by name."""
        return self._code_agent.search_symbols(query, max_results)

    def get_file_symbols(self, file: str) -> list[Symbol]:
        """Get all symbols in a file."""
        return self._code_agent.get_file_symbols(file)

    def get_file_content(self, file: str) -> str | None:
        """Get file content."""
        return self._code_agent.get_file_content(file)

    # ═══════════════════════════════════════════════════════════════════════
    # NAVIGATION
    # ═══════════════════════════════════════════════════════════════════════

    async def go_to_definition(self, file: str, line: int, col: int) -> DefinitionResult:
        """Go to definition."""
        return await self._code_agent.go_to_definition(file, line, col)

    async def find_references(self, file: str, line: int, col: int) -> ReferenceResult:
        """Find all references."""
        return await self._code_agent.find_references(file, line, col)

    async def get_hover(self, file: str, line: int, col: int):
        """Get hover information."""
        return await self._code_agent.get_hover(file, line, col)

    # ═══════════════════════════════════════════════════════════════════════
    # FRONTEND ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════

    async def analyze_frontend(
        self,
        progress: Callable[[str, str], None] | None = None
    ) -> FrontendAnalysis:
        """Analyze frontend code."""
        return await self._code_agent.analyze_frontend(progress)

    # ═══════════════════════════════════════════════════════════════════════
    # BACKEND GENERATION
    # ═══════════════════════════════════════════════════════════════════════

    async def generate_backend(
        self,
        progress: Callable[[str, str], None] | None = None
    ) -> GenerationResult:
        """Generate complete backend from frontend analysis."""
        if not self._initialized:
            await self.initialize(progress)

        return await self._backend_agent.generate_backend(progress)

    async def add_model(
        self,
        name: str,
        fields: list[dict],
        progress: Callable[[str, str], None] | None = None
    ) -> GenerationResult:
        """Add a new model."""
        return await self._backend_agent.add_model(name, fields, progress)

    async def add_endpoint(
        self,
        method: str,
        path: str,
        config: dict | None = None,
        progress: Callable[[str, str], None] | None = None
    ) -> GenerationResult:
        """Add a new API endpoint."""
        return await self._backend_agent.add_endpoint(method, path, config, progress)

    async def sync_backend(
        self,
        progress: Callable[[str, str], None] | None = None
    ) -> GenerationResult:
        """Sync backend with frontend changes."""
        return await self._backend_agent.sync_with_frontend(progress)

    async def rollback(self) -> bool:
        """Rollback last backend change."""
        return await self._backend_agent.rollback()

    # ═══════════════════════════════════════════════════════════════════════
    # REAL-TIME SYNC
    # ═══════════════════════════════════════════════════════════════════════

    async def start_watching(self, auto_sync: bool = False):
        """Start watching for file changes."""
        await self._code_agent.start_watching()
        self._watching = True

        if auto_sync:
            # Start background sync task
            asyncio.create_task(self._auto_sync_loop())

    async def _auto_sync_loop(self):
        """Background loop for auto-syncing backend."""
        while self._watching:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            try:
                # Detect if frontend changed
                # Could be smarter about detecting relevant changes
                pass
            except Exception as e:
                logger.error(f"Auto-sync error: {e}")

    def stop_watching(self):
        """Stop watching for changes."""
        self._code_agent.stop_watching()
        self._watching = False

    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT FOR LLM
    # ═══════════════════════════════════════════════════════════════════════

    async def build_context(
        self,
        query: str,
        current_file: str | None = None,
        include_backend: bool = True,
        top_k: int = 10
    ) -> str:
        """Build context for LLM queries."""
        # Get code context
        context = await self._code_agent.build_context(
            query, current_file, top_k=top_k
        )

        # Add backend architecture context if available
        if include_backend and self._backend_agent.architecture:
            arch = self._backend_agent.architecture
            
            backend_context = "\n\n## Backend Architecture\n"
            
            if arch.models:
                backend_context += "\n### Models\n"
                for model in arch.models[:5]:
                    fields = ', '.join(f.name for f in model.fields[:5])
                    backend_context += f"- **{model.name}**: {fields}\n"

            if arch.api_resources:
                backend_context += "\n### API Endpoints\n"
                for resource in arch.api_resources[:5]:
                    for endpoint in resource.endpoints[:3]:
                        backend_context += f"- `{endpoint.method} {endpoint.path}`\n"

            context += backend_context

        return context

    # ═══════════════════════════════════════════════════════════════════════
    # INTROSPECTION
    # ═══════════════════════════════════════════════════════════════════════

    def get_models(self) -> list[InferredModel]:
        """Get inferred models."""
        return self._backend_agent.get_models()

    def get_api_resources(self) -> list[ApiResourceContract]:
        """Get API resources."""
        return self._backend_agent.get_api_resources()

    def get_stats(self) -> IndexStats:
        """Get indexer statistics."""
        return self._code_agent.stats

    def get_history(self) -> list[dict]:
        """Get operation history."""
        return self._backend_agent.get_history()

    # ═══════════════════════════════════════════════════════════════════════
    # CHAT INTERFACE
    # ═══════════════════════════════════════════════════════════════════════

    async def chat(
        self,
        message: str,
        current_file: str | None = None
    ) -> dict:
        """
        Process a chat message and return response with actions.
        
        Returns:
            {
                'response': str,
                'actions': list[dict],
                'context_used': str
            }
        """
        # Determine intent
        intent = self._classify_intent(message)

        if intent == 'search':
            results = await self.search(message, top_k=5)
            return {
                'response': f"Found {results.total_count} results",
                'actions': [{'type': 'show_results', 'data': results}],
                'context_used': ''
            }

        elif intent == 'generate':
            context = await self.build_context(message, current_file)
            return {
                'response': "I can help generate code. Here's the relevant context.",
                'actions': [{'type': 'suggest_generation', 'data': {}}],
                'context_used': context
            }

        elif intent == 'explain':
            context = await self.build_context(message, current_file)
            return {
                'response': "Here's the context for understanding this code.",
                'actions': [],
                'context_used': context
            }

        else:
            context = await self.build_context(message, current_file)
            return {
                'response': "I'll help with that.",
                'actions': [],
                'context_used': context
            }

    def _classify_intent(self, message: str) -> str:
        """Classify message intent."""
        message_lower = message.lower()

        if any(word in message_lower for word in ['find', 'search', 'where', 'locate']):
            return 'search'
        elif any(word in message_lower for word in ['generate', 'create', 'add', 'make']):
            return 'generate'
        elif any(word in message_lower for word in ['explain', 'what', 'how', 'why']):
            return 'explain'
        else:
            return 'general'