"""Error recovery for parsing."""

import logging
import re

from tree_sitter import Node

from config.settings import Language
from core.types import ParseError, Position, Range

logger = logging.getLogger(__name__)


class ErrorRecovery:
    FIXES = {
        r"(\w+)\s*\n\s*(const|let|var|function|class)": r"\1;\n\2",
        r"(\{[^}]*)\s*$": r"\1}",
        r"(\([^)]*)\s*$": r"\1)",
        r",\s*(\}|\])": r"\1",
    }

    def find_errors(self, root: Node, file: str) -> list[ParseError]:
        errors = []
        self._collect(root, file, errors)
        return errors

    def _collect(self, node: Node, file: str, errors: list[ParseError]):
        if node.is_error or node.is_missing:
            errors.append(
                ParseError(
                    file=file,
                    range=Range(
                        Position(node.start_point[0], node.start_point[1]),
                        Position(node.end_point[0], node.end_point[1]),
                    ),
                    message=(
                        f"Parse error: {node.type}"
                        if node.is_error
                        else f"Missing: {node.type}"
                    ),
                    recoverable=True,
                )
            )
        for child in node.children:
            self._collect(child, file, errors)

    def attempt_recovery(
        self, content: str, errors: list[ParseError], lang: Language
    ) -> tuple[str | None, list[str]]:
        if not errors:
            return None, []

        patches = []
        patched = content

        for error in errors:
            fix = self._suggest_fix(patched, error, lang)
            if fix:
                patched = fix
                patches.append(f"Fixed at line {error.range.start.line + 1}")

        for pattern, replacement in self.FIXES.items():
            new = re.sub(pattern, replacement, patched, flags=re.MULTILINE)
            if new != patched:
                patched = new
                patches.append(f"Applied pattern: {pattern[:30]}...")

        return (patched if patches else None), patches

    def _suggest_fix(
        self, content: str, error: ParseError, lang: Language
    ) -> str | None:
        lines = content.split("\n")
        idx = error.range.start.line
        if idx >= len(lines):
            return None

        line = lines[idx]

        for open_c, close_c in [("(", ")"), ("{", "}"), ("[", "]")]:
            if self._count_unbalanced(line, open_c, close_c) > 0:
                lines[idx] = line + close_c
                return "\n".join(lines)
        return None

    def _count_unbalanced(self, text: str, open_c: str, close_c: str) -> int:
        count = 0
        in_str = False
        str_char = None
        for i, c in enumerate(text):
            if c in ('"', "'", "`") and (i == 0 or text[i - 1] != "\\"):
                if not in_str:
                    in_str = True
                    str_char = c
                elif c == str_char:
                    in_str = False
            elif not in_str:
                if c == open_c:
                    count += 1
                elif c == close_c:
                    count -= 1
        return count


_recovery: ErrorRecovery | None = None


def get_error_recovery() -> ErrorRecovery:
    global _recovery
    if _recovery is None:
        _recovery = ErrorRecovery()
    return _recovery
