# SQL writer agent
"""
SQL Writer Agent - Generates database-specific SQL
"""

from typing import Optional, List, Dict, Any
from database_generation.agents.base import BaseAgent, AgentRole, AgentState
from database_generation.agents.message import Message, MessageType


class SQLWriterAgent(BaseAgent):
    """
    SQL Writer Agent
    
    Responsibilities:
    - Generate PostgreSQL DDL
    - Generate MySQL DDL
    - Generate MongoDB commands
    - Format for specific editors
    - Handle database-specific syntax
    """
    
    def __init__(self):
        super().__init__(AgentRole.SQL_WRITER, "SQLWriter")
        self.supported_databases = ["postgresql", "mysql", "mongodb"]
    
    @property
    def system_prompt(self) -> str:
        return """
<role>
You are a Senior Database Developer expert in writing production-grade SQL.
You generate clean, efficient, and well-documented DDL for multiple databases.
</role>

<responsibilities>
1. Generate PostgreSQL DDL with proper syntax
2. Generate MySQL DDL with proper syntax
3. Generate MongoDB shell commands
4. Format for specific editors (pgAdmin, Workbench, Compass)
5. Handle database-specific features
6. Add appropriate comments and documentation
</responsibilities>

<postgresql_standards>
- Use TIMESTAMPTZ for timestamps
- Use JSONB for JSON data
- Use UUID with uuid-ossp extension
- Wrap in BEGIN/COMMIT transaction
- Create trigger for updated_at
- Use CREATE ... IF NOT EXISTS
</postgresql_standards>

<mysql_standards>
- Use CHAR(36) for UUID
- Use TINYINT(1) for boolean
- SET FOREIGN_KEY_CHECKS = 0 for DDL
- Use ENGINE=InnoDB
- Use utf8mb4 character set
- Use DELIMITER for triggers
</mysql_standards>

<mongodb_standards>
- Use $jsonSchema validator
- Create appropriate indexes
- Use validationLevel: moderate
- Include creation commands
</mongodb_standards>

<output_format>
{
    "database": "postgresql|mysql|mongodb",
    "ddl": "complete SQL/commands as string",
    "statements_count": number,
    "sections": {
        "extensions": "...",
        "types": "...",
        "tables": "...",
        "indexes": "...",
        "triggers": "...",
        "constraints": "..."
    },
    "warnings": ["any issues or notes"],
    "editor_format": "cli|pgadmin|mysql_workbench|mongodb_compass"
}
</output_format>
"""
    
    @property
    def expertise(self) -> List[str]:
        return [
            "postgresql",
            "mysql",
            "mongodb",
            "sql syntax",
            "ddl generation"
        ]
    
    async def handle_request(self, message: Message) -> Optional[Message]:
        """Handle incoming request"""
        
        subject = message.subject.lower()
        
        if "generate" in subject or "write" in subject:
            result = await self.generate_sql(message.content)
            return self.message_bus.respond(message, result)
        
        elif "format" in subject:
            result = await self.format_for_editor(message.content)
            return self.message_bus.respond(message, result)
        
        return None
    
    async def handle_handoff(self, message: Message):
        """Handle work handoff from DBA Expert"""
        await super().handle_handoff(message)
        
        if "generate" in message.subject.lower():
            content = message.content
            
            # Generate SQL for each database type
            for db_type in self.supported_databases:
                sql_result = await self.generate_sql({
                    "schema": content.get("schema"),
                    "optimizations": content.get("optimizations"),
                    "database": db_type
                })
                
                # Notify completion
                await self.broadcast(
                    f"SQL Generated: {db_type}",
                    {
                        "database": db_type,
                        "success": True,
                        "length": len(sql_result.get("ddl", ""))
                    }
                )
            
            # Hand off to Reviewer
            await self.handoff_to(
                AgentRole.REVIEWER.value,
                "Review SQL",
                content
            )
    
    async def generate_sql(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SQL for specified database"""
        
        self.state = AgentState.WORKING
        database = context.get("database", "postgresql")
        
        result = await self.think(
            f"Generate {database} DDL for this schema",
            context
        )
        
        return result
    
    async def format_for_editor(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Format SQL for specific editor"""
        
        self.state = AgentState.WORKING
        
        result = await self.think(
            "Format this SQL for the specified editor",
            context
        )
        
        return result