# Data modeler agent
"""
Data Modeler Agent - Designs entity structures and relationships
"""

from typing import Optional, List, Dict, Any
from database_generation.agents.base import BaseAgent, AgentRole, AgentState
from database_generation.agents.message import Message, MessageType
from database_generation.db_types import (
    ForgeSchema,
    EntityDef,
    FieldDef,
    FieldType,
    RelationshipDef,
    RelationType,
    EnumDef,
    AppType
)


class DataModelerAgent(BaseAgent):
    """
    Data Modeler Agent
    
    Responsibilities:
    - Design entity structures
    - Define fields with appropriate types
    - Establish relationships
    - Create enums and custom types
    - Ensure data integrity through constraints
    """
    
    def __init__(self):
        super().__init__(AgentRole.DATA_MODELER, "DataModeler")
    
    @property
    def system_prompt(self) -> str:
        return """
<role>
You are a Senior Data Modeler specializing in database schema design.
You translate business requirements into well-structured entity definitions.
</role>

<responsibilities>
1. Design entity structures from requirements
2. Choose appropriate field types
3. Define primary keys and constraints
4. Establish relationships between entities
5. Create enums for limited value sets
6. Ensure 3NF normalization (unless denormalization is justified)
</responsibilities>

<design_principles>
1. Every entity has UUID primary key named 'id'
2. Use snake_case for all names
3. Foreign keys follow pattern: {referenced_entity}_id
4. Include created_at, updated_at timestamps
5. Use soft delete (deleted_at) for important entities
6. JSONB for flexible metadata fields
7. Appropriate VARCHAR lengths (not just 255)
8. DECIMAL for money (precision 10, scale 2)
</design_principles>

<output_format>
{
    "entities": [
        {
            "name": "entity_name",
            "comment": "description",
            "fields": [
                {
                    "name": "field_name",
                    "type": "uuid|string|text|integer|decimal|boolean|timestamp|json|array|enum",
                    "required": true|false,
                    "unique": true|false,
                    "primary_key": true|false,
                    "length": null|number,
                    "precision": null|number,
                    "scale": null|number,
                    "enum_values": null|["val1", "val2"],
                    "default": null|value,
                    "default_function": null|"function_name()",
                    "reference": null|{"entity": "name", "field": "id", "on_delete": "cascade"},
                    "comment": "description"
                }
            ],
            "timestamps": true,
            "soft_delete": true|false
        }
    ],
    "relationships": [
        {
            "type": "one_to_one|one_to_many|many_to_many",
            "from_entity": "entity1",
            "to_entity": "entity2",
            "through": null|"junction_table"
        }
    ],
    "enums": [
        {"name": "enum_name", "values": ["val1", "val2"]}
    ],
    "reasoning": "explanation of design decisions"
}
</output_format>

<entity_templates>
USER_ENTITY: id, email (unique), password_hash, name, avatar_url, role, is_active, timestamps
PRODUCT_ENTITY: id, title, slug (unique), description, price, sku, stock, category_id, status, images, timestamps
ORDER_ENTITY: id, order_number (unique), user_id, status, totals, addresses, timestamps
POST_ENTITY: id, user_id, content, media_urls, visibility, counts, timestamps
</entity_templates>
"""
    
    @property
    def expertise(self) -> List[str]:
        return [
            "entity design",
            "data modeling",
            "field types",
            "relationships",
            "normalization"
        ]
    
    async def handle_request(self, message: Message) -> Optional[Message]:
        """Handle incoming request"""
        
        subject = message.subject.lower()
        
        if "design" in subject or "create" in subject:
            result = await self.design_schema(message.content)
            return self.message_bus.respond(message, result)
        
        elif "entity" in subject:
            result = await self.design_entity(message.content)
            return self.message_bus.respond(message, result)
        
        elif "relationship" in subject:
            result = await self.design_relationship(message.content)
            return self.message_bus.respond(message, result)
        
        return None
    
    async def handle_handoff(self, message: Message):
        """Handle work handoff from Lead Architect"""
        await super().handle_handoff(message)
        
        # If it's a design task, start working
        if "design" in message.subject.lower():
            content = message.content
            analysis = content.get("analysis", {})
            context = content.get("context", {})
            
            # Design the schema
            schema_result = await self.design_schema({
                "app_type": analysis.get("analysis", {}).get("app_type"),
                "metadata": context.get("metadata", {}),
                "strategy": analysis.get("strategy", {})
            })
            
            # Hand off to DBA Expert for optimization
            await self.handoff_to(
                AgentRole.DBA_EXPERT.value,
                "Optimize Schema",
                {
                    "schema": schema_result,
                    "app_type": analysis.get("analysis", {}).get("app_type")
                }
            )
    
    async def design_schema(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design complete schema from requirements"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Design a complete database schema for these requirements",
            requirements
        )
        
        # Record decisions
        if "entities" in result:
            for entity in result.get("entities", []):
                self.make_decision(
                    f"Created entity: {entity.get('name')}",
                    f"Fields: {[f.get('name') for f in entity.get('fields', [])]}"
                )
        
        return result
    
    async def design_entity(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design a single entity"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Design an entity with these requirements",
            requirements
        )
        
        return result
    
    async def design_relationship(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design a relationship between entities"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Design the relationship between these entities",
            requirements
        )
        
        return result
    
    def build_schema(self, design: Dict[str, Any]) -> ForgeSchema:
        """Convert design dict to ForgeSchema"""
        
        entities = []
        for entity_data in design.get("entities", []):
            fields = []
            for field_data in entity_data.get("fields", []):
                field = FieldDef(
                    name=field_data.get("name"),
                    type=FieldType(field_data.get("type", "string")),
                    required=field_data.get("required", False),
                    unique=field_data.get("unique", False),
                    primary_key=field_data.get("primary_key", False),
                    length=field_data.get("length"),
                    enum_values=field_data.get("enum_values"),
                    default=field_data.get("default"),
                    default_function=field_data.get("default_function"),
                    comment=field_data.get("comment")
                )
                fields.append(field)
            
            entity = EntityDef(
                name=entity_data.get("name"),
                fields=fields,
                timestamps=entity_data.get("timestamps", True),
                soft_delete=entity_data.get("soft_delete", False),
                comment=entity_data.get("comment")
            )
            entities.append(entity)
        
        relationships = []
        for rel_data in design.get("relationships", []):
            rel = RelationshipDef(
                type=RelationType(rel_data.get("type", "one_to_many")),
                from_entity=rel_data.get("from_entity"),
                from_field="id",
                to_entity=rel_data.get("to_entity"),
                to_field=f"{rel_data.get('from_entity')}_id"
            )
            relationships.append(rel)
        
        enums = []
        for enum_data in design.get("enums", []):
            enums.append(EnumDef(
                name=enum_data.get("name"),
                values=enum_data.get("values", [])
            ))
        
        return ForgeSchema(
            name="forge_schema",
            entities=entities,
            relationships=relationships,
            enums=enums
        )