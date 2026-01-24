"""Call hierarchy functionality."""

import logging
import re

from core.types import (
    CallHierarchyItem,
    CallHierarchyResult,
    IncomingCall,
    NavRequest,
    OutgoingCall,
    Position,
    Range,
    Symbol,
    SymbolKind,
)
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class CallHierarchyAnalyzer:
    """Analyze call hierarchy for functions/methods."""

    def __init__(self, indexer: UnifiedIndexer):
        self._indexer = indexer

    async def get_hierarchy(self, request: NavRequest) -> CallHierarchyResult | None:
        """Get call hierarchy for function at position."""
        symbol = self._indexer.symbol_table.get_at_position(
            request.file, request.position
        )

        if not symbol or symbol.kind not in (
            SymbolKind.FUNCTION,
            SymbolKind.METHOD,
            SymbolKind.HOOK,
            SymbolKind.COMPONENT,
        ):
            return None

        item = CallHierarchyItem(
            id=symbol.id,
            name=symbol.name,
            kind=symbol.kind,
            file=symbol.file,
            range=symbol.range,
            signature=symbol.signature or symbol.name,
        )

        incoming = self._get_incoming_calls(symbol)
        outgoing = self._get_outgoing_calls(symbol)

        return CallHierarchyResult(item=item, incoming=incoming, outgoing=outgoing)

    def _get_incoming_calls(self, symbol: Symbol) -> list[IncomingCall]:
        """Get functions that call this symbol."""
        incoming = []
        callers = self._indexer.dependency_graph.get_callers(symbol.name)

        for caller_name in callers:
            caller_symbols = self._indexer.symbol_table.get_by_name(caller_name)

            for caller in caller_symbols:
                if caller.kind in (
                    SymbolKind.FUNCTION,
                    SymbolKind.METHOD,
                    SymbolKind.HOOK,
                    SymbolKind.COMPONENT,
                ):
                    sites = self._find_call_sites(caller, symbol.name)

                    incoming.append(
                        IncomingCall(
                            caller=CallHierarchyItem(
                                id=caller.id,
                                name=caller.name,
                                kind=caller.kind,
                                file=caller.file,
                                range=caller.range,
                                signature=caller.signature or caller.name,
                            ),
                            sites=sites,
                        )
                    )

        return incoming

    def _get_outgoing_calls(self, symbol: Symbol) -> list[OutgoingCall]:
        """Get functions called by this symbol."""
        outgoing = []
        callees = self._indexer.dependency_graph.get_calls(symbol.id)

        for callee_name in callees:
            callee_symbols = self._indexer.symbol_table.get_by_name(callee_name)

            for callee in callee_symbols:
                if callee.kind in (
                    SymbolKind.FUNCTION,
                    SymbolKind.METHOD,
                    SymbolKind.HOOK,
                    SymbolKind.COMPONENT,
                ):
                    sites = self._find_call_sites(symbol, callee.name)

                    outgoing.append(
                        OutgoingCall(
                            callee=CallHierarchyItem(
                                id=callee.id,
                                name=callee.name,
                                kind=callee.kind,
                                file=callee.file,
                                range=callee.range,
                                signature=callee.signature or callee.name,
                            ),
                            sites=sites,
                        )
                    )

        return outgoing

    def _find_call_sites(self, container: Symbol, callee_name: str) -> list[Range]:
        """Find locations where callee is called within container."""
        sites = []

        if not container.source:
            return sites

        lines = container.source.split("\n")
        pattern = re.compile(r"\b" + re.escape(callee_name) + r"\s*\(")

        for i, line in enumerate(lines):
            for match in pattern.finditer(line):
                sites.append(
                    Range(
                        Position(container.range.start.line + i, match.start()),
                        Position(container.range.start.line + i, match.end() - 1),
                    )
                )

        return sites
