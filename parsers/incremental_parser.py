"""Incremental parser with multi-language support."""

import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator
from tree_sitter import Node, Tree, Parser

from core.types import Symbol, SymbolKind, Parameter, Range, Position, Comment, Docstring, ParseError
from core.utils import generate_id, compute_hash
from config.settings import Language, settings
from parsers.language_registry import get_registry
from parsers.comment_extractor import get_comment_extractor
from parsers.error_recovery import get_error_recovery

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    symbols: list[Symbol]
    comments: list[Comment]
    errors: list[ParseError]
    tree: Tree | None
    language: Language
    success: bool


@dataclass
class IncrementalChange:
    start_byte: int
    old_end_byte: int
    new_end_byte: int
    start_point: tuple[int, int]
    old_end_point: tuple[int, int]
    new_end_point: tuple[int, int]


class IncrementalParser:
    def __init__(self):
        self._registry = get_registry()
        self._comments = get_comment_extractor()
        self._recovery = get_error_recovery()
        self._cache: dict[str, tuple[str, Tree, list[Symbol]]] = {}

    def parse_file(self, file_path: str) -> ParseResult:
        path = Path(file_path)
        if not path.exists():
            return ParseResult([], [], [], None, Language.UNKNOWN, False)
        try:
            content = path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Read error {file_path}: {e}")
            return ParseResult([], [], [], None, Language.UNKNOWN, False)
        return self.parse_content(content, file_path)

    def parse_content(self, content: str, file_path: str, language: Language | None = None) -> ParseResult:
        if language is None:
            language = self._registry.detect_language(file_path)

        if language == Language.UNKNOWN or not self._registry.is_supported(language):
            return self._parse_unsupported(content, file_path, language)

        parser = self._registry.get_parser(language)
        if not parser:
            return self._parse_unsupported(content, file_path, language)

        try:
            tree = parser.parse(bytes(content, 'utf-8'))
        except Exception as e:
            logger.error(f"Parse error {file_path}: {e}")
            return ParseResult([], [], [], None, language, False)

        errors = self._recovery.find_errors(tree.root_node, file_path)

        if errors and settings.parser.error_recovery:
            patched, _ = self._recovery.attempt_recovery(content, errors, language)
            if patched:
                try:
                    tree = parser.parse(bytes(patched, 'utf-8'))
                    errors = self._recovery.find_errors(tree.root_node, file_path)
                except Exception:
                    pass

        symbols = list(self._extract_symbols(tree.root_node, content, file_path, language))

        comments = []
        if settings.parser.extract_comments:
            comments = self._comments.extract_comments(content, language)
            self._associate_comments(comments, symbols)

        self._cache[file_path] = (compute_hash(content), tree, symbols)

        return ParseResult(symbols, comments, errors, tree, language, True)

    def parse_incremental(self, file_path: str, content: str, changes: list[IncrementalChange]) -> ParseResult:
        language = self._registry.detect_language(file_path)
        if file_path not in self._cache or not self._registry.is_supported(language):
            return self.parse_content(content, file_path, language)

        _, old_tree, _ = self._cache[file_path]
        parser = self._registry.get_parser(language)
        if not parser:
            return self.parse_content(content, file_path, language)

        for change in changes:
            old_tree.edit(
                start_byte=change.start_byte,
                old_end_byte=change.old_end_byte,
                new_end_byte=change.new_end_byte,
                start_point=change.start_point,
                old_end_point=change.old_end_point,
                new_end_point=change.new_end_point
            )

        try:
            new_tree = parser.parse(bytes(content, 'utf-8'), old_tree)
        except Exception as e:
            logger.error(f"Incremental parse error: {e}")
            return self.parse_content(content, file_path, language)

        symbols = list(self._extract_symbols(new_tree.root_node, content, file_path, language))
        errors = self._recovery.find_errors(new_tree.root_node, file_path)

        comments = []
        if settings.parser.extract_comments:
            comments = self._comments.extract_comments(content, language)
            self._associate_comments(comments, symbols)

        self._cache[file_path] = (compute_hash(content), new_tree, symbols)
        return ParseResult(symbols, comments, errors, new_tree, language, True)

    def invalidate(self, file_path: str):
        self._cache.pop(file_path, None)

    def clear(self):
        self._cache.clear()

    def _extract_symbols(self, node: Node, content: str, file: str, lang: Language,
                         parent_id: str | None = None, parent_name: str | None = None) -> Iterator[Symbol]:
        if lang in (Language.TYPESCRIPT, Language.TSX, Language.JAVASCRIPT, Language.JSX):
            yield from self._extract_js_ts(node, content, file, lang, parent_id, parent_name)
        elif lang == Language.PYTHON:
            yield from self._extract_python(node, content, file, lang, parent_id, parent_name)
        elif lang == Language.GO:
            yield from self._extract_go(node, content, file, lang, parent_id, parent_name)
        elif lang == Language.RUST:
            yield from self._extract_rust(node, content, file, lang, parent_id, parent_name)
        elif lang == Language.JAVA:
            yield from self._extract_java(node, content, file, lang, parent_id, parent_name)
        elif lang in (Language.C, Language.CPP):
            yield from self._extract_c(node, content, file, lang, parent_id, parent_name)
        else:
            for child in node.children:
                yield from self._extract_symbols(child, content, file, lang, parent_id, parent_name)

    def _extract_js_ts(self, node: Node, content: str, file: str, lang: Language,
                       parent_id: str | None, parent_name: str | None) -> Iterator[Symbol]:
        if node.type in ('function_declaration', 'generator_function_declaration'):
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.FUNCTION, parent_id, parent_name)
                sym.parameters = self._js_params(node)
                sym.return_type = self._js_return(node)
                sym.is_async = b'async' in content[node.start_byte:node.start_byte+20].encode()
                sym.signature = self._signature(sym)
                name = name_node.text.decode()
                if name[0].isupper() and lang in (Language.TSX, Language.JSX):
                    body = node.child_by_field_name('body')
                    if body and b'<' in body.text:
                        sym.kind = SymbolKind.COMPONENT
                if name.startswith('use') and len(name) > 3 and name[3].isupper():
                    sym.kind = SymbolKind.HOOK
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    yield from self._extract_js_ts(body, content, file, lang, sym.id, sym.name)
                return

        if node.type == 'lexical_declaration':
            for child in node.children:
                if child.type == 'variable_declarator':
                    name_node = child.child_by_field_name('name')
                    value_node = child.child_by_field_name('value')
                    if name_node and value_node and value_node.type in ('arrow_function', 'function', 'function_expression'):
                        sym = self._create_symbol(child, name_node, content, file, lang, SymbolKind.FUNCTION, parent_id, parent_name)
                        sym.parameters = self._js_params(value_node)
                        sym.return_type = self._js_return(value_node)
                        sym.is_async = b'async' in content[value_node.start_byte:value_node.start_byte+20].encode()
                        sym.signature = self._signature(sym)
                        name = name_node.text.decode()
                        if name[0].isupper() and lang in (Language.TSX, Language.JSX):
                            body = value_node.child_by_field_name('body')
                            if body and b'<' in body.text:
                                sym.kind = SymbolKind.COMPONENT
                        if name.startswith('use') and len(name) > 3 and name[3].isupper():
                            sym.kind = SymbolKind.HOOK
                        yield sym
                        body = value_node.child_by_field_name('body')
                        if body:
                            yield from self._extract_js_ts(body, content, file, lang, sym.id, sym.name)
                    elif name_node:
                        kind = SymbolKind.CONSTANT if b'const' in node.text[:10] else SymbolKind.VARIABLE
                        yield self._create_symbol(child, name_node, content, file, lang, kind, parent_id, parent_name)

        if node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.CLASS, parent_id, parent_name)
                sym.metadata['bases'] = []
                sym.metadata['interfaces'] = []
                for child in node.children:
                    if child.type == 'class_heritage':
                        for h in child.children:
                            if h.type == 'extends_clause':
                                for t in h.children:
                                    if t.type == 'identifier':
                                        sym.metadata['bases'].append(t.text.decode())
                            elif h.type == 'implements_clause':
                                for t in h.children:
                                    if t.type in ('identifier', 'type_identifier'):
                                        sym.metadata['interfaces'].append(t.text.decode())
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    yield from self._extract_js_ts(body, content, file, lang, sym.id, sym.name)
                return

        if node.type == 'interface_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                yield self._create_symbol(node, name_node, content, file, lang, SymbolKind.INTERFACE, parent_id, parent_name)
                return

        if node.type == 'type_alias_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                yield self._create_symbol(node, name_node, content, file, lang, SymbolKind.TYPE_ALIAS, parent_id, parent_name)
                return

        if node.type == 'enum_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.ENUM, parent_id, parent_name)
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    for member in body.children:
                        if member.type == 'enum_member':
                            mn = member.child_by_field_name('name')
                            if mn:
                                yield self._create_symbol(member, mn, content, file, lang, SymbolKind.ENUM_MEMBER, sym.id, sym.name)
                return

        if node.type == 'method_definition':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.METHOD, parent_id, parent_name)
                sym.parameters = self._js_params(node)
                sym.return_type = self._js_return(node)
                sym.is_async = b'async' in content[node.start_byte:node.start_byte+20].encode()
                sym.signature = self._signature(sym)
                yield sym
                return

        if node.type in ('export_statement', 'export_declaration'):
            decl = node.child_by_field_name('declaration')
            if decl:
                for sym in self._extract_js_ts(decl, content, file, lang, parent_id, parent_name):
                    sym.is_exported = True
                    if b'default' in node.text[:20]:
                        sym.is_default_export = True
                    yield sym
                return

        for child in node.children:
            yield from self._extract_js_ts(child, content, file, lang, parent_id, parent_name)

    def _extract_python(self, node: Node, content: str, file: str, lang: Language,
                        parent_id: str | None, parent_name: str | None) -> Iterator[Symbol]:
        if node.type in ('function_definition', 'async_function_definition'):
            name_node = node.child_by_field_name('name')
            if name_node:
                kind = SymbolKind.METHOD if parent_name else SymbolKind.FUNCTION
                sym = self._create_symbol(node, name_node, content, file, lang, kind, parent_id, parent_name)
                sym.parameters = self._py_params(node)
                sym.return_type = self._py_return(node)
                sym.is_async = node.type == 'async_function_definition'
                sym.decorators = self._py_decorators(node)
                sym.signature = self._signature(sym)
                body = node.child_by_field_name('body')
                if body and body.children:
                    first = body.children[0]
                    if first.type == 'expression_statement' and first.children:
                        expr = first.children[0]
                        if expr.type == 'string':
                            sym.docstring = self._comments.extract_docstring(expr.text.decode(), lang)
                yield sym
                if body:
                    yield from self._extract_python(body, content, file, lang, sym.id, sym.name)
                return

        if node.type == 'class_definition':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.CLASS, parent_id, parent_name)
                sym.metadata['decorators'] = self._py_decorators(node)
                sym.metadata['bases'] = []
                superclasses = node.child_by_field_name('superclasses')
                if superclasses:
                    for child in superclasses.children:
                        if child.type == 'identifier':
                            sym.metadata['bases'].append(child.text.decode())
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    yield from self._extract_python(body, content, file, lang, sym.id, sym.name)
                return

        if node.type == 'assignment' and parent_id is None:
            left = node.child_by_field_name('left')
            if left and left.type == 'identifier':
                name = left.text.decode()
                kind = SymbolKind.CONSTANT if name.isupper() else SymbolKind.VARIABLE
                yield self._create_symbol(node, left, content, file, lang, kind, parent_id, parent_name)
                return

        for child in node.children:
            yield from self._extract_python(child, content, file, lang, parent_id, parent_name)

    def _extract_go(self, node: Node, content: str, file: str, lang: Language,
                    parent_id: str | None, parent_name: str | None) -> Iterator[Symbol]:
        if node.type == 'function_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.FUNCTION, parent_id, parent_name)
                sym.signature = self._signature(sym)
                yield sym
                return

        if node.type == 'method_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.METHOD, parent_id, parent_name)
                receiver = node.child_by_field_name('receiver')
                if receiver:
                    for child in receiver.children:
                        if child.type == 'parameter_declaration':
                            t = child.child_by_field_name('type')
                            if t:
                                sym.parent_name = t.text.decode().lstrip('*')
                sym.signature = self._signature(sym)
                yield sym
                return

        if node.type == 'type_declaration':
            for child in node.children:
                if child.type == 'type_spec':
                    name_node = child.child_by_field_name('name')
                    type_node = child.child_by_field_name('type')
                    if name_node:
                        if type_node and type_node.type == 'struct_type':
                            yield self._create_symbol(child, name_node, content, file, lang, SymbolKind.STRUCT, parent_id, parent_name)
                        elif type_node and type_node.type == 'interface_type':
                            yield self._create_symbol(child, name_node, content, file, lang, SymbolKind.INTERFACE, parent_id, parent_name)
                        else:
                            yield self._create_symbol(child, name_node, content, file, lang, SymbolKind.TYPE_ALIAS, parent_id, parent_name)
            return

        for child in node.children:
            yield from self._extract_go(child, content, file, lang, parent_id, parent_name)

    def _extract_rust(self, node: Node, content: str, file: str, lang: Language,
                      parent_id: str | None, parent_name: str | None) -> Iterator[Symbol]:
        if node.type == 'function_item':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.FUNCTION, parent_id, parent_name)
                sym.is_async = b'async' in content[node.start_byte:node.start_byte+20].encode()
                yield sym
                return

        if node.type == 'struct_item':
            name_node = node.child_by_field_name('name')
            if name_node:
                yield self._create_symbol(node, name_node, content, file, lang, SymbolKind.STRUCT, parent_id, parent_name)
                return

        if node.type == 'enum_item':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.ENUM, parent_id, parent_name)
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    for variant in body.children:
                        if variant.type == 'enum_variant':
                            vn = variant.child_by_field_name('name')
                            if vn:
                                yield self._create_symbol(variant, vn, content, file, lang, SymbolKind.ENUM_MEMBER, sym.id, sym.name)
                return

        if node.type == 'trait_item':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.TRAIT, parent_id, parent_name)
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    yield from self._extract_rust(body, content, file, lang, sym.id, sym.name)
                return

        if node.type == 'impl_item':
            type_node = node.child_by_field_name('type')
            if type_node:
                body = node.child_by_field_name('body')
                if body:
                    yield from self._extract_rust(body, content, file, lang, parent_id, type_node.text.decode())
            return

        for child in node.children:
            yield from self._extract_rust(child, content, file, lang, parent_id, parent_name)

    def _extract_java(self, node: Node, content: str, file: str, lang: Language,
                      parent_id: str | None, parent_name: str | None) -> Iterator[Symbol]:
        if node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.CLASS, parent_id, parent_name)
                sym.metadata['bases'] = []
                sym.metadata['interfaces'] = []
                for child in node.children:
                    if child.type == 'superclass':
                        for t in child.children:
                            if t.type == 'type_identifier':
                                sym.metadata['bases'].append(t.text.decode())
                    elif child.type == 'super_interfaces':
                        for t in child.children:
                            if t.type == 'type_identifier':
                                sym.metadata['interfaces'].append(t.text.decode())
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    yield from self._extract_java(body, content, file, lang, sym.id, sym.name)
                return

        if node.type == 'interface_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.INTERFACE, parent_id, parent_name)
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    yield from self._extract_java(body, content, file, lang, sym.id, sym.name)
                return

        if node.type == 'method_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                yield self._create_symbol(node, name_node, content, file, lang, SymbolKind.METHOD, parent_id, parent_name)
                return

        if node.type == 'enum_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.ENUM, parent_id, parent_name)
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    for child in body.children:
                        if child.type == 'enum_constant':
                            cn = child.child_by_field_name('name')
                            if cn:
                                yield self._create_symbol(child, cn, content, file, lang, SymbolKind.ENUM_MEMBER, sym.id, sym.name)
                return

        for child in node.children:
            yield from self._extract_java(child, content, file, lang, parent_id, parent_name)

    def _extract_c(self, node: Node, content: str, file: str, lang: Language,
                   parent_id: str | None, parent_name: str | None) -> Iterator[Symbol]:
        if node.type == 'function_definition':
            decl = node.child_by_field_name('declarator')
            if decl:
                name_node = self._find_func_name(decl)
                if name_node:
                    yield self._create_symbol(node, name_node, content, file, lang, SymbolKind.FUNCTION, parent_id, parent_name)
                    return

        if node.type in ('struct_specifier', 'class_specifier'):
            name_node = node.child_by_field_name('name')
            if name_node:
                kind = SymbolKind.CLASS if node.type == 'class_specifier' else SymbolKind.STRUCT
                sym = self._create_symbol(node, name_node, content, file, lang, kind, parent_id, parent_name)
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    yield from self._extract_c(body, content, file, lang, sym.id, sym.name)
                return

        if node.type == 'enum_specifier':
            name_node = node.child_by_field_name('name')
            if name_node:
                sym = self._create_symbol(node, name_node, content, file, lang, SymbolKind.ENUM, parent_id, parent_name)
                yield sym
                body = node.child_by_field_name('body')
                if body:
                    for child in body.children:
                        if child.type == 'enumerator':
                            en = child.child_by_field_name('name')
                            if en:
                                yield self._create_symbol(child, en, content, file, lang, SymbolKind.ENUM_MEMBER, sym.id, sym.name)
                return

        for child in node.children:
            yield from self._extract_c(child, content, file, lang, parent_id, parent_name)

    def _find_func_name(self, decl: Node) -> Node | None:
        if decl.type == 'identifier':
            return decl
        if decl.type == 'function_declarator':
            return self._find_func_name(decl.child_by_field_name('declarator'))
        if decl.type == 'pointer_declarator':
            return self._find_func_name(decl.child_by_field_name('declarator'))
        for child in decl.children:
            r = self._find_func_name(child)
            if r:
                return r
        return None

    def _parse_unsupported(self, content: str, file: str, lang: Language) -> ParseResult:
        import re
        symbols = []
        lines = content.split('\n')

        func_patterns = [
            r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)',
            r'^\s*def\s+(\w+)',
            r'^\s*func\s+(\w+)',
            r'^\s*fn\s+(\w+)',
        ]
        class_patterns = [
            r'^\s*(?:export\s+)?class\s+(\w+)',
            r'^\s*class\s+(\w+)',
            r'^\s*struct\s+(\w+)',
        ]

        for i, line in enumerate(lines):
            for pattern in func_patterns:
                m = re.match(pattern, line)
                if m:
                    symbols.append(Symbol(
                        name=m.group(1),
                        kind=SymbolKind.FUNCTION,
                        file=file,
                        range=Range(Position(i, 0), Position(i, len(line))),
                        metadata={
                            "id": generate_id(),
                            "qualified_name": f"{file}:{m.group(1)}",
                            "selection_range": Range(Position(i, m.start(1)), Position(i, m.end(1))),
                            "source": line,
                            "language": lang
                        }
                    ))
                    break
            for pattern in class_patterns:
                m = re.match(pattern, line)
                if m:
                    symbols.append(Symbol(
                        name=m.group(1),
                        kind=SymbolKind.CLASS,
                        file=file,
                        range=Range(Position(i, 0), Position(i, len(line))),
                        metadata={
                            "id": generate_id(),
                            "qualified_name": f"{file}:{m.group(1)}",
                            "selection_range": Range(Position(i, m.start(1)), Position(i, m.end(1))),
                            "source": line,
                            "language": lang
                        }
                    ))
                    break

        return ParseResult(symbols, [], [], None, lang, True)

    def _create_symbol(self, node: Node, name_node: Node, content: str, file: str, lang: Language,
                       kind: SymbolKind, parent_id: str | None, parent_name: str | None) -> Symbol:
        name = name_node.text.decode()
        range_ = Range(Position(node.start_point[0], node.start_point[1]), Position(node.end_point[0], node.end_point[1]))
        selection = Range(Position(name_node.start_point[0], name_node.start_point[1]), Position(name_node.end_point[0], name_node.end_point[1]))
        qualified = f"{file}:{parent_name}.{name}" if parent_name else f"{file}:{name}"
        source = content[node.start_byte:node.end_byte]
        is_exported = node.parent and node.parent.type in ('export_statement', 'export_declaration')

        # Create symbol with only fields defined in the Symbol dataclass
        symbol = Symbol(
            name=name,
            kind=kind,
            file=file,
            range=range_,
            signature=source[:200] if len(source) > 200 else source,  # Store signature
        )
        
        # Store additional metadata
        symbol.metadata = {
            'id': generate_id(),
            'qualified_name': qualified,
            'selection_range': selection,
            'source': source,
            'language': str(lang.value),
            'is_exported': is_exported,
            'parent_id': parent_id,
            'parent_name': parent_name,
            'has_errors': node.has_error
        }
        
        return symbol

    def _js_params(self, node: Node) -> list[Parameter]:
        params = []
        pn = node.child_by_field_name('parameters')
        if not pn:
            return params
        for child in pn.children:
            if child.type in ('required_parameter', 'optional_parameter', 'identifier'):
                p = self._parse_js_param(child)
                if p:
                    params.append(p)
            elif child.type == 'rest_pattern' and len(child.children) > 1:
                params.append(Parameter(name=child.children[1].text.decode(), rest=True))
        return params

    def _parse_js_param(self, node: Node) -> Parameter | None:
        if node.type == 'identifier':
            return Parameter(name=node.text.decode())
        name_node = node.child_by_field_name('pattern') or node.child_by_field_name('name')
        if not name_node or name_node.type != 'identifier':
            return None
        name = name_node.text.decode()
        type_node = node.child_by_field_name('type')
        type_ann = type_node.text.decode().lstrip(': ') if type_node else None
        value_node = node.child_by_field_name('value')
        default = value_node.text.decode() if value_node else None
        return Parameter(name=name, param_type=type_ann or "", default=default, optional=node.type == 'optional_parameter' or default is not None)

    def _js_return(self, node: Node) -> str | None:
        rt = node.child_by_field_name('return_type')
        return rt.text.decode().lstrip(': ') if rt else None

    def _py_params(self, node: Node) -> list[Parameter]:
        params = []
        pn = node.child_by_field_name('parameters')
        if not pn:
            return params
        for child in pn.children:
            if child.type in ('identifier', 'typed_parameter', 'default_parameter', 'typed_default_parameter'):
                p = self._parse_py_param(child)
                if p:
                    params.append(p)
        return params

    def _parse_py_param(self, node: Node) -> Parameter | None:
        if node.type == 'identifier':
            name = node.text.decode()
            return None if name in ('self', 'cls') else Parameter(name=name)
        name = type_ann = default = None
        if node.type == 'typed_parameter':
            for child in node.children:
                if child.type == 'identifier' and name is None:
                    name = child.text.decode()
                elif child.type == 'type':
                    type_ann = child.text.decode()
        elif node.type == 'default_parameter':
            nn = node.child_by_field_name('name')
            vn = node.child_by_field_name('value')
            name = nn.text.decode() if nn else None
            default = vn.text.decode() if vn else None
        elif node.type == 'typed_default_parameter':
            for child in node.children:
                if child.type == 'identifier' and name is None:
                    name = child.text.decode()
                elif child.type == 'type':
                    type_ann = child.text.decode()
            vn = node.child_by_field_name('value')
            default = vn.text.decode() if vn else None
        if name and name not in ('self', 'cls'):
            return Parameter(name=name, param_type=type_ann or "", default=default, optional=default is not None)
        return None

    def _py_return(self, node: Node) -> str | None:
        rt = node.child_by_field_name('return_type')
        return rt.text.decode().lstrip(' -> ') if rt else None

    def _py_decorators(self, node: Node) -> list[str]:
        decorators = []
        for child in node.children:
            if child.type == 'decorator':
                text = child.text.decode()
                decorators.append(text.lstrip('@').split('(')[0])
        return decorators

    def _signature(self, sym: Symbol) -> str:
        params = ', '.join(f"{p.name}: {p.param_type}" if p.param_type else p.name for p in sym.parameters)
        ret = f" -> {sym.return_type}" if sym.return_type else ""
        prefix = "async " if sym.is_async else ""
        return f"{prefix}{sym.name}({params}){ret}"

    def _associate_comments(self, comments: list[Comment], symbols: list[Symbol]):
        if not comments or not symbols:
            return
        sorted_syms = sorted(symbols, key=lambda s: s.range.start.line)
        for comment in comments:
            end = comment.range.end.line
            for sym in sorted_syms:
                start = sym.range.start.line
                if 0 <= start - end <= 2:
                    sym_id = sym.metadata.get('id', f"{sym.file}:{sym.name}")
                    comment.symbol_id = sym_id
                    comments = sym.metadata.get('comments', [])
                    comments.append(comment)
                    sym.metadata['comments'] = comments
                    if comment.kind == 'doc' and not sym.doc:
                        lang = sym.metadata.get('language', Language.PYTHON)
                        sym.doc = self._comments.extract_docstring(comment.content, lang)
                    break


_parser: IncrementalParser | None = None


def get_parser() -> IncrementalParser:
    global _parser
    if _parser is None:
        _parser = IncrementalParser()
    return _parser