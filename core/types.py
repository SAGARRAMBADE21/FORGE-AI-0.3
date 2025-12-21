"""Extended type definitions for full-stack generation."""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Any
import numpy as np

# ═══════════════════════════════════════════════════════════════════════════
# CORE TYPES (Part 1)
# ═══════════════════════════════════════════════════════════════════════════

class SymbolKind(str, Enum):
    """Kind of code symbol."""
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    INTERFACE = "interface"
    TYPE = "type"
    TYPE_ALIAS = "type_alias"
    VARIABLE = "variable"
    CONSTANT = "constant"
    PROPERTY = "property"
    PARAMETER = "parameter"
    MODULE = "module"
    IMPORT = "import"
    EXPORT = "export"
    COMPONENT = "component"
    HOOK = "hook"
    DECORATOR = "decorator"
    ENUM = "enum"
    STRUCT = "struct"
    NAMESPACE = "namespace"


@dataclass
class Position:
    """Position in source code."""
    line: int
    column: int


@dataclass
class Range:
    """Range in source code."""
    start: Position
    end: Position
    
    def contains(self, position: Position) -> bool:
        """Check if this range contains the given position."""
        if self.start.line < position.line < self.end.line:
            return True
        if self.start.line == position.line == self.end.line:
            return self.start.column <= position.column <= self.end.column
        if self.start.line == position.line:
            return position.column >= self.start.column
        if self.end.line == position.line:
            return position.column <= self.end.column
        return False
    
    @property
    def lines(self) -> int:
        """Number of lines in this range."""
        return self.end.line - self.start.line + 1


@dataclass
class Symbol:
    """Code symbol with metadata."""
    name: str
    kind: SymbolKind
    file: str
    range: Range
    doc: str = ""
    signature: str = ""
    modifiers: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    # Backward compatibility properties for accessing metadata
    @property
    def id(self) -> str:
        return self.metadata.get('id', f"{self.file}:{self.name}")
    
    @property
    def qualified_name(self) -> str:
        return self.metadata.get('qualified_name', f"{self.file}:{self.name}")
    
    @property
    def selection_range(self):
        return self.metadata.get('selection_range', self.range)
    
    @property
    def source(self) -> str:
        return self.metadata.get('source', self.signature)
    
    @property
    def language(self):
        from config.settings import Language
        return self.metadata.get('language', Language.PYTHON)
    
    @property
    def type_annotation(self) -> str | None:
        return self.metadata.get('type_annotation')
    
    @property
    def return_type(self) -> str | None:
        return self.metadata.get('return_type')
    
    @return_type.setter
    def return_type(self, value: str | None):
        self.metadata['return_type'] = value
    
    @property
    def parameters(self) -> list:
        return self.metadata.get('parameters', [])
    
    @parameters.setter
    def parameters(self, value: list):
        self.metadata['parameters'] = value
    
    @property
    def bases(self) -> list:
        return self.metadata.get('bases', [])
    
    @property
    def interfaces(self) -> list:
        return self.metadata.get('interfaces', [])
    
    @property
    def comments(self) -> list:
        return self.metadata.get('comments', [])
    
    @property
    def docstring(self) -> str:
        return self.doc
    
    @docstring.setter
    def docstring(self, value: str):
        self.doc = value
    
    @property
    def decorators(self) -> list:
        return self.metadata.get('decorators', [])
    
    @decorators.setter
    def decorators(self, value: list):
        self.metadata['decorators'] = value
    
    @property
    def is_async(self) -> bool:
        return self.metadata.get('is_async', False)
    
    @is_async.setter
    def is_async(self, value: bool):
        self.metadata['is_async'] = value
    
    @property
    def is_exported(self) -> bool:
        return self.metadata.get('is_exported', False)
    
    @is_exported.setter
    def is_exported(self, value: bool):
        self.metadata['is_exported'] = value
    
    @property
    def parent_id(self) -> str | None:
        return self.metadata.get('parent_id')
    
    @property
    def parent_name(self) -> str | None:
        return self.metadata.get('parent_name')


