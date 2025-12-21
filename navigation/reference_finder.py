"""Find-all-references functionality."""

import re
import logging

from core.types import (
    Symbol, NavRequest, ReferenceResult, Reference, 
    Location, Range, Position, ReferenceKind, SymbolKind
)
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class ReferenceFinder:
    """Find all references to a symbol."""

    def __init__(self, indexer: UnifiedIndexer):
        self._indexer = indexer

    async def find_references(
        self, 
        request: NavRequest, 
        include_definition: bool = True
    ) -> ReferenceResult:
        """Find all references to symbol at position."""
        # Find symbol at position
        symbol = self._indexer.symbol_table.get_at_position(request.file, request.position)
        
        if not symbol:
            # Try to find by identifier
            content = self._indexer.get_file_content(request.file)
            if content:
                identifier = self._get_identifier(content, request.position)
                if identifier:
                    symbols = self._indexer.symbol_table.get_by_name(identifier)
                    if symbols:
                        symbol = symbols[0]
        
        if not symbol:
            return ReferenceResult(
                symbol=Symbol(
                    id="", name="", qualified_name="", kind=SymbolKind.UNKNOWN,
                    file="", range=Range(Position(0, 0), Position(0, 0)),
                    selection_range=Range(Position(0, 0), Position(0, 0))
                ),
                references=[]
            )
        
        references = self._find_all_references(symbol, include_definition)
        
        return ReferenceResult(
            symbol=symbol,
            references=references
        )

    def _find_all_references(self, symbol: Symbol, include_definition: bool) -> list[Reference]:
        """Find all references to a symbol across the codebase."""
        references = []
        name = symbol.name
        
        # Note: include_definition parameter not used since ReferenceKind.DEFINITION doesn't exist
        # Just find all references in files
        
        # Search in all files
        for file_info in self._indexer.file_index.all_files():
            content = self._indexer.get_file_content(file_info.path)
            if not content:
                continue
            
            file_refs = self._find_references_in_file(
                name, content, file_info.path, symbol.id,
                exclude_definition=(file_info.path == symbol.file)
            )
            references.extend(file_refs)
        
        return references

    def _find_references_in_file(
        self, 
        name: str, 
        content: str, 
        file: str,
        symbol_id: str,
        exclude_definition: bool = False
    ) -> list[Reference]:
        """Find references in a single file."""
        references = []
        lines = content.split('\n')
        
        # Use word boundary regex
        pattern = re.compile(r'\b' + re.escape(name) + r'\b')
        
        for line_num, line in enumerate(lines):
            for match in pattern.finditer(line):
                col = match.start()
                
                # Determine reference kind
                kind = self._determine_reference_kind(line, col, name)
                
                # Note: exclude_definition not used since ReferenceKind.DEFINITION doesn't exist
                
                references.append(Reference(
                    symbol=symbol_id,
                    location=Location(
                        file,
                        Range(
                            Position(line_num, col),
                            Position(line_num, col + len(name))
                        )
                    ),
                    kind=kind,
                    context=line.strip()
                ))
        
        return references

    def _determine_reference_kind(self, line: str, col: int, name: str) -> ReferenceKind:
        """Determine the kind of reference."""
        before = line[:col].strip()
        after = line[col + len(name):].strip()
        
        # Assignment (write)
        if after.startswith('=') and not after.startswith('=='):
            return ReferenceKind.WRITE
        
        # Function call
        if after.startswith('('):
            return ReferenceKind.CALL
        
        # Import
        if 'import' in before or 'from' in before:
            return ReferenceKind.IMPORT
        
        # Export
        if 'export' in before:
            return ReferenceKind.EXPORT
        
        # Type reference
        if ':' in before or '<' in before or 'extends' in before or 'implements' in before:
            return ReferenceKind.TYPE_REF
        
        return ReferenceKind.READ

    def _get_container(self, file: str, line: int) -> str | None:
        """Get the containing function/class for a line."""
        symbols = self._indexer.symbol_table.get_by_file(file)
        
        for symbol in symbols:
            if (symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD, 
                               SymbolKind.CLASS, SymbolKind.COMPONENT) and
                symbol.range.start.line <= line <= symbol.range.end.line):
                return symbol.name
        
        return None

    def _get_identifier(self, content: str, position: Position) -> str | None:
        """Get identifier at position."""
        lines = content.split('\n')
        if position.line >= len(lines):
            return None
        
        line = lines[position.line]
        start = position.column
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == '_'):
            start -= 1
        
        end = position.column
        while end < len(line) and (line[end].isalnum() or line[end] == '_'):
            end += 1
        
        return line[start:end] if start < end else None