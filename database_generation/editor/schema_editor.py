# Schema editor
"""
Schema Editor - Programmatic schema editing
"""

from typing import Optional, List, Dict, Any
from database_generation.db_types import (
    ForgeSchema,
    EntityDef,
    FieldDef,
    FieldType,
    IndexDef,
    IndexType,
    RelationshipDef,
    RelationType,
    EnumDef,
    FieldReference,
    OnDeleteAction,
    AppType
)


class SchemaEditor:
    """Programmatic schema editor with fluent API"""
    
    def __init__(self, schema: ForgeSchema = None):
        """Initialize editor with optional existing schema"""
        self.schema = schema or ForgeSchema(name="forge_schema")
        self._history: List[ForgeSchema] = []
        self._future: List[ForgeSchema] = []
    
    def _save_state(self):
        """Save current state for undo"""
        self._history.append(self.schema.model_copy(deep=True))
        self._future.clear()
        if len(self._history) > 100:
            self._history.pop(0)
    
    def undo(self) -> bool:
        """Undo last change"""
        if self._history:
            self._future.append(self.schema.model_copy(deep=True))
            self.schema = self._history.pop()
            return True
        return False
    
    def redo(self) -> bool:
        """Redo last undone change"""
        if self._future:
            self._history.append(self.schema.model_copy(deep=True))
            self.schema = self._future.pop()
            return True
        return False
    
    # ==========================================
    # Entity Operations
    # ==========================================
    
    def create_entity(self, name: str, **kwargs) -> "EntityBuilder":
        """Create a new entity and return builder"""
        self._save_state()
        
        # Check if exists
        if any(e.name == name for e in self.schema.entities):
            raise ValueError(f"Entity '{name}' already exists")
        
        entity = EntityDef(
            name=name,
            fields=[
                FieldDef(
                    name="id",
                    type=FieldType.UUID,
                    primary_key=True,
                    required=True,
                    default_function="uuid_generate_v4()"
                )
            ],
            timestamps=kwargs.get("timestamps", True),
            soft_delete=kwargs.get("soft_delete", False),
            comment=kwargs.get("comment")
        )
        
        self.schema.entities.append(entity)
        return EntityBuilder(self, entity)
    
    def get_entity(self, name: str) -> Optional["EntityBuilder"]:
        """Get entity builder for existing entity"""
        entity = next((e for e in self.schema.entities if e.name == name), None)
        if entity:
            return EntityBuilder(self, entity)
        return None
    
    def remove_entity(self, name: str) -> "SchemaEditor":
        """Remove an entity"""
        self._save_state()
        
        self.schema.entities = [e for e in self.schema.entities if e.name != name]
        self.schema.relationships = [
            r for r in self.schema.relationships
            if r.from_entity != name and r.to_entity != name
        ]
        return self
    
    def rename_entity(self, old_name: str, new_name: str) -> "SchemaEditor":
        """Rename an entity"""
        self._save_state()
        
        entity = next((e for e in self.schema.entities if e.name == old_name), None)
        if not entity:
            raise ValueError(f"Entity '{old_name}' not found")
        
        entity.name = new_name
        
        # Update relationships
        for rel in self.schema.relationships:
            if rel.from_entity == old_name:
                rel.from_entity = new_name
            if rel.to_entity == old_name:
                rel.to_entity = new_name
        
        # Update foreign key references
        for e in self.schema.entities:
            for f in e.fields:
                if f.reference and f.reference.entity == old_name:
                    f.reference.entity = new_name
        
        return self
    
    # ==========================================
    # Relationship Operations
    # ==========================================
    
    def add_relationship(self,
                         from_entity: str,
                         to_entity: str,
                         rel_type: str = "one_to_many",
                         through: str = None) -> "SchemaEditor":
        """Add relationship between entities"""
        self._save_state()
        
        # Validate entities exist
        from_e = next((e for e in self.schema.entities if e.name == from_entity), None)
        to_e = next((e for e in self.schema.entities if e.name == to_entity), None)
        
        if not from_e:
            raise ValueError(f"Entity '{from_entity}' not found")
        if not to_e:
            raise ValueError(f"Entity '{to_entity}' not found")
        
        # Add foreign key
        fk_name = f"{from_entity}_id"
        if not any(f.name == fk_name for f in to_e.fields):
            to_e.fields.append(FieldDef(
                name=fk_name,
                type=FieldType.UUID,
                reference=FieldReference(
                    entity=from_entity,
                    field="id",
                    on_delete=OnDeleteAction.CASCADE
                )
            ))
        
        # Add relationship
        self.schema.relationships.append(RelationshipDef(
            type=RelationType(rel_type),
            from_entity=from_entity,
            from_field="id",
            to_entity=to_entity,
            to_field=fk_name,
            through_entity=through
        ))
        
        return self
    
    def remove_relationship(self, from_entity: str, to_entity: str) -> "SchemaEditor":
        """Remove relationship"""
        self._save_state()
        
        self.schema.relationships = [
            r for r in self.schema.relationships
            if not (r.from_entity == from_entity and r.to_entity == to_entity)
        ]
        return self
    
    # ==========================================
    # Enum Operations
    # ==========================================
    
    def add_enum(self, name: str, values: List[str]) -> "SchemaEditor":
        """Add enum type"""
        self._save_state()
        
        if any(e.name == name for e in self.schema.enums):
            raise ValueError(f"Enum '{name}' already exists")
        
        self.schema.enums.append(EnumDef(name=name, values=values))
        return self
    
    def remove_enum(self, name: str) -> "SchemaEditor":
        """Remove enum type"""
        self._save_state()
        self.schema.enums = [e for e in self.schema.enums if e.name != name]
        return self
    
    # ==========================================
    # Schema Operations
    # ==========================================
    
    def set_name(self, name: str) -> "SchemaEditor":
        """Set schema name"""
        self.schema.name = name
        return self
    
    def set_app_type(self, app_type: str) -> "SchemaEditor":
        """Set application type"""
        self.schema.app_type = AppType(app_type)
        return self
    
    def get_schema(self) -> ForgeSchema:
        """Get the schema"""
        return self.schema
    
    def to_dict(self) -> Dict[str, Any]:
        """Export schema as dictionary"""
        return self.schema.model_dump()
    
    def to_json(self, indent: int = 2) -> str:
        """Export schema as JSON"""
        return self.schema.model_dump_json(indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaEditor":
        """Create editor from dictionary"""
        schema = ForgeSchema(**data)
        return cls(schema)
    
    @classmethod
    def from_json(cls, json_str: str) -> "SchemaEditor":
        """Create editor from JSON"""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)


