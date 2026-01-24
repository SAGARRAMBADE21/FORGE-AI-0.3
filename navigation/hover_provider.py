"""Hover information provider."""

import logging

from core.types import HoverInfo, NavRequest, Position, Symbol, SymbolKind
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class HoverProvider:
    """Provide hover information for symbols."""

    def __init__(self, indexer: UnifiedIndexer):
        self._indexer = indexer

    async def get_hover(self, request: NavRequest) -> HoverInfo | None:
        """Get hover information for position."""
        symbol = self._indexer.symbol_table.get_at_position(
            request.file, request.position
        )

        if not symbol:
            return None

        content = self._build_hover_content(symbol)

        return HoverInfo(content=content, range=symbol.selection_range, symbol=symbol)

    def _build_hover_content(self, symbol: Symbol) -> str:
        """Build markdown hover content for a symbol."""
        parts = []

        # Header with kind and name
        kind_str = self._kind_label(symbol.kind)
        parts.append(f"**{kind_str}** `{symbol.name}`")

        # Get language from metadata with fallback
        language = symbol.metadata.get("language", "python")
        language_str = language.value if hasattr(language, "value") else str(language)

        # Signature
        if symbol.signature:
            parts.append(f"```{language_str}")
            parts.append(symbol.signature)
            parts.append("```")
        elif symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            sig = self._build_signature(symbol)
            parts.append(f"```{language_str}")
            parts.append(sig)
            parts.append("```")

        # Type annotation for variables/properties
        type_annotation = symbol.metadata.get("type_annotation")
        if type_annotation and symbol.kind in (
            SymbolKind.VARIABLE,
            SymbolKind.CONSTANT,
            SymbolKind.PROPERTY,
        ):
            parts.append(f"Type: `{type_annotation}`")

        # Inheritance
        bases = symbol.metadata.get("bases", [])
        interfaces = symbol.metadata.get("interfaces", [])
        if bases:
            parts.append(f"Extends: {', '.join(f'`{b}`' for b in bases)}")
        if interfaces:
            parts.append(f"Implements: {', '.join(f'`{i}`' for i in interfaces)}")

        # Docstring
        if symbol.docstring:
            parts.append("")
            parts.append("---")
            parts.append("")
            if symbol.docstring.summary:
                parts.append(symbol.docstring.summary)

            if symbol.docstring.params:
                parts.append("")
                parts.append("**Parameters:**")
                for name, desc in symbol.docstring.params.items():
                    parts.append(f"- `{name}`: {desc}")

            if symbol.docstring.returns:
                parts.append("")
                parts.append(f"**Returns:** {symbol.docstring.returns}")

        # Location
        parts.append("")
        parts.append(f"*Defined in {symbol.file}:{symbol.range.start.line + 1}*")

        return "\n".join(parts)

    def _kind_label(self, kind: SymbolKind) -> str:
        """Get human-readable label for symbol kind."""
        labels = {
            SymbolKind.FUNCTION: "function",
            SymbolKind.METHOD: "method",
            SymbolKind.CLASS: "class",
            SymbolKind.INTERFACE: "interface",
            SymbolKind.TYPE_ALIAS: "type",
            SymbolKind.VARIABLE: "variable",
            SymbolKind.CONSTANT: "constant",
            SymbolKind.PROPERTY: "property",
            SymbolKind.COMPONENT: "component",
            SymbolKind.HOOK: "hook",
            SymbolKind.ENUM: "enum",
            SymbolKind.ENUM_MEMBER: "enum member",
            SymbolKind.STRUCT: "struct",
            SymbolKind.TRAIT: "trait",
            SymbolKind.MODULE: "module",
        }
        return labels.get(kind, str(kind.value))

    def _build_signature(self, symbol: Symbol) -> str:
        """Build function signature string."""
        params = []
        for p in symbol.metadata.get("parameters", []):
            param_str = p.name
            if p.type:
                param_str += f": {p.type}"
            if p.default:
                param_str += f" = {p.default}"
            if p.optional and not p.default:
                param_str += "?"
            params.append(param_str)

        sig = f"{symbol.name}({', '.join(params)})"

        return_type = symbol.metadata.get("return_type")
        if return_type:
            sig += f" -> {return_type}"

        if symbol.is_async:
            sig = f"async {sig}"

        return sig
