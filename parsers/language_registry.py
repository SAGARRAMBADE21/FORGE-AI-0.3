"""Language registry with tree-sitter support."""

import logging
from dataclasses import dataclass, field

from tree_sitter import Language as TSLanguage
from tree_sitter import Parser

from config.settings import Language

logger = logging.getLogger(__name__)


@dataclass
class LanguageConfig:
    name: str
    ts_language: TSLanguage | None = None
    extensions: list[str] = field(default_factory=list)
    comment_patterns: list[str] = field(default_factory=list)
    docstring_patterns: list[str] = field(default_factory=list)


class LanguageRegistry:
    def __init__(self):
        self._languages: dict[Language, LanguageConfig] = {}
        self._parsers: dict[Language, Parser] = {}
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        self._register_languages()
        self._initialized = True

    def _register_languages(self):
        # Python
        try:
            import tree_sitter_python as ts_py

            self._register(
                Language.PYTHON,
                LanguageConfig(
                    name="python",
                    ts_language=TSLanguage(ts_py.language()),
                    extensions=[".py", ".pyi"],
                    comment_patterns=[r"#.*$"],
                    docstring_patterns=[r'""".*?"""', r"'''.*?'''"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-python not available")

        # JavaScript
        try:
            import tree_sitter_javascript as ts_js

            js_lang = TSLanguage(ts_js.language())
            self._register(
                Language.JAVASCRIPT,
                LanguageConfig(
                    name="javascript",
                    ts_language=js_lang,
                    extensions=[".js", ".mjs", ".cjs"],
                    comment_patterns=[r"//.*$", r"/\*.*?\*/"],
                    docstring_patterns=[r"/\*\*.*?\*/"],
                ),
            )
            self._register(
                Language.JSX,
                LanguageConfig(
                    name="jsx",
                    ts_language=js_lang,
                    extensions=[".jsx"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-javascript not available")

        # TypeScript
        try:
            import tree_sitter_typescript as ts_ts

            ts_lang = TSLanguage(ts_ts.language_typescript())
            tsx_lang = TSLanguage(ts_ts.language_tsx())
            self._register(
                Language.TYPESCRIPT,
                LanguageConfig(
                    name="typescript",
                    ts_language=ts_lang,
                    extensions=[".ts", ".mts"],
                ),
            )
            self._register(
                Language.TSX,
                LanguageConfig(
                    name="tsx",
                    ts_language=tsx_lang,
                    extensions=[".tsx"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-typescript not available")

        # Go
        try:
            import tree_sitter_go as ts_go

            self._register(
                Language.GO,
                LanguageConfig(
                    name="go",
                    ts_language=TSLanguage(ts_go.language()),
                    extensions=[".go"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-go not available")

        # Rust
        try:
            import tree_sitter_rust as ts_rs

            self._register(
                Language.RUST,
                LanguageConfig(
                    name="rust",
                    ts_language=TSLanguage(ts_rs.language()),
                    extensions=[".rs"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-rust not available")

        # Java
        try:
            import tree_sitter_java as ts_java

            self._register(
                Language.JAVA,
                LanguageConfig(
                    name="java",
                    ts_language=TSLanguage(ts_java.language()),
                    extensions=[".java"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-java not available")

        # C
        try:
            import tree_sitter_c as ts_c

            self._register(
                Language.C,
                LanguageConfig(
                    name="c",
                    ts_language=TSLanguage(ts_c.language()),
                    extensions=[".c", ".h"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-c not available")

        # C++
        try:
            import tree_sitter_cpp as ts_cpp

            self._register(
                Language.CPP,
                LanguageConfig(
                    name="cpp",
                    ts_language=TSLanguage(ts_cpp.language()),
                    extensions=[".cpp", ".cc", ".cxx", ".hpp"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-cpp not available")

        # C#
        try:
            import tree_sitter_c_sharp as ts_cs

            self._register(
                Language.CSHARP,
                LanguageConfig(
                    name="csharp",
                    ts_language=TSLanguage(ts_cs.language()),
                    extensions=[".cs"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-c-sharp not available")

        # Ruby
        try:
            import tree_sitter_ruby as ts_rb

            self._register(
                Language.RUBY,
                LanguageConfig(
                    name="ruby",
                    ts_language=TSLanguage(ts_rb.language()),
                    extensions=[".rb"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-ruby not available")

        # PHP
        try:
            import tree_sitter_php as ts_php

            self._register(
                Language.PHP,
                LanguageConfig(
                    name="php",
                    ts_language=TSLanguage(ts_php.language_php()),
                    extensions=[".php"],
                ),
            )
        except ImportError:
            logger.debug("tree-sitter-php not available")

        logger.info(f"Registered {len(self._languages)} languages")

    def _register(self, lang: Language, config: LanguageConfig):
        self._languages[lang] = config
        if config.ts_language:
            parser = Parser()
            parser.language = config.ts_language
            self._parsers[lang] = parser

    def get_parser(self, lang: Language) -> Parser | None:
        return self._parsers.get(lang)

    def get_config(self, lang: Language) -> LanguageConfig | None:
        return self._languages.get(lang)

    def detect_language(self, path: str) -> Language:
        from pathlib import Path

        from config.settings import EXTENSION_MAP

        ext = Path(path).suffix.lower()
        return EXTENSION_MAP.get(ext, Language.UNKNOWN)

    def is_supported(self, lang: Language) -> bool:
        return lang in self._parsers

    @property
    def supported_languages(self) -> list[Language]:
        return list(self._parsers.keys())


_registry: LanguageRegistry | None = None


def get_registry() -> LanguageRegistry:
    global _registry
    if _registry is None:
        _registry = LanguageRegistry()
        _registry.initialize()
    return _registry
