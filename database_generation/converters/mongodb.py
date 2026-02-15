# MongoDB converter
"""
MongoDB Converter
"""

import json
from datetime import datetime
from database_generation.converters.base import BaseConverter
from database_generation.db_types import (
    ForgeSchema,
    EntityDef,
    FieldDef,
    FieldType,
    EditorType
)


class MongoDBConverter(BaseConverter):
    """Converts ForgeSchema to MongoDB commands"""
    
    BSON_TYPE_MAP = {
        FieldType.UUID: "string",
        FieldType.STRING: "string",
        FieldType.TEXT: "string",
        FieldType.INTEGER: "int",
        FieldType.BIGINT: "long",
        FieldType.DECIMAL: "decimal",
        FieldType.FLOAT: "double",
        FieldType.BOOLEAN: "bool",
        FieldType.DATE: "date",
        FieldType.TIME: "string",
        FieldType.TIMESTAMP: "date",
        FieldType.JSON: "object",
        FieldType.ARRAY: "array",
        FieldType.ENUM: "string",
        FieldType.BINARY: "binData",
    }
    
    def convert(self, schema: ForgeSchema) -> str:
        """Convert schema to MongoDB shell commands"""
        
        lines = [self._header(schema)]
        
        for entity in schema.entities:
            lines.append(self._collection(entity))
        
        lines.append(self._footer())
        
        return "\n\n".join(lines)
    
    def format_for_editor(self, script: str, editor: EditorType) -> str:
        """Format script for editor"""
        
        if editor == EditorType.MONGODB_COMPASS:
            return f"// MongoDB Compass Compatible\n\n{script}"
        
        return script
    
    def _header(self, schema: ForgeSchema) -> str:
        db_name = schema.name.replace("-", "_")
        return f"""// =============================================
// FORGE Generated Schema: {schema.name}
// Database: MongoDB
// App Type: {schema.app_type.value}
// Generated: {datetime.now().isoformat()}
// =============================================
// 
// Run this file in MongoDB shell with: mongosh
//

// Switch to database
// use {db_name};

// Or run in Node.js/JavaScript context:
const dbName = '{db_name}';
// const db = client.db(dbName);"""
    
    def _collection(self, entity: EntityDef) -> str:
        validator = self._build_validator(entity)
        indexes = self._build_indexes(entity)
        
        lines = [f"// Collection: {entity.name}"]
        
        # Create collection with pretty-printed JSON
        validator_json = json.dumps(validator, indent=2)
        lines.append(f"""db.createCollection("{entity.name}", {{
  validator: {validator_json},
  validationLevel: "moderate"
}});""")
        
        # Create indexes with pretty formatting
        if indexes:
            lines.append(f"\n// Indexes for {entity.name}")
            for idx in indexes:
                keys_json = json.dumps(idx["keys"], indent=2)
                opts_json = json.dumps(idx["options"], indent=2)
                lines.append(f'db.{entity.name}.createIndex(\n  {keys_json},\n  {opts_json}\n);')
        
        return "\n".join(lines)
    
    def _build_validator(self, entity: EntityDef) -> dict:
        required = []
        properties = {}
        
        for field in entity.fields:
            prop = self._field_validator(field)
            properties[field.name] = prop
            
            if field.required or field.primary_key:
                required.append(field.name)
        
        # Timestamps (only add if not already in fields)
        if entity.timestamps:
            if "created_at" not in properties:
                properties["created_at"] = {"bsonType": "date"}
                required.append("created_at")
            if "updated_at" not in properties:
                properties["updated_at"] = {"bsonType": "date"}
                required.append("updated_at")
        
        if entity.soft_delete:
            properties["deleted_at"] = {"bsonType": ["date", "null"]}
        
        return {
            "$jsonSchema": {
                "bsonType": "object",
                "required": required,
                "properties": properties
            }
        }
    
    def _field_validator(self, field: FieldDef) -> dict:
        bson_type = self.BSON_TYPE_MAP.get(field.type, "string")
        
        validator = {}
        
        if field.required:
            validator["bsonType"] = bson_type
        else:
            validator["bsonType"] = [bson_type, "null"]
        
        if field.type == FieldType.STRING and field.length:
            validator["maxLength"] = field.length
        
        if field.type == FieldType.ENUM and field.enum_values:
            validator["enum"] = field.enum_values
        
        if field.comment:
            validator["description"] = field.comment
        
        return validator
    
    def _build_indexes(self, entity: EntityDef) -> list:
        indexes = []
        
        # Primary key
        for field in entity.fields:
            if field.primary_key and field.name != "_id":
                indexes.append({
                    "keys": {field.name: 1},
                    "options": {"unique": True, "name": f"pk_{entity.name}_{field.name}"}
                })
        
        # Unique fields
        for field in entity.fields:
            if field.unique and not field.primary_key:
                indexes.append({
                    "keys": {field.name: 1},
                    "options": {"unique": True, "name": f"uk_{entity.name}_{field.name}"}
                })
        
        # Foreign keys
        for field in entity.fields:
            if field.reference:
                indexes.append({
                    "keys": {field.name: 1},
                    "options": {"name": f"fk_{entity.name}_{field.name}"}
                })
        
        # Custom indexes
        for idx in entity.indexes:
            keys = {f: 1 for f in idx.fields}
            indexes.append({
                "keys": keys,
                "options": {
                    "name": idx.name or f"idx_{entity.name}_custom",
                    "unique": idx.unique
                }
            })
        
        # Timestamps
        if entity.timestamps:
            indexes.append({
                "keys": {"created_at": -1},
                "options": {"name": f"idx_{entity.name}_created_at"}
            })
        
        return indexes
    
    def _footer(self) -> str:
        return """
// =============================================
// Schema generation complete
// =============================================
print("FORGE schema applied successfully");"""
    
    def to_json_schema(self, schema: ForgeSchema) -> dict:
        """Export as JSON schema for Compass import"""
        collections = {}
        
        for entity in schema.entities:
            collections[entity.name] = {
                "validator": self._build_validator(entity),
                "indexes": self._build_indexes(entity)
            }
        
        return {
            "database": schema.name,
            "collections": collections
        }