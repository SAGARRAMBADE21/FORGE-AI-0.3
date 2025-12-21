# chunking/dynamic_chunker.py
"""Dynamic chunker with cross-file context."""

import re
import logging
from collections import defaultdict
from typing import Iterator

from core.types import Symbol, SymbolKind, Chunk, ChunkType, CrossFileContext
from core.utils import generate_id, count_tokens, extract_keywords
from config.settings import settings, Language

logger = logging.getLogger(__name__)


class DynamicChunker:
    def __init__(self):
        self.min_tokens = settings.chunking.min_tokens
        self.max_tokens = settings.chunking.max_tokens
        self.target_tokens = settings.chunking.target_tokens
        self.overlap_tokens = settings.chunking.overlap_tokens
        self._import_graph: dict[str, set[str]] = defaultdict(set)
        self._imported_by: dict[str, set[str]] = defaultdict(set)
        self._call_graph: dict[str, set[str]] = defaultdict(set)
        self._reverse_calls: dict[str, set[str]] = defaultdict(set)

    def build_graphs(self, symbols_by_file: dict[str, list[Symbol]], contents: dict[str, str]):
        self._import_graph.clear()
        self._imported_by.clear()
        for file, symbols in symbols_by_file.items():
            content = contents.get(file, "")
            lang = symbols[0].metadata.get('language', Language.UNKNOWN) if symbols else Language.UNKNOWN
            imports = self._extract_imports(content, lang)
            self._import_graph[file] = set(imports)
        for file, imports in self._import_graph.items():
            for imp in imports:
                self._imported_by[imp].add(file)

    def build_call_graph(self, symbols: list[Symbol]):
        self._call_graph.clear()
        self._reverse_calls.clear()
        symbol_names = {s.name: s.id for s in symbols}
        for sym in symbols:
            if sym.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD, SymbolKind.HOOK):
                calls = re.findall(r'\b(\w+)\s*\(', sym.source)
                for call in calls:
                    if call in symbol_names and call != sym.name:
                        self._call_graph[sym.id].add(call)
                        self._reverse_calls[symbol_names[call]].add(sym.name)

    def chunk_file(self, content: str, file: str, symbols: list[Symbol], language: Language) -> list[Chunk]:
        lines = content.split('\n')
        if not symbols:
            return self._chunk_by_size(content, file, language, lines)

        sorted_syms = sorted(symbols, key=lambda s: s.range.start.line)
        chunks = []
        covered = set()

        for sym in sorted_syms:
            if sym.parent_id or sym.kind in (SymbolKind.IMPORT, SymbolKind.VARIABLE):
                continue
            chunk = self._create_symbol_chunk(sym, content, lines, file, language)
            if chunk:
                if chunks:
                    self._add_overlap(chunks[-1], chunk, lines)
                chunks.append(chunk)
                for ln in range(chunk.start_line, chunk.end_line + 1):
                    covered.add(ln)

        if chunks and chunks[0].start_line > 0:
            header = self._create_header(content, lines, file, language, chunks[0].start_line)
            if header:
                chunks.insert(0, header)

        chunks = self._fill_gaps(chunks, lines, file, language, covered)

        final = []
        for chunk in chunks:
            if chunk.tokens > self.max_tokens:
                final.extend(self._split_chunk(chunk, lines))
            else:
                final.append(chunk)

        final = self._merge_small(final, lines)

        for chunk in final:
            chunk.cross_file = self._get_cross_file(chunk, file)

        return final

    def _create_symbol_chunk(self, sym: Symbol, content: str, lines: list[str], file: str, lang: Language) -> Chunk | None:
        start, end = sym.range.start.line, sym.range.end.line
        if end - start < 2:
            return None
        chunk_content = '\n'.join(lines[start:end + 1])
        tokens = count_tokens(chunk_content)
        if tokens < self.min_tokens:
            return None
        docstring = sym.docstring.summary if sym.docstring else ""
        parent_ctx = f"In {sym.parent_name}" if sym.parent_name else ""
        file_ctx = f"File: {file}"

        return Chunk(
            id=generate_id(),
            content=chunk_content,
            chunk_type=self._sym_to_chunk(sym.kind),
            file=file,
            start_line=start,
            end_line=end,
            language=lang.value if hasattr(lang, 'value') else str(lang),
            metadata={
                'tokens': tokens,
                'symbol_id': sym.id,
                'symbol_name': sym.name,
                'symbol_kind': sym.kind,
                'parent_context': parent_ctx,
                'file_context': file_ctx,
                'keywords': extract_keywords(chunk_content),
                'docstring': docstring[:200]
            }
        )

    def _create_header(self, content: str, lines: list[str], file: str, lang: Language, first_line: int) -> Chunk | None:
        end = min(first_line - 1, 50)
        if end < 0:
            return None
        chunk_content = '\n'.join(lines[:end + 1])
        tokens = count_tokens(chunk_content)
        if tokens < self.min_tokens:
            return None
        return Chunk(
            id=generate_id(),
            content=chunk_content,
            chunk_type=ChunkType.FILE_HEADER.value if hasattr(ChunkType.FILE_HEADER, 'value') else 'file_header',
            file=file,
            start_line=0,
            end_line=end,
            language=lang.value if hasattr(lang, 'value') else str(lang),
            metadata={
                'tokens': tokens,
                'keywords': extract_keywords(chunk_content),
                'file_context': f"File: {file}"
            }
        )

    def _add_overlap(self, prev: Chunk, curr: Chunk, lines: list[str]):
        gap = curr.start_line - prev.end_line
        if gap > 10:
            return
        overlap_lines = min(self.overlap_tokens // 20, 10)
        ctx_start = max(prev.end_line - overlap_lines + 1, prev.start_line)
        curr.overlap_prev = prev.end_line - ctx_start + 1
        if curr.start_line > ctx_start:
            new_content = '\n'.join(lines[ctx_start:curr.end_line + 1])
            curr.content = new_content
            curr.start_line = ctx_start
            curr.tokens = count_tokens(new_content)

    def _fill_gaps(self, chunks: list[Chunk], lines: list[str], file: str, lang: Language, covered: set[int]) -> list[Chunk]:
        total = len(lines)
        uncovered = []
        start = None
        for i in range(total):
            if i not in covered:
                if start is None:
                    start = i
            else:
                if start is not None:
                    uncovered.append((start, i - 1))
                    start = None
        if start is not None:
            uncovered.append((start, total - 1))

        gap_chunks = []
        for s, e in uncovered:
            if e - s < 5:
                continue
            content = '\n'.join(lines[s:e + 1])
            tokens = count_tokens(content)
            if tokens >= self.min_tokens:
                gap_chunks.append(Chunk(
                    id=generate_id(),
                    content=content,
                    chunk_type=ChunkType.CODE_BLOCK.value,
                    file=file,
                    start_line=s,
                    end_line=e,
                    language=lang.value if hasattr(lang, 'value') else str(lang),
                    metadata={
                        'tokens': tokens,
                        'keywords': extract_keywords(content)
                    }
                ))

        all_chunks = chunks + gap_chunks
        all_chunks.sort(key=lambda c: c.start_line)
        return all_chunks

    def _split_chunk(self, chunk: Chunk, lines: list[str]) -> list[Chunk]:
        result = []
        chunk_lines = lines[chunk.start_line:chunk.end_line + 1]
        current_start = 0
        current_tokens = 0
        current_lines = []

        for i, line in enumerate(chunk_lines):
            line_tokens = count_tokens(line)
            should_split = current_tokens + line_tokens > self.target_tokens and current_tokens >= self.min_tokens
            is_boundary = line.strip() in ('', '}', ')') or line.strip().endswith('{')

            if should_split and (is_boundary or current_tokens > self.max_tokens - 100):
                content = '\n'.join(current_lines)
                result.append(Chunk(
                    id=generate_id(),
                    content=content,
                    chunk_type=chunk.chunk_type,
                    file=chunk.file,
                    start_line=chunk.start_line + current_start,
                    end_line=chunk.start_line + current_start + len(current_lines) - 1,
                    language=chunk.language,
                    metadata={
                        'tokens': current_tokens,
                        'symbol_id': chunk.symbol_id,
                        'symbol_name': chunk.symbol_name,
                        'symbol_kind': chunk.symbol_kind,
                        'parent_context': chunk.parent_context,
                        'file_context': chunk.file_context,
                        'keywords': extract_keywords(content)
                    }
                ))
                overlap_start = max(0, len(current_lines) - 3)
                current_lines = current_lines[overlap_start:]
                current_start = current_start + overlap_start
                current_tokens = sum(count_tokens(l) for l in current_lines)

            current_lines.append(line)
            current_tokens += line_tokens

        if current_lines:
            content = '\n'.join(current_lines)
            result.append(Chunk(
                id=generate_id(),
                content=content,
                chunk_type=chunk.chunk_type,
                file=chunk.file,
                start_line=chunk.start_line + current_start,
                end_line=chunk.end_line,
                language=chunk.language,
                metadata={
                    'tokens': count_tokens(content),
                    'symbol_id': chunk.symbol_id,
                    'symbol_name': chunk.symbol_name,
                    'symbol_kind': chunk.symbol_kind,
                    'parent_context': chunk.parent_context,
                    'file_context': chunk.file_context,
                    'keywords': extract_keywords(content)
                }
            ))

        return result if result else [chunk]

    def _merge_small(self, chunks: list[Chunk], lines: list[str]) -> list[Chunk]:
        if not chunks:
            return chunks
        merged = []
        current = chunks[0]
        for next_c in chunks[1:]:
            combined = current.tokens + next_c.tokens
            adjacent = next_c.start_line <= current.end_line + 5
            same_type = current.chunk_type == next_c.chunk_type
            if combined <= self.max_tokens and adjacent and same_type:
                new_content = '\n'.join(lines[current.start_line:next_c.end_line + 1])
                current = Chunk(
                    id=generate_id(),
                    content=new_content,
                    chunk_type=current.chunk_type,
                    file=current.file,
                    start_line=current.start_line,
                    end_line=next_c.end_line,
                    language=current.language,
                    metadata={
                        'tokens': count_tokens(new_content),
                        'symbol_id': current.symbol_id or next_c.symbol_id,
                        'symbol_name': current.symbol_name or next_c.symbol_name,
                        'symbol_kind': current.symbol_kind or next_c.symbol_kind,
                        'parent_context': current.parent_context,
                        'file_context': current.file_context,
                        'keywords': list(set(current.keywords + next_c.keywords))[:20]
                    }
                )
            else:
                if current.tokens >= self.min_tokens:
                    merged.append(current)
                current = next_c
        if current.tokens >= self.min_tokens:
            merged.append(current)
        return merged

    def _chunk_by_size(self, content: str, file: str, lang: Language, lines: list[str]) -> list[Chunk]:
        chunks = []
        current_start = 0
        current_tokens = 0
        current_lines = []
        for i, line in enumerate(lines):
            line_tokens = count_tokens(line)
            if current_tokens + line_tokens > self.target_tokens and current_lines:
                chunk_content = '\n'.join(current_lines)
                chunks.append(Chunk(
                    id=generate_id(),
                    content=chunk_content,
                    chunk_type=ChunkType.CODE_BLOCK.value,
                    file=file,
                    start_line=current_start,
                    end_line=current_start + len(current_lines) - 1,
                    language=lang.value if hasattr(lang, 'value') else str(lang),
                    metadata={
                        'tokens': current_tokens,
                        'keywords': extract_keywords(chunk_content)
                    }
                ))
                overlap = min(5, len(current_lines))
                current_lines = current_lines[-overlap:]
                current_start = i - overlap
                current_tokens = sum(count_tokens(l) for l in current_lines)
            current_lines.append(line)
            current_tokens += line_tokens

        if current_lines and current_tokens >= self.min_tokens:
            chunk_content = '\n'.join(current_lines)
            chunks.append(Chunk(
                id=generate_id(),
                content=chunk_content,
                chunk_type=ChunkType.CODE_BLOCK.value,
                file=file,
                start_line=current_start,
                end_line=len(lines) - 1,
                language=lang.value if hasattr(lang, 'value') else str(lang),
                metadata={
                    'tokens': current_tokens,
                    'keywords': extract_keywords(chunk_content)
                }
            ))
        return chunks

    def _get_cross_file(self, chunk: Chunk, file: str) -> CrossFileContext:
        ctx = CrossFileContext(file=file)
        ctx.imports = list(self._import_graph.get(file, set()))[:settings.chunking.max_cross_refs]
        ctx.imported_by = list(self._imported_by.get(file, set()))[:settings.chunking.max_cross_refs]
        if chunk.symbol_id:
            ctx.callees = list(self._call_graph.get(chunk.symbol_id, set()))[:settings.chunking.max_cross_refs]
            ctx.callers = list(self._reverse_calls.get(chunk.symbol_id, set()))[:settings.chunking.max_cross_refs]
        return ctx

    def _extract_imports(self, content: str, lang: Language) -> list[str]:
        imports = []
        if lang in (Language.TYPESCRIPT, Language.TSX, Language.JAVASCRIPT, Language.JSX):
            imports.extend(m.group(1) for m in re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content))
            imports.extend(m.group(1) for m in re.finditer(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content))
        elif lang == Language.PYTHON:
            for m in re.finditer(r'^(?:from\s+(\S+)|import\s+(\S+))', content, re.MULTILINE):
                imports.append(m.group(1) or m.group(2))
        elif lang == Language.GO:
            imports.extend(m.group(1) for m in re.finditer(r'import\s+[\'"]([^\'"]+)[\'"]', content))
        elif lang == Language.RUST:
            imports.extend(m.group(1).strip() for m in re.finditer(r'use\s+([^;]+)', content))
        elif lang == Language.JAVA:
            imports.extend(m.group(1) for m in re.finditer(r'import\s+([\w.]+)', content))
        return imports[:20]

    def _sym_to_chunk(self, kind: SymbolKind) -> ChunkType:
        mapping = {
            SymbolKind.FUNCTION: ChunkType.FUNCTION,
            SymbolKind.METHOD: ChunkType.METHOD,
            SymbolKind.CLASS: ChunkType.CLASS,
            SymbolKind.INTERFACE: ChunkType.INTERFACE,
            SymbolKind.TYPE_ALIAS: ChunkType.TYPE,
            SymbolKind.COMPONENT: ChunkType.COMPONENT,
            SymbolKind.HOOK: ChunkType.HOOK,
            SymbolKind.STRUCT: ChunkType.STRUCT,
        }
        return mapping.get(kind, ChunkType.CODE_BLOCK)


_chunker: DynamicChunker | None = None


def get_chunker() -> DynamicChunker:
    global _chunker
    if _chunker is None:
        _chunker = DynamicChunker()
    return _chunker