"""Configuration settings."""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


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
    skip_dirs: set[str] = field(
        default_factory=lambda: {
            "node_modules",
            "__pycache__",
            ".git",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "coverage",
            ".venv",
            "venv",
            "env",
            "target",
            "vendor",
            ".cache",
            "out",
            ".idea",
            ".vscode",
            "bin",
            "obj",
        }
    )


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
    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    openai_model: str = "text-embedding-3-small"
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    voyage_model: str = "voyage-code-3"
    voyage_api_key: str = field(default_factory=lambda: os.getenv("VOYAGE_API_KEY", ""))

    batch_size: int = 100
    cache_enabled: bool = True
    cache_dir: Path = field(
        default_factory=lambda: Path.home() / ".code_indexer" / "cache"
    )
    query_prefix: str = "Query: "
    doc_prefix: str = ""


@dataclass
class VectorStoreConfig:
    backend: VectorStoreBackend = (
        VectorStoreBackend.CHROMADB
    )  # Changed from MONGODB to CHROMADB for local storage
    persist_dir: Path = field(
        default_factory=lambda: Path.home() / ".code_indexer" / "vectorstore"
    )
    collection: str = "code_chunks"
    # MongoDB Atlas specific settings
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", ""))
    mongodb_database: str = field(
        default_factory=lambda: os.getenv("MONGODB_DATABASE", "code_indexer")
    )
    mongodb_collection: str = field(
        default_factory=lambda: os.getenv("MONGODB_COLLECTION", "code_chunks")
    )
    mongodb_index: str = field(
        default_factory=lambda: os.getenv("MONGODB_INDEX", "vector_index")
    )


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
class OptimizationConfig:
    """Configuration for FORGE optimizations."""

    # Caching
    enable_cache: bool = True
    cache_ttl_hours: float = 24.0

    # Cost tracking
    enable_cost_tracking: bool = True
    session_limit_usd: float = 10.0
    lifetime_limit_usd: float = 100.0

    # Prompt optimization
    enable_prompt_optimization: bool = True
    aggressive_optimization: bool = False

    # Performance
    lightweight_mode: bool = field(
        default_factory=lambda: os.getenv("FORGE_LIGHTWEIGHT", "").lower()
        in ("true", "1", "yes")
    )
    lazy_load_models: bool = True


@dataclass
class LLMConfig:
    """Configuration for LLM-based code generation"""

    # Backend generation (optimized for code generation)
    backend_provider: str = "openai"
    backend_model: str = "gpt-4.1-mini"
    backend_max_tokens: int = 16384  # GPT-4.1-mini supports up to 1M context
    backend_temperature: float = 0.1

    # Frontend generation (if different)
    frontend_provider: str = "openai"
    frontend_model: str = "gpt-4.1-mini"
    frontend_max_tokens: int = 16384
    frontend_temperature: float = 0.1

    # Smart routing - use cheaper models for simple tasks
    simple_task_provider: str = "groq"
    simple_task_model: str = "llama-3.1-8b-instant"

    # API keys from environment
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    huggingface_api_key: str = field(
        default_factory=lambda: os.getenv("HUGGINGFACE_API_KEY", "")
    )
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))


@dataclass
class Settings:
    parser: ParserConfig = field(default_factory=ParserConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vectorstore: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    realtime: RealtimeConfig = field(default_factory=RealtimeConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    debug: bool = False


settings = Settings()