class EntityBuilder:
    """Fluent builder for entity modification"""
    
    def __init__(self, editor: SchemaEditor, entity: EntityDef):
        self.editor = editor
        self.entity = entity
    
    def add_field(self,
                  name: str,
                  field_type: str = "string",
                  **kwargs) -> "EntityBuilder":
        """Add a field to the entity"""
        self.editor._save_state()
        
        if any(f.name == name for f in self.entity.fields):
            raise ValueError(f"Field '{name}' already exists in '{self.entity.name}'")
        
        # Build reference if specified
        reference = None
        if kwargs.get("references"):
            ref_data = kwargs["references"]
            reference = FieldReference(
                entity=ref_data.get("entity"),
                field=ref_data.get("field", "id"),
                on_delete=OnDeleteAction(ref_data.get("on_delete", "cascade"))
            )
        
        field = FieldDef(
            name=name,
            type=FieldType(field_type),
            required=kwargs.get("required", False),
            unique=kwargs.get("unique", False),
            length=kwargs.get("length"),
            precision=kwargs.get("precision"),
            scale=kwargs.get("scale"),
            enum_values=kwargs.get("enum_values"),
            default=kwargs.get("default"),
            default_function=kwargs.get("default_function"),
            reference=reference,
            check=kwargs.get("check"),
            comment=kwargs.get("comment")
        )
        
        self.entity.fields.append(field)
        return self
    
    def remove_field(self, name: str) -> "EntityBuilder":
        """Remove a field"""
        self.editor._save_state()
        
        field = next((f for f in self.entity.fields if f.name == name), None)
        if not field:
            raise ValueError(f"Field '{name}' not found")
        if field.primary_key:
            raise ValueError("Cannot remove primary key")
        
        self.entity.fields = [f for f in self.entity.fields if f.name != name]
        return self
    
    def modify_field(self, name: str, **kwargs) -> "EntityBuilder":
        """Modify field properties"""
        self.editor._save_state()
        
        field = next((f for f in self.entity.fields if f.name == name), None)
        if not field:
            raise ValueError(f"Field '{name}' not found")
        
        for key, value in kwargs.items():
            if hasattr(field, key):
                setattr(field, key, value)
        
        return self
    
    def rename_field(self, old_name: str, new_name: str) -> "EntityBuilder":
        """Rename a field"""
        self.editor._save_state()
        
        field = next((f for f in self.entity.fields if f.name == old_name), None)
        if not field:
            raise ValueError(f"Field '{old_name}' not found")
        
        field.name = new_name
        
        # Update indexes
        for idx in self.entity.indexes:
            idx.fields = [new_name if f == old_name else f for f in idx.fields]
        
        return self
    
    def add_index(self,
                  fields: List[str],
                  unique: bool = False,
                  name: str = None,
                  index_type: str = "btree") -> "EntityBuilder":
        """Add index"""
        self.editor._save_state()
        
        idx_name = name or f"idx_{self.entity.name}_{'_'.join(fields)}"
        
        self.entity.indexes.append(IndexDef(
            name=idx_name,
            fields=fields,
            type=IndexType(index_type),
            unique=unique
        ))
        return self
    
    def remove_index(self, name: str) -> "EntityBuilder":
        """Remove index"""
        self.editor._save_state()
        self.entity.indexes = [i for i in self.entity.indexes if i.name != name]
        return self
    
    def set_timestamps(self, enabled: bool = True) -> "EntityBuilder":
        """Enable/disable timestamps"""
        self.entity.timestamps = enabled
        return self
    
    def set_soft_delete(self, enabled: bool = True) -> "EntityBuilder":
        """Enable/disable soft delete"""
        self.entity.soft_delete = enabled
        return self
    
    def set_comment(self, comment: str) -> "EntityBuilder":
        """Set entity comment"""
        self.entity.comment = comment
        return self
    
    def done(self) -> SchemaEditor:
        """Return to schema editor"""
        return self.editor