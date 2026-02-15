# Chat session
"""
Chat Session Management
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from database_generation.db_types import ForgeSchema, PipelineContext


class Message(BaseModel):
    """Single chat message"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}


class ChatSession(BaseModel):
    """Chat session state"""
    model_config = ConfigDict(protected_namespaces=())
    
    session_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Conversation history
    messages: List[Message] = []
    
    # Current schema being worked on
    schema: Optional[ForgeSchema] = None
    
    # Context
    app_type: Optional[str] = None
    target_database: str = "postgresql"
    target_editor: str = "cli"
    
    # Session state
    pending_confirmation: Optional[Dict[str, Any]] = None
    undo_stack: List[ForgeSchema] = []
    redo_stack: List[ForgeSchema] = []
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add message to history"""
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata or {}
        ))
    
    def get_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history"""
        recent = self.messages[-limit:] if len(self.messages) > limit else self.messages
        return [{"role": m.role, "content": m.content} for m in recent]
    
    def save_state(self):
        """Save current schema state for undo"""
        if self.schema:
            self.undo_stack.append(self.schema.model_copy(deep=True))
            self.redo_stack.clear()  # Clear redo on new change
            # Limit stack size
            if len(self.undo_stack) > 50:
                self.undo_stack.pop(0)
    
    def undo(self) -> bool:
        """Undo last schema change"""
        if self.undo_stack:
            if self.schema:
                self.redo_stack.append(self.schema.model_copy(deep=True))
            self.schema = self.undo_stack.pop()
            return True
        return False
    
    def redo(self) -> bool:
        """Redo last undone change"""
        if self.redo_stack:
            if self.schema:
                self.undo_stack.append(self.schema.model_copy(deep=True))
            self.schema = self.redo_stack.pop()
            return True
        return False
    
    def clear_history(self):
        """Clear conversation history"""
        self.messages.clear()
    
    def to_context(self) -> Dict[str, Any]:
        """Convert session to context for AI"""
        return {
            "app_type": self.app_type,
            "target_database": self.target_database,
            "has_schema": self.schema is not None,
            "entity_count": len(self.schema.entities) if self.schema else 0,
            "entities": [e.name for e in self.schema.entities] if self.schema else []
        }