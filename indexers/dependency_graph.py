"""Dependency graph for tracking file and symbol relationships."""

import logging
import re
from collections import defaultdict
from pathlib import Path

from config.settings import Language
from core.types import Symbol, SymbolKind

logger = logging.getLogger(__name__)


class DependencyGraph:
    """
    Track dependencies between files and symbols:
    - Import/export relationships
    - Call graph
    - Type dependencies
    """

    def __init__(self):
        # File-level dependencies
        self._imports: dict[str, set[str]] = defaultdict(
            set
        )  # file -> imported modules
        self._imported_by: dict[str, set[str]] = defaultdict(
            set
        )  # module -> importing files

        # Symbol-level dependencies
        self._calls: dict[str, set[str]] = defaultdict(
            set
        )  # symbol_id -> called symbol names
        self._called_by: dict[str, set[str]] = defaultdict(
            set
        )  # symbol_name -> caller symbol names
        self._type_refs: dict[str, set[str]] = defaultdict(
            set
        )  # symbol_id -> referenced type names

    def build_from_files(
        self, contents: dict[str, str], languages: dict[str, Language]
    ):
        """Build import graph from file contents."""
        self._imports.clear()
        self._imported_by.clear()

        for file, content in contents.items():
            lang = languages.get(file, Language.UNKNOWN)
            imports = self._extract_imports(content, lang)
            self._imports[file] = set(imports)

            for imp in imports:
                self._imported_by[imp].add(file)

    def build_call_graph(self, symbols: list[Symbol]):
        """Build call graph from symbols."""
        self._calls.clear()
        self._called_by.clear()

        # Create name -> symbol mapping
        symbol_names = {s.name: s for s in symbols}

        for symbol in symbols:
            if symbol.kind not in (
                SymbolKind.FUNCTION,
                SymbolKind.METHOD,
                SymbolKind.HOOK,
                SymbolKind.COMPONENT,
            ):
                continue

            # Find function calls in source
            source = symbol.metadata.get("source", "")
            calls = re.findall(r"\b(\w+)\s*\(", source)

            for call_name in calls:
                if call_name in symbol_names and call_name != symbol.name:
                    self._calls[symbol.id].add(call_name)
                    self._called_by[call_name].add(symbol.name)

    def build_type_refs(self, symbols: list[Symbol]):
        """Build type reference graph."""
        self._type_refs.clear()

        # Get all type names
        type_names = {
            s.name
            for s in symbols
            if s.kind
            in (
                SymbolKind.CLASS,
                SymbolKind.INTERFACE,
                SymbolKind.TYPE_ALIAS,
                SymbolKind.STRUCT,
            )
        }

        for symbol in symbols:
            # Check type annotations
            type_annotation = symbol.metadata.get("type_annotation")
            if type_annotation:
                for type_name in type_names:
                    if type_name in type_annotation:
                        self._type_refs[symbol.id].add(type_name)

            # Check return type
            return_type = symbol.metadata.get("return_type")
            if return_type:
                for type_name in type_names:
                    if type_name in return_type:
                        self._type_refs[symbol.id].add(type_name)

            # Check parameter types
            for param in symbol.metadata.get("parameters", []):
                if param.param_type:
                    for type_name in type_names:
                        if type_name in param.param_type:
                            self._type_refs[symbol.id].add(type_name)

    def get_imports(self, file: str) -> list[str]:
        """Get imports for a file."""
        return list(self._imports.get(file, set()))

    def get_imported_by(self, module: str) -> list[str]:
        """Get files that import a module."""
        return list(self._imported_by.get(module, set()))

    def get_calls(self, symbol_id: str) -> list[str]:
        """Get symbols called by a symbol."""
        return list(self._calls.get(symbol_id, set()))

    def get_callers(self, symbol_name: str) -> list[str]:
        """Get symbols that call a symbol."""
        return list(self._called_by.get(symbol_name, set()))

    def get_type_refs(self, symbol_id: str) -> list[str]:
        """Get type references for a symbol."""
        return list(self._type_refs.get(symbol_id, set()))

    def get_related_files(self, file: str, depth: int = 1) -> set[str]:
        """Get files related to a file (imports and importers)."""
        related = set()
        to_visit = {file}
        visited = set()

        for _ in range(depth):
            next_visit = set()
            for f in to_visit:
                if f in visited:
                    continue
                visited.add(f)

                # Add imports
                imports = self._imports.get(f, set())
                related.update(imports)
                next_visit.update(imports)

                # Add importers
                importers = self._imported_by.get(f, set())
                related.update(importers)
                next_visit.update(importers)

            to_visit = next_visit - visited

        return related - {file}

    def _extract_imports(self, content: str, language: Language) -> list[str]:
        """Extract import statements from content."""
        imports = []

        if language in (
            Language.TYPESCRIPT,
            Language.TSX,
            Language.JAVASCRIPT,
            Language.JSX,
        ):
            # ES6 imports
            for m in re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content):
                imports.append(m.group(1))
            # require()
            for m in re.finditer(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content):
                imports.append(m.group(1))

        elif language == Language.PYTHON:
            for m in re.finditer(
                r"^(?:from\s+(\S+)|import\s+(\S+))", content, re.MULTILINE
            ):
                imports.append(m.group(1) or m.group(2))

        elif language == Language.GO:
            for m in re.finditer(r'import\s+(?:\(\s*)?[\'"]([^\'"]+)[\'"]', content):
                imports.append(m.group(1))

        elif language == Language.RUST:
            for m in re.finditer(r"use\s+([^;{]+)", content):
                imports.append(m.group(1).strip())

        elif language == Language.JAVA:
            for m in re.finditer(r"import\s+([\w.]+)", content):
                imports.append(m.group(1))

        return imports[:50]  # Limit

    def clear(self):
        """Clear all graphs."""
        self._imports.clear()
        self._imported_by.clear()
        self._calls.clear()
        self._called_by.clear()
        self._type_refs.clear()
