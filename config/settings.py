"""Configuration settings."""

from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import os


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    TSX = "tsx"
    JSX = "jsx"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    VUE = "vue"
    SVELTE = "svelte"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    VOYAGE = "voyage"
    LOCAL = "local"


class VectorStoreBackend(str, Enum):
    MEMORY = "memory"
    CHROMADB = "chromadb"
    QDRANT = "qdrant"
    MONGODB = "mongodb"


EXTENSION_MAP: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".pyi": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".mts": Language.TYPESCRIPT,
    ".tsx": Language.TSX,
    ".jsx": Language.JSX,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".java": Language.JAVA,
    ".c": Language.C,
    ".h": Language.C,
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".hpp": Language.CPP,
    ".cs": Language.CSHARP,
    ".rb": Language.RUBY,
    ".php": Language.PHP,
    ".kt": Language.KOTLIN,
    ".swift": Language.SWIFT,
    ".vue": Language.VUE,
    ".svelte": Language.SVELTE,
    ".html": Language.HTML,
    ".htm": Language.HTML,
    ".css": Language.CSS,
    ".scss": Language.CSS,
    ".json": Language.JSON,
    ".yaml": Language.YAML,
    ".yml": Language.YAML,
    ".md": Language.MARKDOWN,
}


@dataclass
class ParserConfig:
    max_file_size: int = 1_000_000
    error_recovery: bool = True
    extract_comments: bool = True
    incremental: bool = True
    skip_dirs: set[str] = field(default_factory=lambda: {
        "node_modules", "__pycache__", ".git", "dist", "build",
        ".next", ".nuxt", "coverage", ".venv", "venv", "env", "target",
        "vendor", ".cache", "out", ".idea", ".vscode", "bin", "obj"
    })


@dataclass
class ChunkingConfig:
    min_tokens: int = 50
    max_tokens: int = 1500
    target_tokens: int = 800
    overlap_tokens: int = 100
    include_imports: bool = True
    include_context: bool = True
    include_cross_file: bool = True
    max_cross_refs: int = 5


@dataclass
class EmbeddingConfig:
    provider: EmbeddingProvider = EmbeddingProvider.LOCAL
    openai_model: str = "text-embedding-3-small"
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    voyage_model: str = "voyage-code-2"
    voyage_api_key: str = field(default_factory=lambda: os.getenv("VOYAGE_API_KEY", ""))
    local_model: str = "microsoft/graphcodebert-base"
    batch_size: int = 100
    cache_enabled: bool = True
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".code_indexer" / "cache")
    query_prefix: str = "Query: "
    doc_prefix: str = ""


@dataclass
class VectorStoreConfig:
    backend: VectorStoreBackend = VectorStoreBackend.CHROMADB  # Changed from MONGODB to CHROMADB for local storage
    persist_dir: Path = field(default_factory=lambda: Path.home() / ".code_indexer" / "vectorstore")
    collection: str = "code_chunks"
    # MongoDB Atlas specific settings
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", ""))
    mongodb_database: str = field(default_factory=lambda: os.getenv("MONGODB_DATABASE", "code_indexer"))
    mongodb_collection: str = field(default_factory=lambda: os.getenv("MONGODB_COLLECTION", "code_chunks"))
    mongodb_index: str = field(default_factory=lambda: os.getenv("MONGODB_INDEX", "vector_index"))


@dataclass
class SearchConfig:
    top_k: int = 10
    retrieval_k: int = 100
    threshold: float = 0.5
    hybrid_alpha: float = 0.7
    rerank: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_k: int = 20
    recency_boost: float = 0.1
    path_boost: float = 0.2
    symbol_boost: float = 0.3


@dataclass
class RealtimeConfig:
    enabled: bool = True
    debounce_ms: int = 500
    workers: int = 2


@dataclass
class Settings:
    parser: ParserConfig = field(default_factory=ParserConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vectorstore: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    realtime: RealtimeConfig = field(default_factory=RealtimeConfig)
    debug: bool = False


settings = Settings()