@dataclass
class Chunk:
    """Semantic code chunk."""
    id: str
    content: str
    file: str
    start_line: int
    end_line: int
    language: str
    chunk_type: str = "code"
    symbols: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    context: str = ""
    embedding: np.ndarray | None = None
    metadata: dict = field(default_factory=dict)
    
    # Backward compatibility properties
    @property
    def tokens(self) -> int:
        return self.metadata.get('tokens', 0)
    
    @tokens.setter
    def tokens(self, value: int):
        self.metadata['tokens'] = value
    
    @property
    def keywords(self) -> list:
        return self.metadata.get('keywords', [])
    
    @keywords.setter
    def keywords(self, value: list):
        self.metadata['keywords'] = value
    
    @property
    def file_context(self) -> str:
        return self.metadata.get('file_context', '')
    
    @file_context.setter
    def file_context(self, value: str):
        self.metadata['file_context'] = value
    
    @property
    def symbol_id(self) -> str | None:
        return self.metadata.get('symbol_id')
    
    @property
    def symbol_name(self) -> str | None:
        return self.metadata.get('symbol_name')
    
    @property
    def symbol_kind(self):
        return self.metadata.get('symbol_kind')
    
    @property
    def parent_context(self) -> str:
        return self.metadata.get('parent_context', '')
    
    @property
    def imports(self) -> list:
        return self.metadata.get('imports', [])
    
    @property
    def semantic_tags(self) -> list:
        return self.metadata.get('semantic_tags', [])
    
    @property
    def weighted_keywords(self) -> dict:
        return self.metadata.get('weighted_keywords', {})
    
    def to_embedding_text(self) -> str:
        """Convert chunk to text for embedding."""
        parts = []
        if self.file:
            parts.append(f"File: {self.file}")
        if self.symbol_name:
            parts.append(f"Symbol: {self.symbol_name}")
        if self.context:
            parts.append(self.context)
        parts.append(self.content)
        return "\n".join(parts)


@dataclass
class SearchQuery:
    """Search query parameters."""
    query: str
    top_k: int = 10
    file_filter: list[str] | None = None
    language_filter: list[str] | None = None
    symbol_kind_filter: list[SymbolKind] | None = None
    include_context: bool = True
    threshold: float = 0.5


@dataclass
class SearchResult:
    """Single search result."""
    chunk: Chunk
    score: float
    highlights: list[str] = field(default_factory=list)


@dataclass
class SearchResponse:
    """Search response with results."""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_count: int = 0
    search_time_ms: float = 0.0


@dataclass
class NavRequest:
    """Navigation request."""
    file: str
    position: Position
    include_references: bool = True


@dataclass
class DefinitionResult:
    """Definition lookup result."""
    symbol: Symbol | None = None
    definitions: list[Symbol] = field(default_factory=list)


@dataclass
class ReferenceResult:
    """Reference lookup result."""
    symbol: Symbol | None = None
    references: list["Reference"] = field(default_factory=list)


@dataclass
class CallHierarchyItem:
    """Call hierarchy item."""
    symbol: Symbol
    incoming: list["CallHierarchyItem"] = field(default_factory=list)
    outgoing: list["CallHierarchyItem"] = field(default_factory=list)


@dataclass
class CallHierarchyResult:
    """Call hierarchy result."""
    root: CallHierarchyItem | None = None


@dataclass
class HoverInfo:
    """Hover information."""
    symbol: Symbol | None = None
    documentation: str = ""
    signature: str = ""
    type_info: str = ""


@dataclass
class ComponentInfo:
    """Frontend component information."""
    name: str
    file: str
    id: str = ""
    component_type: str = "component"
    props: list[dict] = field(default_factory=list)
    state: list[dict] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    api_calls: list = field(default_factory=list)
    forms: list = field(default_factory=list)
    exported: bool = False


@dataclass
class FormInfo:
    """Form information."""
    file: str
    name: str = ""
    id: str = ""
    component: str | None = None
    submit_endpoint: str | None = None
    validation_lib: str = ""
    fields: list[dict] = field(default_factory=list)
    validation: dict = field(default_factory=dict)
    submit_handler: str = ""


@dataclass
class ApiCallInfo:
    """API call information."""
    method: str
    endpoint: str
    file: str
    line: int
    request_body: dict | None = None
    response_type: str = ""


@dataclass
class FrontendAnalysis:
    """Complete frontend analysis."""
    project: str = ""
    framework: Any = None
    language: Any = None
    api_calls: list[ApiCallInfo] = field(default_factory=list)
    data_models: list = field(default_factory=list)
    components: list[ComponentInfo] = field(default_factory=list)
    forms: list[FormInfo] = field(default_factory=list)
    auth: "AuthPattern | None" = None
    routes: list[dict] = field(default_factory=list)
    stats: Any = None
    state_stores: list[dict] = field(default_factory=list)


@dataclass
class IndexStats:
    """Indexing statistics."""
    total_files: int = 0
    total_chunks: int = 0
    total_symbols: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    index_time_ms: float = 0.0
    last_updated: datetime | None = None


# ═══════════════════════════════════════════════════════════════════════════
# ADDITIONAL CORE TYPES
# ═══════════════════════════════════════════════════════════════════════════

