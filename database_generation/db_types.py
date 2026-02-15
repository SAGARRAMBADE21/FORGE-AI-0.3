# Type definitions
"""
FORGE Core Types - Data Models
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# ============================================
# ENUMS
# ============================================

class FieldType(str, Enum):
    UUID = "uuid"
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    BIGINT = "bigint"
    DECIMAL = "decimal"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    TIME = "time"
    TIMESTAMP = "timestamp"
    JSON = "json"
    ARRAY = "array"
    ENUM = "enum"
    BINARY = "binary"


class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SQLITE = "sqlite"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"
    MARIADB = "mariadb"


class EditorType(str, Enum):
    CLI = "cli"
    PGADMIN = "pgadmin"
    MYSQL_WORKBENCH = "mysql_workbench"
    MONGODB_COMPASS = "mongodb_compass"
    DBEAVER = "dbeaver"


class AppType(str, Enum):
    ECOMMERCE = "ecommerce"
    SOCIAL = "social"
    SAAS = "saas"
    CONTENT = "content"
    MARKETPLACE = "marketplace"
    ANALYTICS = "analytics"
    UNKNOWN = "unknown"


class OnDeleteAction(str, Enum):
    CASCADE = "cascade"
    RESTRICT = "restrict"
    SET_NULL = "set_null"
    NO_ACTION = "no_action"


class RelationType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class IndexType(str, Enum):
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    FULLTEXT = "fulltext"


# ============================================
# INPUT MODEL (Pre-scanned Metadata)
# ============================================

class InputMetadata(BaseModel):
    """Pre-scanned frontend metadata input"""
    
    # Application info
    app_name: str = "app"
    framework: str = "unknown"
    
    # Detected entities from frontend
    entities: List[Dict[str, Any]] = []
    
    # API endpoints found
    api_endpoints: List[Dict[str, Any]] = []
    
    # Form structures
    forms: List[Dict[str, Any]] = []
    
    # State/Store patterns
    state_schemas: List[Dict[str, Any]] = []
    
    # Detected relationships
    relationships: List[Dict[str, Any]] = []
    
    # Additional hints
    hints: Dict[str, Any] = {}


# ============================================
# SCHEMA MODELS
# ============================================

class FieldReference(BaseModel):
    """Foreign key reference"""
    entity: str
    field: str = "id"
    on_delete: OnDeleteAction = OnDeleteAction.CASCADE
    on_update: OnDeleteAction = OnDeleteAction.CASCADE


class FieldDef(BaseModel):
    """Field definition"""
    name: str
    type: FieldType
    required: bool = False
    unique: bool = False
    primary_key: bool = False
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    enum_values: Optional[List[str]] = None
    default: Optional[Any] = None
    default_function: Optional[str] = None
    reference: Optional[FieldReference] = None
    check: Optional[str] = None
    comment: Optional[str] = None


class IndexDef(BaseModel):
    """Index definition"""
    name: Optional[str] = None
    fields: List[str]
    type: IndexType = IndexType.BTREE
    unique: bool = False
    where: Optional[str] = None


class EntityDef(BaseModel):
    """Entity/Table definition"""
    name: str
    fields: List[FieldDef]
    indexes: List[IndexDef] = []
    timestamps: bool = True
    soft_delete: bool = False
    comment: Optional[str] = None


class RelationshipDef(BaseModel):
    """Relationship definition"""
    type: RelationType
    from_entity: str
    from_field: str
    to_entity: str
    to_field: str = "id"
    through_entity: Optional[str] = None


class EnumDef(BaseModel):
    """Enum type definition"""
    name: str
    values: List[str]


class ForgeSchema(BaseModel):
    """Complete database schema"""
    name: str
    version: str = "1.0.0"
    app_type: AppType = AppType.UNKNOWN
    entities: List[EntityDef] = []
    relationships: List[RelationshipDef] = []
    enums: List[EnumDef] = []
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================
# OUTPUT MODELS
# ============================================

class GeneratedOutput(BaseModel):
    """Generated database output"""
    database_type: DatabaseType
    editor_type: EditorType
    ddl: str
    entities_count: int
    indexes_count: int
    warnings: List[str] = []


class ExecutionResult(BaseModel):
    """Database execution result"""
    success: bool
    message: str
    statements_executed: int = 0
    errors: List[str] = []
    duration_ms: float = 0


# ============================================
# AGENT CONTEXT
# ============================================

class AgentResponse(BaseModel):
    """Structured response from an agent"""
    agent: str
    success: bool
    data: Any
    reasoning: Optional[str] = None
    errors: List[str] = []


class PipelineContext(BaseModel):
    """Context passed through the pipeline"""
    model_config = ConfigDict(protected_namespaces=())
    
    input_metadata: InputMetadata
    app_type: Optional[AppType] = None
    schema: Optional[ForgeSchema] = None
    outputs: Dict[str, GeneratedOutput] = {}
    agent_responses: List[AgentResponse] = []