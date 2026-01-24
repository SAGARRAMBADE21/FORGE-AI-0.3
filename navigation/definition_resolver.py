"""Go-to-definition functionality."""

import logging
import re
from typing import Iterator

from core.types import (
    DefinitionResult,
    LocationLink,
    NavRequest,
    Position,
    Range,
    Symbol,
    SymbolKind,
)
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class DefinitionResolver:
    """Resolve definitions for symbols."""

    def __init__(self, indexer: UnifiedIndexer):
        self._indexer = indexer

    async def get_definition(self, request: NavRequest) -> DefinitionResult:
        """Get definition(s) for symbol at position."""
        # Find symbol at position
        symbol = self._indexer.symbol_table.get_at_position(
            request.file, request.position
        )

        if symbol:
            # Symbol found at position - return its definition
            return DefinitionResult(symbol=symbol, definitions=[symbol])

        # Try to find identifier at position
        content = self._indexer.get_file_content(request.file)
        if not content:
            return DefinitionResult(definitions=[])

        identifier = self._get_identifier_at_position(content, request.position)
        if not identifier:
            return DefinitionResult(definitions=[])

        # Search for symbol by name
        definitions = self._find_definitions(identifier, request.file)

        return DefinitionResult(
            symbol=definitions[0] if definitions else None, definitions=definitions
        )

    def _get_identifier_at_position(
        self, content: str, position: Position
    ) -> str | None:
        """Extract identifier at cursor position."""
        lines = content.split("\n")
        if position.line >= len(lines):
            return None

        line = lines[position.line]
        if position.column >= len(line):
            return None

        # Find word boundaries
        start = position.column
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        end = position.column
        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        if start == end:
            return None

        return line[start:end]

    def _find_definitions(self, name: str, current_file: str) -> list[Symbol]:
        """Find definition symbols for a name."""
        candidates = self._indexer.symbol_table.get_by_name(name)

        if not candidates:
            return []

        # Prioritize:
        # 1. Same file
        # 2. Imported files
        # 3. Exported symbols
        # 4. Other symbols

        same_file = [s for s in candidates if s.file == current_file]
        if same_file:
            return same_file

        imports = self._indexer.dependency_graph.get_imports(current_file)
        imported = [s for s in candidates if any(imp in s.file for imp in imports)]
        if imported:
            return imported

        exported = [s for s in candidates if s.is_exported]
        if exported:
            return exported

        return candidates[:5]  # Limit results
