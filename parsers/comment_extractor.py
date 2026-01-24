"""Comment and docstring extraction."""

import re

from config.settings import Language
from core.types import Comment, Docstring, Position, Range


class CommentExtractor:
    def extract_comments(self, content: str, language: Language) -> list[Comment]:
        comments = []
        patterns = self._get_patterns(language)

        for pattern, kind in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                start = self._offset_to_pos(content, match.start())
                end = self._offset_to_pos(content, match.end())
                comments.append(
                    Comment(
                        content=match.group().strip(),
                        range=Range(start, end),
                        kind=kind,
                    )
                )
        return comments

    def extract_docstring(self, content: str, language: Language) -> Docstring | None:
        raw = self._extract_raw(content, language)
        if not raw:
            return None
        return self._parse_docstring(raw, language)

    def _get_patterns(self, lang: Language) -> list[tuple[str, str]]:
        if lang == Language.PYTHON:
            return [(r"#[^\n]*", "line"), (r'""".*?"""', "doc"), (r"'''.*?'''", "doc")]
        elif lang in (
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.TSX,
            Language.JSX,
            Language.JAVA,
            Language.GO,
            Language.RUST,
            Language.C,
            Language.CPP,
        ):
            return [
                (r"//[^\n]*", "line"),
                (r"/\*\*.*?\*/", "doc"),
                (r"/\*.*?\*/", "block"),
            ]
        elif lang == Language.RUBY:
            return [(r"#[^\n]*", "line")]
        return []

    def _extract_raw(self, content: str, lang: Language) -> str | None:
        if lang == Language.PYTHON:
            m = re.match(r'^\s*"""(.*?)"""', content, re.DOTALL)
            if m:
                return m.group(1).strip()
            m = re.match(r"^\s*'''(.*?)'''", content, re.DOTALL)
            if m:
                return m.group(1).strip()
        elif lang in (
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.TSX,
            Language.JSX,
            Language.JAVA,
        ):
            m = re.match(r"^\s*/\*\*(.*?)\*/", content, re.DOTALL)
            if m:
                doc = m.group(1)
                lines = [re.sub(r"^\s*\*\s?", "", line) for line in doc.split("\n")]
                return "\n".join(lines).strip()
        return None

    def _parse_docstring(self, raw: str, lang: Language) -> Docstring:
        doc = Docstring(content=raw, range=Range(Position(0, 0), Position(0, 0)))
        lines = raw.split("\n")
        for line in lines:
            if line.strip():
                doc.summary = line.strip()
                break

        if lang in (
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.TSX,
            Language.JSX,
            Language.JAVA,
        ):
            doc.params = dict(
                re.findall(
                    r"@param\s+(?:\{[^}]+\}\s+)?(\w+)\s+(.+?)(?=@|\Z)", raw, re.DOTALL
                )
            )
            m = re.search(r"@returns?\s+(?:\{[^}]+\}\s+)?(.+?)(?=@|\Z)", raw, re.DOTALL)
            if m:
                doc.returns = m.group(1).strip()
        elif lang == Language.PYTHON:
            args_m = re.search(r"(?:Args|Parameters):\s*\n((?:\s+\w+.*\n?)+)", raw)
            if args_m:
                for pm in re.finditer(
                    r"\s+(\w+)(?:\s*\([^)]+\))?\s*:\s*(.+)", args_m.group(1)
                ):
                    doc.params[pm.group(1)] = pm.group(2).strip()
            ret_m = re.search(r"Returns?:\s*\n?\s*(.+?)(?=\n\n|\Z)", raw, re.DOTALL)
            if ret_m:
                doc.returns = ret_m.group(1).strip()
        return doc

    def _offset_to_pos(self, content: str, offset: int) -> Position:
        line = content[:offset].count("\n")
        last_nl = content.rfind("\n", 0, offset)
        col = offset - last_nl - 1 if last_nl >= 0 else offset
        return Position(line, col)


_extractor: CommentExtractor | None = None


def get_comment_extractor() -> CommentExtractor:
    global _extractor
    if _extractor is None:
        _extractor = CommentExtractor()
    return _extractor
