# Schema builder
"""
Schema Builder - Constructs database-specific schemas
"""

from typing import Dict, Any, List
from database_generation.db_types import (
    ForgeSchema,
    DatabaseType,
    EditorType,
    GeneratedOutput
)
from database_generation.converters import get_converter


class SchemaBuilder:
    """Builds database-specific DDL from ForgeSchema"""
    
    def build(self,
              schema: ForgeSchema,
              database_type: DatabaseType,
              editor_type: EditorType = EditorType.CLI) -> GeneratedOutput:
        """
        Build DDL for a specific database
        
        Args:
            schema: The ForgeSchema to convert
            database_type: Target database
            editor_type: Target editor format
        
        Returns:
            GeneratedOutput with DDL and metadata
        """
        
        converter = get_converter(database_type)
        
        if not converter:
            return GeneratedOutput(
                database_type=database_type,
                editor_type=editor_type,
                ddl="",
                entities_count=0,
                indexes_count=0,
                warnings=[f"No converter for {database_type}"]
            )
        
        # Convert schema
        ddl = converter.convert(schema)
        
        # Format for editor
        formatted_ddl = converter.format_for_editor(ddl, editor_type)
        
        # Count elements
        total_indexes = sum(len(e.indexes) for e in schema.entities)
        
        return GeneratedOutput(
            database_type=database_type,
            editor_type=editor_type,
            ddl=formatted_ddl,
            entities_count=len(schema.entities),
            indexes_count=total_indexes,
            warnings=[]
        )
    
    def build_all(self, schema: ForgeSchema) -> Dict[DatabaseType, GeneratedOutput]:
        """Build DDL for all supported databases"""
        
        results = {}
        
        for db_type in DatabaseType:
            results[db_type] = self.build(schema, db_type, EditorType.CLI)
        
        return results


# Singleton instance
schema_builder = SchemaBuilder()