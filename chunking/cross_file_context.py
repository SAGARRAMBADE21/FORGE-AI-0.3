"""Cross-file context builder for understanding code relationships."""

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

from config.settings import Language, settings
from core.types import Chunk, CrossFileContext, Symbol, SymbolKind

logger = logging.getLogger(__name__)


class CrossFileContextBuilder:
    """
    Builds cross-file context for chunks to understand dependencies and relationships.

    Tracks imports, exports, function calls, and type usage across files.
    """

    def __init__(self):
        # Import graph: file -> files it imports
        self._import_graph: Dict[str, Set[str]] = defaultdict(set)

        # Reverse import graph: file -> files that import it
        self._imported_by: Dict[str, Set[str]] = defaultdict(set)

        # Call graph: symbol_id -> symbol_ids it calls
        self._call_graph: Dict[str, Set[str]] = defaultdict(set)

        # Reverse call graph: symbol_id -> symbol_ids that call it
        self._callers: Dict[str, Set[str]] = defaultdict(set)

        # Type dependencies: file -> types it uses
        self._type_dependencies: Dict[str, Set[str]] = defaultdict(set)

        # Symbol definitions: symbol_name -> file location
        self._symbol_locations: Dict[str, List[str]] = defaultdict(list)

        self.max_cross_refs = settings.chunking.max_cross_refs

    def build_graphs(
        self, symbols_by_file: Dict[str, List[Symbol]], contents: Dict[str, str]
    ) -> None:
        """
        Build cross-file relationship graphs.

        Args:
            symbols_by_file: Symbols organized by file
            contents: File contents by file path
        """
        logger.info(f"Building cross-file context for {len(symbols_by_file)} files")

        # Clear existing data
        self._import_graph.clear()
        self._imported_by.clear()
        self._call_graph.clear()
        self._callers.clear()
        self._type_dependencies.clear()
        self._symbol_locations.clear()

        # Build symbol location index
        self._build_symbol_index(symbols_by_file)

        # Build import graphs
        for file, symbols in symbols_by_file.items():
            content = contents.get(file, "")
            if not content:
                continue

            # Determine language
            lang = self._detect_language(file, symbols)

            # Extract imports
            imports = self._extract_imports(content, lang, file)
            self._import_graph[file] = set(imports)

            # Build reverse import graph
            for imported_file in imports:
                self._imported_by[imported_file].add(file)

            # Extract type dependencies
            type_deps = self._extract_type_dependencies(content, lang)
            self._type_dependencies[file] = set(type_deps)

        # Build call graphs
        self._build_call_graphs(symbols_by_file, contents)

        logger.info(
            f"Built graphs: {len(self._import_graph)} import edges, "
            f"{len(self._call_graph)} call edges"
        )

    def get_context_for_chunk(self, chunk: Chunk, file: str) -> CrossFileContext:
        """
        Get cross-file context for a specific chunk.

        Args:
            chunk: Chunk to get context for
            file: File path the chunk belongs to

        Returns:
            CrossFileContext with relevant relationships
        """
        ctx = CrossFileContext(file=file)

        # Get imports for this file
        ctx.imports = list(self._import_graph.get(file, set()))[: self.max_cross_refs]

        # Get files that import this file
        ctx.imported_by = list(self._imported_by.get(file, set()))[
            : self.max_cross_refs
        ]

        # Get exports from this file
        ctx.exports = self._get_file_exports(file, chunk)

        # Get symbol-specific context if available
        symbol_id = chunk.metadata.get("id") if hasattr(chunk, "metadata") else None
        if symbol_id:
            # Functions/methods this symbol calls
            ctx.dependencies = list(self._call_graph.get(symbol_id, set()))[
                : self.max_cross_refs
            ]

        # Add type dependencies
        if file in self._type_dependencies:
            # Store in metadata as it's not a direct field
            if not hasattr(chunk, "metadata"):
                chunk.metadata = {}
            chunk.metadata["type_dependencies"] = list(self._type_dependencies[file])[
                : self.max_cross_refs
            ]

        return ctx

    def _build_symbol_index(self, symbols_by_file: Dict[str, List[Symbol]]) -> None:
        """Build index of symbol names to their file locations."""
        for file, symbols in symbols_by_file.items():
            for symbol in symbols:
                self._symbol_locations[symbol.name].append(file)

    def _build_call_graphs(
        self, symbols_by_file: Dict[str, List[Symbol]], contents: Dict[str, str]
    ) -> None:
        """Build function/method call graphs."""
        # First pass: collect all symbol names and IDs
        symbol_name_to_id = {}
        for file, symbols in symbols_by_file.items():
            for sym in symbols:
                sym_id = (
                    sym.metadata.get("id") if hasattr(sym, "metadata") else sym.name
                )
                symbol_name_to_id[sym.name] = sym_id

        # Second pass: find calls
        for file, symbols in symbols_by_file.items():
            for sym in symbols:
                if sym.kind not in (
                    SymbolKind.FUNCTION,
                    SymbolKind.METHOD,
                    SymbolKind.HOOK,
                ):
                    continue

                sym_id = (
                    sym.metadata.get("id") if hasattr(sym, "metadata") else sym.name
                )
                source = sym.signature if sym.signature else ""

                # Find function calls in the signature/source
                calls = self._extract_function_calls(source)

                for called_name in calls:
                    if called_name in symbol_name_to_id and called_name != sym.name:
                        called_id = symbol_name_to_id[called_name]
                        self._call_graph[sym_id].add(called_name)
                        self._callers[called_id].add(sym.name)

    def _extract_imports(
        self, content: str, lang: Language, current_file: str
    ) -> List[str]:
        """
        Extract imported files/modules from source code.

        Args:
            content: Source code content
            lang: Programming language
            current_file: Current file path for resolving relative imports

        Returns:
            List of imported file/module paths
        """
        imports = []

        if lang in (
            Language.TYPESCRIPT,
            Language.TSX,
            Language.JAVASCRIPT,
            Language.JSX,
        ):
            # ES6 imports: import ... from 'path'
            imports.extend(
                m.group(1)
                for m in re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
            )

            # CommonJS requires: require('path')
            imports.extend(
                m.group(1)
                for m in re.finditer(
                    r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content
                )
            )

            # Dynamic imports: import('path')
            imports.extend(
                m.group(1)
                for m in re.finditer(r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content)
            )

        elif lang == Language.PYTHON:
            # from module import ...
            for m in re.finditer(r"^from\s+(\S+)\s+import", content, re.MULTILINE):
                imports.append(m.group(1))

            # import module
            for m in re.finditer(r"^import\s+(\S+)", content, re.MULTILINE):
                imports.append(m.group(1).split(",")[0].strip())

        elif lang == Language.GO:
            # import "path"
            imports.extend(
                m.group(1)
                for m in re.finditer(r'import\s+[\'"]([^\'"]+)[\'"]', content)
            )

            # import ( ... )
            import_blocks = re.finditer(r"import\s+\((.*?)\)", content, re.DOTALL)
            for block in import_blocks:
                block_imports = re.findall(r'[\'"]([^\'"]+)[\'"]', block.group(1))
                imports.extend(block_imports)

        elif lang == Language.RUST:
            # use path;
            imports.extend(
                m.group(1).strip() for m in re.finditer(r"use\s+([^;]+);", content)
            )

        elif lang == Language.JAVA:
            # import package.Class;
            imports.extend(
                m.group(1) for m in re.finditer(r"import\s+([\w.]+);", content)
            )

        # Resolve relative imports to absolute paths if possible
        resolved_imports = []
        for imp in imports:
            resolved = self._resolve_import_path(imp, current_file, lang)
            if resolved:
                resolved_imports.append(resolved)

        return resolved_imports[:20]  # Limit to prevent explosion

    def _resolve_import_path(
        self, import_path: str, current_file: str, lang: Language
    ) -> str:
        """
        Resolve relative import paths to absolute paths.

        Args:
            import_path: Import path from source
            current_file: Current file path
            lang: Programming language

        Returns:
            Resolved import path
        """
        # For JS/TS, handle relative imports
        if lang in (
            Language.TYPESCRIPT,
            Language.TSX,
            Language.JAVASCRIPT,
            Language.JSX,
        ):
            if import_path.startswith("."):
                current_dir = str(Path(current_file).parent)
                resolved = str(Path(current_dir) / import_path)
                return resolved

        # For Python, convert module paths
        if lang == Language.PYTHON:
            # Convert module.submodule to file path
            return import_path.replace(".", "/")

        return import_path

    def _extract_type_dependencies(self, content: str, lang: Language) -> List[str]:
        """Extract type/interface dependencies from source code."""
        types = []

        if lang in (Language.TYPESCRIPT, Language.TSX):
            # Type annotations: : TypeName
            types.extend(
                m.group(1) for m in re.finditer(r":\s*([A-Z][a-zA-Z0-9_]*)", content)
            )

            # Generic types: Array<Type>
            types.extend(
                m.group(1) for m in re.finditer(r"<([A-Z][a-zA-Z0-9_]*)>", content)
            )

            # Interface/type definitions
            types.extend(
                m.group(1)
                for m in re.finditer(
                    r"(?:interface|type)\s+([A-Z][a-zA-Z0-9_]*)", content
                )
            )

        return list(set(types))[:20]

    def _extract_function_calls(self, source: str) -> List[str]:
        """Extract function/method calls from source code."""
        # Match function calls: functionName(
        calls = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", source)

        # Filter out common keywords
        keywords = {
            "if",
            "while",
            "for",
            "switch",
            "catch",
            "print",
            "len",
            "range",
            "typeof",
            "new",
            "delete",
        }

        return [call for call in calls if call not in keywords]

    def _detect_language(self, file: str, symbols: List[Symbol]) -> Language:
        """Detect language from file extension or symbols."""
        ext = Path(file).suffix.lower()

        from config.settings import EXTENSION_MAP

        return EXTENSION_MAP.get(ext, Language.UNKNOWN)

    def _get_file_exports(self, file: str, chunk: Chunk) -> List[str]:
        """Get exported symbols from a file."""
        exports = []

        # Check chunk content for export statements
        content = chunk.content if hasattr(chunk, "content") else ""

        # ES6 exports
        exports.extend(
            m.group(1)
            for m in re.finditer(
                r"export\s+(?:const|let|var|function|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                content,
            )
        )

        # export default
        if "export default" in content:
            exports.append("default")

        # Python __all__
        all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if all_match:
            exports.extend(
                name.strip().strip("'\"") for name in all_match.group(1).split(",")
            )

        return exports[: self.max_cross_refs]

    def get_related_files(self, file: str, max_depth: int = 2) -> Set[str]:
        """
        Get files related to the given file through imports.

        Args:
            file: File path
            max_depth: Maximum depth to traverse

        Returns:
            Set of related file paths
        """
        related = set()
        visited = set()
        to_visit = [(file, 0)]

        while to_visit:
            current, depth = to_visit.pop(0)

            if current in visited or depth > max_depth:
                continue

            visited.add(current)

            # Add imports
            for imported in self._import_graph.get(current, set()):
                related.add(imported)
                if depth < max_depth:
                    to_visit.append((imported, depth + 1))

            # Add importers
            for importer in self._imported_by.get(current, set()):
                related.add(importer)
                if depth < max_depth:
                    to_visit.append((importer, depth + 1))

        related.discard(file)  # Remove the original file
        return related


_cross_file_builder: CrossFileContextBuilder | None = None


def get_cross_file_builder() -> CrossFileContextBuilder:
    """Get singleton cross-file context builder instance."""
    global _cross_file_builder
    if _cross_file_builder is None:
        _cross_file_builder = CrossFileContextBuilder()
    return _cross_file_builder