class ChunkType(str, Enum):
    """Type of code chunk."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    IMPORT = "import"
    COMMENT = "comment"
    DOCSTRING = "docstring"
    CODE = "code"
    CODE_BLOCK = "code_block"
    INTERFACE = "interface"
    TYPE = "type"
    COMPONENT = "component"
    HOOK = "hook"
    STRUCT = "struct"
    FILE_HEADER = "file_header"


@dataclass
class Parameter:
    """Function/method parameter."""
    name: str
    param_type: str = ""
    default: str | None = None
    optional: bool = False


@dataclass
class Comment:
    """Code comment."""
    content: str
    range: Range
    kind: str = "line"  # line, block, doc


@dataclass
class Docstring:
    """Documentation string."""
    content: str
    range: Range
    format: str = "plain"  # plain, jsdoc, sphinx, google
    summary: str = ""
    params: dict = field(default_factory=dict)
    returns: str = ""


@dataclass
@dataclass
class ParseError:
    """Parse error information."""
    message: str
    range: Range
    file: str = ""
    severity: str = "error"  # error, warning
    recoverable: bool = True


@dataclass
class CrossFileContext:
    """Cross-file context information."""
    file: str
    symbols: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


class ReferenceKind(str, Enum):
    """Kind of reference."""
    READ = "read"
    WRITE = "write"
    CALL = "call"
    TYPE = "type"
    IMPORT = "import"
    EXPORT = "export"


class HTTPMethod(str, Enum):
    """HTTP method types."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class AuthType(str, Enum):
    """Authentication type."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    JWT = "jwt"
    API_KEY = "api_key"
    OAUTH = "oauth"
    SESSION = "session"


class FrameworkType(str, Enum):
    """Frontend framework type."""
    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"
    NEXT = "next"
    NUXT = "nuxt"
    EXPRESS = "express"
    UNKNOWN = "unknown"


@dataclass
class Location:
    """Source code location."""
    file: str
    range: Range


@dataclass
class LocationLink:
    """Link to a location in source code."""
    target_uri: str
    target_range: Range
    target_selection_range: Range
    origin_selection_range: Range | None = None


@dataclass
class Reference:
    """Code reference."""
    symbol: str
    location: Location
    kind: ReferenceKind = ReferenceKind.READ
    context: str = ""


@dataclass
class IncomingCall:
    """Incoming call in call hierarchy."""
    from_symbol: Symbol
    from_ranges: list[Range] = field(default_factory=list)


@dataclass
class OutgoingCall:
    """Outgoing call in call hierarchy."""
    to_symbol: Symbol
    from_ranges: list[Range] = field(default_factory=list)


@dataclass
class FileInfo:
    """File information."""
    path: str
    language: str
    size: int = 0
    lines: int = 0
    last_modified: datetime | None = None
    hash: str = ""
    symbols: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)


@dataclass
class FieldInfo:
    """Field information for models/forms."""
    name: str
    field_type: str
    required: bool = False
    default: Any = None
    array: bool = False
    nullable: bool = False
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    validation: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class FormField:
    """Form field definition."""
    name: str
    field_type: str
    label: str = ""
    placeholder: str = ""
    required: bool = False
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    validation: list[str] = field(default_factory=list)
    default: Any = None


@dataclass
class DataModel:
    """Data model representation."""
    name: str
    fields: list[FieldInfo] = field(default_factory=list)
    id: str = ""
    primary_key: str = "id"
    timestamps: bool = True
    source_file: str = ""
    source: str = ""


@dataclass
class APICall:
    """API call representation."""
    method: HTTPMethod
    endpoint: str
    file: str
    line: int
    id: str = ""
    path_params: list[str] = field(default_factory=list)
    query_params: list[str] = field(default_factory=list)
    requires_auth: bool = False
    body_type: str = ""
    request_body: dict | None = None
    response_type: str = ""
    headers: dict = field(default_factory=dict)
    source: str = ""


@dataclass
class AuthPattern:
    """Authentication pattern."""
    type: AuthType
    auth_type: AuthType | None = None
    storage: str | None = None
    key: str | None = None
    login_endpoint: str | None = None
    logout_endpoint: str | None = None
    refresh_endpoint: str | None = None
    protected_routes: list[str] = field(default_factory=list)
    public_routes: list[str] = field(default_factory=list)
    token_storage: str = "localStorage"
    refresh_enabled: bool = False


@dataclass
class Relationship:
    """Model relationship."""
    source: str = ""
    target: str = ""
    type: str = ""
    relation_type: str = ""  # one-to-one, one-to-many, many-to-many
    field: str = ""
    foreign_key: str = ""
    through: str | None = None


@dataclass
class RouteInfo:
    """Route information."""
    path: str
    component: str
    file: str
    is_dynamic: bool = False
    params: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    middleware: list[str] = field(default_factory=list)
    auth_required: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# NEW: INFERENCE TYPES
# ═══════════════════════════════════════════════════════════════════════════

class EvidenceSource(str, Enum):
    """Source of inference evidence."""
    TYPESCRIPT_TYPE = "typescript_type"
    ZOD_SCHEMA = "zod_schema"
    API_RESPONSE = "api_response"
    FORM_STATE = "form_state"
    STATE_MANAGEMENT = "state_management"
    GRAPHQL_SCHEMA = "graphql_schema"
    VALIDATION_RULE = "validation_rule"


class InferredRelationType(str, Enum):
    """Type of relationship between models."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"
    SELF_REFERENTIAL = "self_referential"


