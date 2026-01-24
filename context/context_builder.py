"""Build context for LLM queries."""

import logging
from typing import Awaitable, Callable

from context.token_budgeter import TokenBudget, TokenBudgeter
from core.types import Chunk, SearchResult
from core.utils import count_tokens, truncate_tokens
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build optimized context for LLM queries."""

    def __init__(self, indexer: UnifiedIndexer, budget: TokenBudget | None = None):
        self._indexer = indexer
        self._budgeter = TokenBudgeter(budget)

    async def build_context(
        self,
        query: str,
        search_results: list[SearchResult],
        current_file: str | None = None,
        selection: tuple[int, int] | None = None,
    ) -> str:
        """Build context from search results and current file."""
        self._budgeter.reset()
        parts = []
        seen_content = set()

        # 1. Search results
        search_budget = self._budgeter.get_allocation("search")
        search_context = self._build_search_context(
            search_results, search_budget, seen_content
        )
        if search_context:
            parts.append("## Relevant Code\n" + search_context)
            self._budgeter.allocate(search_context)

        # 2. Current file context
        if current_file:
            current_budget = self._budgeter.get_allocation("current")
            current_context = self._build_current_file_context(
                current_file, selection, current_budget
            )
            if current_context:
                parts.append("## Current File\n" + current_context)
                self._budgeter.allocate(current_context)

        # 3. Related files
        if current_file:
            related_budget = self._budgeter.get_allocation("related")
            related_context = self._build_related_context(
                current_file, related_budget, seen_content
            )
            if related_context:
                parts.append("## Related Files\n" + related_context)

        return "\n\n".join(parts)

    def _build_search_context(
        self, results: list[SearchResult], max_tokens: int, seen: set
    ) -> str:
        """Build context from search results."""
        parts = []
        used_tokens = 0

        for result in results:
            content_hash = hash(result.chunk.content)
            if content_hash in seen:
                continue
            seen.add(content_hash)

            formatted = self._format_chunk(result.chunk)
            chunk_tokens = count_tokens(formatted)

            if used_tokens + chunk_tokens > max_tokens:
                # Try truncated version
                remaining = max_tokens - used_tokens
                if remaining > 200:
                    truncated = truncate_tokens(formatted, remaining - 50)
                    parts.append(truncated + "\n...(truncated)")
                break

            parts.append(formatted)
            used_tokens += chunk_tokens

        return "\n\n".join(parts)

    def _format_chunk(self, chunk: Chunk) -> str:
        """Format a chunk for context."""
        header = f"### {chunk.file}:{chunk.start_line + 1}-{chunk.end_line + 1}"
        if chunk.symbol_name:
            header += f" ({chunk.symbol_name})"

        return f"{header}\n```{chunk.language}\n{chunk.content}\n```"

    def _build_current_file_context(
        self, file: str, selection: tuple[int, int] | None, max_tokens: int
    ) -> str:
        """Build context from current file."""
        content = self._indexer.get_file_content(file)
        if not content:
            return ""

        lines = content.split("\n")

        if selection:
            start, end = selection
            # Include surrounding context
            context_start = max(0, start - 20)
            context_end = min(len(lines), end + 20)
            focused = "\n".join(lines[context_start:context_end])
            return truncate_tokens(focused, max_tokens)

        # Return file summary with key symbols
        symbols = self._indexer.symbol_table.get_by_file(file)
        if not symbols:
            return truncate_tokens(content, max_tokens)

        # Build summary from signatures
        parts = [f"File: {file}\n"]
        for sym in symbols[:15]:
            if sym.signature:
                parts.append(f"- {sym.signature}")
            else:
                parts.append(f"- {sym.kind.value}: {sym.name}")

        summary = "\n".join(parts)
        return truncate_tokens(summary, max_tokens)

    def _build_related_context(self, file: str, max_tokens: int, seen: set) -> str:
        """Build context from related files."""
        imports = self._indexer.dependency_graph.get_imports(file)
        parts = []
        used_tokens = 0

        for imp in imports[:5]:
            # Find matching file
            for info in self._indexer.file_index.all_files():
                if imp in info.path:
                    symbols = self._indexer.symbol_table.get_by_file(info.path)
                    exports = [s for s in symbols if s.is_exported]

                    if exports:
                        sigs = [s.signature or s.name for s in exports[:5]]
                        part = f"**{info.path}**: {', '.join(sigs)}"
                        part_tokens = count_tokens(part)

                        if used_tokens + part_tokens > max_tokens:
                            break

                        parts.append(part)
                        used_tokens += part_tokens
                    break

        return "\n".join(parts)
