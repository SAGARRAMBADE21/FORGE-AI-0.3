"""Symbol table for storing and querying symbols."""

import logging
import re
from collections import defaultdict
from typing import Iterator

from core.types import Position, Symbol, SymbolKind

logger = logging.getLogger(__name__)


class SymbolTable:
    """
    Symbol table with multiple indexes for fast lookup:
    - By ID
    - By name
    - By qualified name
    - By file
    - By kind
    """

    def __init__(self):
        self._symbols: dict[str, Symbol] = {}
        self._by_name: dict[str, list[str]] = defaultdict(list)
        self._by_qualified: dict[str, str] = {}
        self._by_file: dict[str, list[str]] = defaultdict(list)
        self._by_kind: dict[SymbolKind, list[str]] = defaultdict(list)

    def add(self, symbol: Symbol):
        """Add a symbol to the table."""
        symbol_id = symbol.metadata.get("id", f"{symbol.file}:{symbol.name}")
        qualified_name = symbol.metadata.get(
            "qualified_name", f"{symbol.file}:{symbol.name}"
        )

        self._symbols[symbol_id] = symbol
        self._by_name[symbol.name.lower()].append(symbol_id)
        self._by_qualified[qualified_name] = symbol_id
        self._by_file[symbol.file].append(symbol_id)
        self._by_kind[symbol.kind].append(symbol_id)

    def add_many(self, symbols: list[Symbol]):
        """Add multiple symbols."""
        for symbol in symbols:
            self.add(symbol)

    def get(self, symbol_id: str) -> Symbol | None:
        """Get symbol by ID."""
        return self._symbols.get(symbol_id)

    def get_by_name(self, name: str) -> list[Symbol]:
        """Get symbols by name (case-insensitive)."""
        ids = self._by_name.get(name.lower(), [])
        return [self._symbols[sid] for sid in ids if sid in self._symbols]

    def get_by_qualified_name(self, qualified_name: str) -> Symbol | None:
        """Get symbol by fully qualified name."""
        sid = self._by_qualified.get(qualified_name)
        return self._symbols.get(sid) if sid else None

    def get_by_file(self, file: str) -> list[Symbol]:
        """Get all symbols in a file."""
        ids = self._by_file.get(file, [])
        return [self._symbols[sid] for sid in ids if sid in self._symbols]

    def get_by_kind(self, kind: SymbolKind) -> list[Symbol]:
        """Get all symbols of a specific kind."""
        ids = self._by_kind.get(kind, [])
        return [self._symbols[sid] for sid in ids if sid in self._symbols]

    def get_at_position(self, file: str, position: Position) -> Symbol | None:
        """Get symbol at a specific position."""
        symbols = self.get_by_file(file)

        # Find the most specific symbol containing the position
        best_match = None
        best_size = float("inf")

        for symbol in symbols:
            # Check selection_range from metadata if available
            selection_range = symbol.metadata.get("selection_range")
            if (
                selection_range
                and hasattr(selection_range, "contains")
                and selection_range.contains(position)
            ):
                size = (
                    selection_range.lines
                    if hasattr(selection_range, "lines")
                    else float("inf")
                )
                if size < best_size:
                    best_match = symbol
                    best_size = size
            elif symbol.range.contains(position):
                size = (
                    symbol.range.lines
                    if hasattr(symbol.range, "lines")
                    else float("inf")
                )
                if best_match is None or size < best_size:
                    best_match = symbol
                    best_size = size

        return best_match

    def search(
        self, query: str, kinds: list[SymbolKind] | None = None, max_results: int = 50
    ) -> list[Symbol]:
        """Search symbols by name pattern."""
        query_lower = query.lower()
        results = []

        # Exact match first
        for name, ids in self._by_name.items():
            if name == query_lower:
                for sid in ids:
                    if sid in self._symbols:
                        symbol = self._symbols[sid]
                        if kinds is None or symbol.kind in kinds:
                            results.append((symbol, 100))  # Exact match score

        # Prefix match
        for name, ids in self._by_name.items():
            if name.startswith(query_lower) and name != query_lower:
                for sid in ids:
                    if sid in self._symbols:
                        symbol = self._symbols[sid]
                        if kinds is None or symbol.kind in kinds:
                            results.append((symbol, 80))

        # Contains match
        for name, ids in self._by_name.items():
            if query_lower in name and not name.startswith(query_lower):
                for sid in ids:
                    if sid in self._symbols:
                        symbol = self._symbols[sid]
                        if kinds is None or symbol.kind in kinds:
                            results.append((symbol, 60))

        # Fuzzy match (camelCase/snake_case parts)
        query_parts = set(re.findall(r"[a-z]+", query_lower))
        if query_parts:
            for name, ids in self._by_name.items():
                name_parts = set(re.findall(r"[a-z]+", name))
                if query_parts & name_parts and query_lower not in name:
                    for sid in ids:
                        if sid in self._symbols:
                            symbol = self._symbols[sid]
                            if kinds is None or symbol.kind in kinds:
                                overlap = len(query_parts & name_parts) / len(
                                    query_parts
                                )
                                results.append((symbol, int(40 * overlap)))

        # Sort by score and deduplicate
        seen = set()
        sorted_results = []
        for symbol, score in sorted(results, key=lambda x: -x[1]):
            if symbol.id not in seen:
                seen.add(symbol.id)
                sorted_results.append(symbol)
                if len(sorted_results) >= max_results:
                    break

        return sorted_results

    def remove_file(self, file: str):
        """Remove all symbols from a file."""
        ids = self._by_file.pop(file, [])

        for sid in ids:
            if sid in self._symbols:
                symbol = self._symbols[sid]

                # Remove from name index
                name_lower = symbol.name.lower()
                if name_lower in self._by_name:
                    self._by_name[name_lower] = [
                        s for s in self._by_name[name_lower] if s != sid
                    ]

                # Remove from qualified index
                self._by_qualified.pop(symbol.qualified_name, None)

                # Remove from kind index
                if symbol.kind in self._by_kind:
                    self._by_kind[symbol.kind] = [
                        s for s in self._by_kind[symbol.kind] if s != sid
                    ]

                # Remove symbol
                del self._symbols[sid]

    def clear(self):
        """Clear all symbols."""
        self._symbols.clear()
        self._by_name.clear()
        self._by_qualified.clear()
        self._by_file.clear()
        self._by_kind.clear()

    def __len__(self) -> int:
        return len(self._symbols)

    def __iter__(self) -> Iterator[Symbol]:
        return iter(self._symbols.values())

    def all_symbols(self) -> list[Symbol]:
        """Get all symbols."""
        return list(self._symbols.values())