class InferredFieldType(str, Enum):
    """Database field type."""
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    JSON = "json"
    UUID = "uuid"
    ENUM = "enum"
    RELATION = "relation"


@dataclass
class Evidence:
    """Evidence for inference."""
    source: EvidenceSource
    file: str
    line: int
    content: str
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class InferredField:
    """Inferred model field."""
    name: str
    field_type: InferredFieldType
    nullable: bool = False
    unique: bool = False
    indexed: bool = False
    default: Any = None
    constraints: dict = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    relation_to: str | None = None
    relation_type: InferredRelationType | None = None
    enum_values: list[str] = field(default_factory=list)


@dataclass
class InferredModel:
    """Inferred data model."""
    name: str
    fields: list[InferredField] = field(default_factory=list)
    primary_key: str = "id"
    timestamps: bool = True
    soft_delete: bool = False
    indexes: list[list[str]] = field(default_factory=list)
    unique_constraints: list[list[str]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class InferredRelation:
    """Inferred relationship."""
    source_model: str
    target_model: str
    relation_type: InferredRelationType
    source_field: str
    target_field: str
    through_model: str | None = None
    cascade_delete: bool = False
    evidence: list[Evidence] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# NEW: API CONTRACT TYPES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PathParam:
    """API path parameter."""
    name: str
    param_type: str = "string"
    required: bool = True


@dataclass
class QueryParam:
    """API query parameter."""
    name: str
    param_type: str = "string"
    required: bool = False
    default: Any = None


@dataclass
class RequestBodySchema:
    """Request body schema."""
    content_type: str = "application/json"
    schema: dict = field(default_factory=dict)
    required: bool = True


@dataclass
class ResponseSchema:
    """Response schema."""
    status_code: int
    content_type: str = "application/json"
    schema: dict = field(default_factory=dict)
    description: str = ""


@dataclass
class ApiEndpointContract:
    """Synthesized API endpoint."""
    id: str
    method: str
    path: str
    path_params: list[PathParam] = field(default_factory=list)
    query_params: list[QueryParam] = field(default_factory=list)
    request_body: RequestBodySchema | None = None
    responses: list[ResponseSchema] = field(default_factory=list)
    requires_auth: bool = False
    permissions: list[str] = field(default_factory=list)
    rate_limit: int | None = None
    cache_ttl: int | None = None
    tags: list[str] = field(default_factory=list)
    description: str = ""
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ApiResourceContract:
    """Group of related endpoints."""
    name: str
    base_path: str
    endpoints: list[ApiEndpointContract] = field(default_factory=list)
    model: str | None = None
    middleware: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# NEW: AUTH TYPES
# ═══════════════════════════════════════════════════════════════════════════

class AuthStrategy(str, Enum):
    """Authentication strategy."""
    JWT = "jwt"
    SESSION = "session"
    OAUTH = "oauth"
    API_KEY = "api_key"
    HYBRID = "hybrid"


class PermissionModel(str, Enum):
    """Permission model type."""
    RBAC = "rbac"
    ABAC = "abac"
    SIMPLE = "simple"


@dataclass
class RoleDefinition:
    """Role definition."""
    name: str
    permissions: list[str] = field(default_factory=list)
    inherits: list[str] = field(default_factory=list)


@dataclass
class PermissionDefinition:
    """Permission definition."""
    name: str
    resource: str
    actions: list[str] = field(default_factory=list)


@dataclass
class OAuthProviderConfig:
    """OAuth provider configuration."""
    name: str
    client_id_env: str
    client_secret_env: str
    scopes: list[str] = field(default_factory=list)


@dataclass
class AuthRequirements:
    """Inferred auth requirements."""
    strategy: AuthStrategy
    permission_model: PermissionModel
    roles: list[RoleDefinition] = field(default_factory=list)
    permissions: list[PermissionDefinition] = field(default_factory=list)
    oauth_providers: list[OAuthProviderConfig] = field(default_factory=list)
    session_config: dict = field(default_factory=dict)
    jwt_config: dict = field(default_factory=dict)
    password_policy: dict = field(default_factory=dict)
    mfa_required: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# NEW: SCHEMA DESIGN TYPES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DatabaseColumn:
    """Database column definition."""
    name: str
    db_type: str
    nullable: bool = False
    primary_key: bool = False
    unique: bool = False
    default: Any = None
    references: str | None = None


@dataclass
class DatabaseIndex:
    """Database index definition."""
    name: str
    columns: list[str]
    unique: bool = False
    index_type: str = "btree"


@dataclass
class DatabaseTable:
    """Database table definition."""
    name: str
    columns: list[DatabaseColumn] = field(default_factory=list)
    indexes: list[DatabaseIndex] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    foreign_keys: list[dict] = field(default_factory=list)


@dataclass
class DatabaseSchema:
    """Complete database schema."""
    tables: list[DatabaseTable] = field(default_factory=list)
    enums: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Migration:
    """Database migration."""
    id: str
    name: str
    up_sql: str
    down_sql: str
    created_at: datetime = field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# NEW: SERVICE ARCHITECTURE TYPES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RepositoryMethod:
    """Repository method definition."""
    name: str
    return_type: str
    parameters: list[dict] = field(default_factory=list)
    query_type: str = "select"


@dataclass
class RepositoryDefinition:
    """Repository definition."""
    name: str
    model: str
    methods: list[RepositoryMethod] = field(default_factory=list)


@dataclass
class ServiceMethod:
    """Service method definition."""
    name: str
    return_type: str
    parameters: list[dict] = field(default_factory=list)
    business_logic: str = ""
    repository_calls: list[str] = field(default_factory=list)
    transaction_boundary: bool = False


@dataclass
class ServiceDefinition:
    """Service definition."""
    name: str
    dependencies: list[str] = field(default_factory=list)
    methods: list[ServiceMethod] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# NEW: EXECUTION TYPES
# ═══════════════════════════════════════════════════════════════════════════

class ChangeType(str, Enum):
    """File change type."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RENAME = "rename"


@dataclass
class FileChange:
    """File change."""
    change_type: ChangeType
    path: str
    content: str | None = None
    old_path: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ChangeSet:
    """Set of atomic changes."""
    id: str
    description: str
    changes: list[FileChange] = field(default_factory=list)
    rollback_changes: list[FileChange] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    """Validation result."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# NEW: ORCHESTRATION TYPES
# ═══════════════════════════════════════════════════════════════════════════

class TaskType(str, Enum):
    """Task type."""
    GENERATE_BACKEND = "generate_backend"
    ADD_ENDPOINT = "add_endpoint"
    ADD_MODEL = "add_model"
    ADD_AUTH = "add_auth"
    ADD_INTEGRATION = "add_integration"
    SYNC_FRONTEND = "sync_frontend"
    REFACTOR = "refactor"


class TaskStatus(str, Enum):
    """Task status."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class TaskStep:
    """Task step."""
    id: str
    name: str
    description: str
    action: str
    parameters: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    rollback_action: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None


@dataclass
class TaskPlan:
    """Task execution plan."""
    id: str
    task_type: TaskType
    description: str
    steps: list[TaskStep] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    risk_level: str = "low"
    estimated_time_ms: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Checkpoint:
    """Rollback checkpoint."""
    id: str
    task_id: str
    step_id: str
    file_states: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentSession:
    """Agent session."""
    id: str
    project_path: str
    current_task: TaskPlan | None = None
    checkpoints: list[Checkpoint] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# NEW: GENERATION OUTPUT TYPES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GeneratedFile:
    """Generated file."""
    path: str
    content: str
    file_type: str
    generator: str
    metadata: dict = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result of code generation."""
    success: bool
    files: list[GeneratedFile] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


@dataclass
class BackendArchitecture:
    """Complete backend architecture."""
    models: list[InferredModel] = field(default_factory=list)
    relations: list[InferredRelation] = field(default_factory=list)
    api_resources: list[ApiResourceContract] = field(default_factory=list)
    auth: AuthRequirements | None = None
    schema: DatabaseSchema | None = None
    repositories: list[RepositoryDefinition] = field(default_factory=list)
    services: list[ServiceDefinition] = field(default_factory=list)