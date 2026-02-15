"""
Data models for edit console
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class ActionType(str, Enum):
    """Types of edit actions"""
    RENAME = "rename"
    ADD = "add"
    REMOVE = "remove"
    MODIFY = "modify"
    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"


class TargetType(str, Enum):
    """Types of edit targets"""
    TABLE = "table"
    FIELD = "field"
    COLUMN = "column"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    LINE = "line"
    VALUE = "value"
    PROPERTY = "property"
    FILE = "file"


class FileType(str, Enum):
    """Supported file types"""
    SQL = "sql"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    JSON = "json"
    YAML = "yaml"
    UNKNOWN = "unknown"


@dataclass
class TargetLocation:
    """Location of an edit target"""
    name: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    column_start: Optional[int] = None
    column_end: Optional[int] = None


@dataclass
class Changes:
    """Details of changes to apply"""
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    additional_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EditIntent:
    """Parsed edit intent from NLP command"""
    action: ActionType
    target_type: TargetType
    target_location: TargetLocation
    changes: Changes
    confidence: float = 1.0
    raw_command: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "EditIntent":
        """Create EditIntent from dictionary"""
        return cls(
            action=ActionType(data.get("action", "modify")),
            target_type=TargetType(data.get("target_type", "line")),
            target_location=TargetLocation(**data.get("target_location", {})),
            changes=Changes(**data.get("changes", {})),
            confidence=data.get("confidence", 1.0),
            raw_command=data.get("raw_command", "")
        )


@dataclass
class EditResult:
    """Result of applying an edit"""
    success: bool
    original_content: str
    modified_content: str
    diff: str
    message: str
    errors: List[str] = field(default_factory=list)


@dataclass
class FileContext:
    """Context about the file being edited"""
    filename: str
    file_type: FileType
    content: str
    summary: str = ""
    line_count: int = 0
    
    def __post_init__(self):
        if not self.line_count:
            self.line_count = len(self.content.splitlines())
