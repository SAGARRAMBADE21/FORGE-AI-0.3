# Command handler
"""
Command Handler - Execute parsed intents
"""

from typing import Dict, Any, Optional, Tuple
from database_generation.chat.session import ChatSession
from database_generation.chat.intent_parser import Intent
from database_generation.db_types import (
    ForgeSchema,
    EntityDef,
    FieldDef,
    FieldType,
    IndexDef,
    RelationshipDef,
    RelationType,
    FieldReference,
    OnDeleteAction,
    AppType
)
from database_generation.engine.schema_builder import schema_builder
from database_generation.db_types import DatabaseType, EditorType


class CommandHandler:
    """Handle and execute parsed commands"""
    
    def execute(self, 
                intent: Intent, 
                params: Dict[str, Any],
                session: ChatSession) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Execute a command
        
        Returns:
            Tuple of (success, message, result_data)
        """
        handler = getattr(self, f"_handle_{intent.value}", None)
        
        if handler:
            return handler(params, session)
        
        return False, f"Unknown command: {intent.value}", None
    
    def _handle_create_entity(self, params: Dict[str, Any], 
                              session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Create a new entity"""
        entity_name = params.get("entity_name", "").lower()
        
        if not entity_name:
            return False, "Entity name is required", None
        
        # Initialize schema if needed
        if not session.schema:
            session.schema = ForgeSchema(
                name="forge_schema",
                app_type=AppType(session.app_type) if session.app_type else AppType.UNKNOWN
            )
        
        # Check if entity exists
        existing = [e for e in session.schema.entities if e.name == entity_name]
        if existing:
            return False, f"Entity '{entity_name}' already exists", None
        
        # Save state for undo
        session.save_state()
        
        # Build fields
        fields = [
            FieldDef(
                name="id",
                type=FieldType.UUID,
                primary_key=True,
                required=True,
                default_function="uuid_generate_v4()"
            )
        ]
        
        # Add user-specified fields
        for f in params.get("fields", []):
            field_type = FieldType(f.get("type", "string"))
            fields.append(FieldDef(
                name=f["name"],
                type=field_type,
                required=False
            ))
        
        # Create entity
        entity = EntityDef(
            name=entity_name,
            fields=fields,
            timestamps=True
        )
        
        session.schema.entities.append(entity)
        
        field_names = [f.name for f in fields]
        return True, f"Created entity '{entity_name}' with fields: {', '.join(field_names)}", {
            "entity": entity_name,
            "fields": field_names
        }
    
    def _handle_add_field(self, params: Dict[str, Any],
                          session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Add field to entity"""
        entity_name = params.get("entity_name", "").lower()
        field_name = params.get("field_name", "").lower()
        field_type = params.get("field_type", "string")
        
        if not entity_name or not field_name:
            return False, "Entity name and field name are required", None
        
        if not session.schema:
            return False, "No schema exists. Create an entity first.", None
        
        # Find entity
        entity = next((e for e in session.schema.entities if e.name == entity_name), None)
        if not entity:
            return False, f"Entity '{entity_name}' not found", None
        
        # Check if field exists
        if any(f.name == field_name for f in entity.fields):
            return False, f"Field '{field_name}' already exists in '{entity_name}'", None
        
        # Save state
        session.save_state()
        
        # Add field
        new_field = FieldDef(
            name=field_name,
            type=FieldType(field_type),
            required=False
        )
        entity.fields.append(new_field)
        
        return True, f"Added field '{field_name}' ({field_type}) to '{entity_name}'", {
            "entity": entity_name,
            "field": field_name,
            "type": field_type
        }
    
    def _handle_remove_field(self, params: Dict[str, Any],
                             session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Remove field from entity"""
        entity_name = params.get("entity_name", "").lower()
        field_name = params.get("field_name", "").lower()
        
        if not entity_name or not field_name:
            return False, "Entity name and field name are required", None
        
        if not session.schema:
            return False, "No schema exists", None
        
        # Find entity
        entity = next((e for e in session.schema.entities if e.name == entity_name), None)
        if not entity:
            return False, f"Entity '{entity_name}' not found", None
        
        # Find and remove field
        field_idx = next((i for i, f in enumerate(entity.fields) if f.name == field_name), None)
        if field_idx is None:
            return False, f"Field '{field_name}' not found in '{entity_name}'", None
        
        # Prevent removing primary key
        if entity.fields[field_idx].primary_key:
            return False, "Cannot remove primary key field", None
        
        # Save state
        session.save_state()
        
        entity.fields.pop(field_idx)
        
        return True, f"Removed field '{field_name}' from '{entity_name}'", {
            "entity": entity_name,
            "field": field_name
        }
    
    def _handle_modify_field(self, params: Dict[str, Any],
                             session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Modify field properties"""
        entity_name = params.get("entity_name", "").lower()
        field_name = params.get("field_name", "").lower() if params.get("field_name") else None
        modification = params.get("modification", "").lower()
        
        if not session.schema:
            return False, "No schema exists", None
        
        entity = next((e for e in session.schema.entities if e.name == entity_name), None)
        if not entity:
            return False, f"Entity '{entity_name}' not found", None
        
        # If no field specified, might be modifying entity
        if not field_name:
            return False, "Please specify which field to modify", None
        
        field = next((f for f in entity.fields if f.name == field_name), None)
        if not field:
            return False, f"Field '{field_name}' not found in '{entity_name}'", None
        
        # Save state
        session.save_state()
        
        # Apply modification
        if modification == "unique":
            field.unique = True
            msg = f"Made '{entity_name}.{field_name}' unique"
        elif modification == "required":
            field.required = True
            msg = f"Made '{entity_name}.{field_name}' required"
        elif modification in ["optional", "nullable"]:
            field.required = False
            msg = f"Made '{entity_name}.{field_name}' optional"
        else:
            return False, f"Unknown modification: {modification}", None
        
        return True, msg, {
            "entity": entity_name,
            "field": field_name,
            "modification": modification
        }
    
    def _handle_add_relationship(self, params: Dict[str, Any],
                                 session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Add relationship between entities"""
        from_entity = params.get("from_entity", "").lower()
        to_entity = params.get("to_entity", "").lower()
        rel_type = params.get("type", "one_to_many")
        
        if not session.schema:
            return False, "No schema exists", None
        
        # Validate entities exist
        from_e = next((e for e in session.schema.entities if e.name == from_entity), None)
        to_e = next((e for e in session.schema.entities if e.name == to_entity), None)
        
        if not from_e:
            return False, f"Entity '{from_entity}' not found", None
        if not to_e:
            return False, f"Entity '{to_entity}' not found", None
        
        # Save state
        session.save_state()
        
        # Add foreign key field
        fk_field_name = f"{from_entity}_id"
        
        if not any(f.name == fk_field_name for f in to_e.fields):
            to_e.fields.append(FieldDef(
                name=fk_field_name,
                type=FieldType.UUID,
                required=False,
                reference=FieldReference(
                    entity=from_entity,
                    field="id",
                    on_delete=OnDeleteAction.CASCADE
                )
            ))
        
        # Add relationship
        session.schema.relationships.append(RelationshipDef(
            type=RelationType(rel_type),
            from_entity=from_entity,
            from_field="id",
            to_entity=to_entity,
            to_field=fk_field_name
        ))
        
        return True, f"Added {rel_type} relationship: {from_entity} → {to_entity}", {
            "from": from_entity,
            "to": to_entity,
            "type": rel_type
        }
    
    def _handle_add_index(self, params: Dict[str, Any],
                          session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Add index to entity"""
        entity_name = params.get("entity_name", "").lower()
        field_name = params.get("field_name", "").lower()
        
        if not session.schema:
            return False, "No schema exists", None
        
        entity = next((e for e in session.schema.entities if e.name == entity_name), None)
        if not entity:
            return False, f"Entity '{entity_name}' not found", None
        
        if not any(f.name == field_name for f in entity.fields):
            return False, f"Field '{field_name}' not found in '{entity_name}'", None
        
        # Save state
        session.save_state()
        
        # Add index
        idx_name = f"idx_{entity_name}_{field_name}"
        entity.indexes.append(IndexDef(
            name=idx_name,
            fields=[field_name]
        ))
        
        return True, f"Added index on '{entity_name}.{field_name}'", {
            "entity": entity_name,
            "field": field_name,
            "index": idx_name
        }
    
    def _handle_remove_entity(self, params: Dict[str, Any],
                              session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Remove entity"""
        entity_name = params.get("entity_name", "").lower()
        
        if not session.schema:
            return False, "No schema exists", None
        
        entity_idx = next(
            (i for i, e in enumerate(session.schema.entities) if e.name == entity_name),
            None
        )
        
        if entity_idx is None:
            return False, f"Entity '{entity_name}' not found", None
        
        # Save state
        session.save_state()
        
        session.schema.entities.pop(entity_idx)
        
        # Remove related relationships
        session.schema.relationships = [
            r for r in session.schema.relationships
            if r.from_entity != entity_name and r.to_entity != entity_name
        ]
        
        return True, f"Removed entity '{entity_name}'", {
            "entity": entity_name
        }
    
    def _handle_generate_sql(self, params: Dict[str, Any],
                             session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Generate SQL"""
        if not session.schema:
            return False, "No schema exists", None
        
        database = params.get("database", session.target_database)
        db_type = DatabaseType(database)
        editor_type = EditorType(session.target_editor)
        
        result = schema_builder.build(session.schema, db_type, editor_type)
        
        return True, f"Generated {database} SQL ({len(result.ddl)} characters)", {
            "database": database,
            "ddl": result.ddl,
            "entities_count": result.entities_count
        }
    
    def _handle_show_schema(self, params: Dict[str, Any],
                            session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Show current schema"""
        if not session.schema:
            return True, "No schema defined yet. Start by creating an entity.", None
        
        entities_info = []
        for entity in session.schema.entities:
            fields = [f"{f.name}:{f.type.value}" for f in entity.fields]
            entities_info.append({
                "name": entity.name,
                "fields": fields,
                "indexes": len(entity.indexes)
            })
        
        summary = f"Schema has {len(session.schema.entities)} entities:\n"
        for e in entities_info:
            summary += f"\n• {e['name']}: {', '.join(e['fields'][:5])}"
            if len(e['fields']) > 5:
                summary += f" (+{len(e['fields'])-5} more)"
        
        return True, summary, {"entities": entities_info}
    
    def _handle_undo(self, params: Dict[str, Any],
                     session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Undo last change"""
        if session.undo():
            return True, "Undid last change", None
        return False, "Nothing to undo", None
    
    def _handle_redo(self, params: Dict[str, Any],
                     session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Redo last undone change"""
        if session.redo():
            return True, "Redid last change", None
        return False, "Nothing to redo", None
    
    def _handle_help(self, params: Dict[str, Any],
                     session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Show help"""
        help_text = """
**FORGE Chat Commands:**

**Creating & Managing Entities:**
• "Create a users table with email and password"
• "Add a products entity"
• "Remove the orders table"

**Managing Fields:**
• "Add a phone field to users"
• "Remove email from users"  
• "Make email unique in users"
• "Make name required in products"

**Relationships:**
• "Users have many orders"
• "Orders belong to users"
• "Connect products and categories"

**Indexes:**
• "Add index on users.email"

**Generate & Export:**
• "Generate PostgreSQL SQL"
• "Show MySQL code"
• "Export to MongoDB"

**Other:**
• "Show schema" - View current schema
• "Undo" - Undo last change
• "Redo" - Redo undone change
• "Help" - Show this message
"""
        return True, help_text, None
    
    def _handle_explain(self, params: Dict[str, Any],
                        session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Explain something about the schema"""
        # This would typically use AI, but provide basic explanations
        return True, "I can explain schema decisions. What would you like to know?", None
    
    def _handle_suggest(self, params: Dict[str, Any],
                        session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Provide suggestions"""
        if not session.schema:
            return True, "Create a schema first, then I can suggest improvements.", None
        
        suggestions = []
        
        for entity in session.schema.entities:
            # Suggest indexes for foreign keys
            for field in entity.fields:
                if field.reference and not any(
                    field.name in idx.fields for idx in entity.indexes
                ):
                    suggestions.append(f"Add index on {entity.name}.{field.name} (foreign key)")
            
            # Suggest unique for email fields
            for field in entity.fields:
                if "email" in field.name and not field.unique:
                    suggestions.append(f"Make {entity.name}.{field.name} unique")
        
        if suggestions:
            return True, "Suggestions:\n• " + "\n• ".join(suggestions), {
                "suggestions": suggestions
            }
        
        return True, "Your schema looks good! No immediate suggestions.", None
    
    def _handle_export(self, params: Dict[str, Any],
                       session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Export schema"""
        return self._handle_generate_sql(params, session)
    
    def _handle_unknown(self, params: Dict[str, Any],
                        session: ChatSession) -> Tuple[bool, str, Optional[Dict]]:
        """Handle unknown intent"""
        return False, "I didn't understand that. Type 'help' for available commands.", None