# PostgreSQL converter
"""
PostgreSQL Converter
"""

from datetime import datetime
from database_generation.converters.base import BaseConverter
from database_generation.db_types import (
    ForgeSchema,
    EntityDef,
    FieldDef,
    FieldType,
    EditorType
)


class PostgreSQLConverter(BaseConverter):
    """Converts ForgeSchema to PostgreSQL DDL"""
    
    TYPE_MAP = {
        FieldType.UUID: "UUID",
        FieldType.STRING: "VARCHAR",
        FieldType.TEXT: "TEXT",
        FieldType.INTEGER: "INTEGER",
        FieldType.BIGINT: "BIGINT",
        FieldType.DECIMAL: "NUMERIC",
        FieldType.FLOAT: "DOUBLE PRECISION",
        FieldType.BOOLEAN: "BOOLEAN",
        FieldType.DATE: "DATE",
        FieldType.TIME: "TIME",
        FieldType.TIMESTAMP: "TIMESTAMPTZ",
        FieldType.JSON: "JSONB",
        FieldType.ARRAY: "TEXT[]",
        FieldType.ENUM: "VARCHAR(50)",
        FieldType.BINARY: "BYTEA",
    }
    
    def convert(self, schema: ForgeSchema) -> str:
        """Convert schema to PostgreSQL DDL"""
        
        parts = [
            self._header(schema),
            self._extensions(),
            self._enums(schema),
            self._tables(schema),
            self._indexes(schema),
            self._triggers(schema),
            self._footer()
        ]
        
        return "\n\n".join(filter(None, parts))
    
    def format_for_editor(self, ddl: str, editor: EditorType) -> str:
        """Format DDL for editor"""
        
        if editor == EditorType.PGADMIN:
            return f"\\set ON_ERROR_STOP on\n\n{ddl}"
        elif editor == EditorType.DBEAVER:
            return f"-- @delimiter ;\n\n{ddl}"
        
        return ddl
    
    def _header(self, schema: ForgeSchema) -> str:
        return f"""-- =============================================
-- FORGE Generated Schema: {schema.name}
-- Database: PostgreSQL
-- App Type: {schema.app_type.value}
-- Generated: {datetime.now().isoformat()}
-- =============================================

BEGIN;"""
    
    def _extensions(self) -> str:
        return """-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";"""
    
    def _enums(self, schema: ForgeSchema) -> str:
        if not schema.enums:
            return ""
        
        lines = ["-- Enums"]
        for enum in schema.enums:
            values = ", ".join(f"'{v}'" for v in enum.values)
            lines.append(f"""DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum.name}') THEN
        CREATE TYPE {enum.name} AS ENUM ({values});
    END IF;
END $$;""")
        
        return "\n\n".join(lines)
    
    def _tables(self, schema: ForgeSchema) -> str:
        tables = ["-- Tables"]
        
        for entity in schema.entities:
            tables.append(self._table(entity))
        
        return "\n\n".join(tables)
    
    def _table(self, entity: EntityDef) -> str:
        lines = [f"-- Table: {entity.name}"]
        lines.append(f"CREATE TABLE IF NOT EXISTS {entity.name} (")
        
        field_lines = []
        for field in entity.fields:
            field_lines.append(self._field(field))
        
        # Timestamps
        if entity.timestamps:
            field_lines.append("    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
            field_lines.append("    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
        
        if entity.soft_delete:
            field_lines.append("    deleted_at TIMESTAMPTZ")
        
        lines.append(",\n".join(field_lines))
        lines.append(");")
        
        if entity.comment:
            lines.append(f"\nCOMMENT ON TABLE {entity.name} IS '{entity.comment}';")
        
        return "\n".join(lines)
    
    def _field(self, field: FieldDef) -> str:
        parts = [f"    {field.name}"]
        
        # Type
        sql_type = self._get_type(field)
        parts.append(sql_type)
        
        # Constraints
        if field.primary_key:
            parts.append("PRIMARY KEY")
        
        if field.required and not field.primary_key:
            parts.append("NOT NULL")
        
        if field.unique and not field.primary_key:
            parts.append("UNIQUE")
        
        # Default
        if field.default_function:
            parts.append(f"DEFAULT {field.default_function}")
        elif field.default is not None:
            default_val = self._format_default(field.default)
            parts.append(f"DEFAULT {default_val}")
        
        # Check
        if field.check:
            parts.append(f"CHECK ({field.check})")
        
        # Foreign key
        if field.reference:
            ref = field.reference
            parts.append(
                f"REFERENCES {ref.entity}({ref.field}) "
                f"ON DELETE {ref.on_delete.value.upper()} "
                f"ON UPDATE {ref.on_update.value.upper()}"
            )
        
        return " ".join(parts)
    
    def _get_type(self, field: FieldDef) -> str:
        base_type = self.TYPE_MAP.get(field.type, "TEXT")
        
        if field.type == FieldType.STRING:
            length = field.length or 255
            return f"VARCHAR({length})"
        
        if field.type == FieldType.DECIMAL:
            precision = field.precision or 10
            scale = field.scale or 2
            return f"NUMERIC({precision}, {scale})"
        
        if field.type == FieldType.ENUM and field.enum_values:
            # Could use actual enum type here if defined
            return "VARCHAR(50)"
        
        return base_type
    
    def _format_default(self, value) -> str:
        if isinstance(value, bool):
            return str(value).upper()
        if isinstance(value, str):
            return f"'{value}'"
        if value is None:
            return "NULL"
        return str(value)
    
    def _indexes(self, schema: ForgeSchema) -> str:
        lines = ["-- Indexes"]
        
        for entity in schema.entities:
            for idx in entity.indexes:
                idx_name = idx.name or f"idx_{entity.name}_{'_'.join(idx.fields)}"
                unique = "UNIQUE " if idx.unique else ""
                using = f" USING {idx.type.value.upper()}" if idx.type.value != "btree" else ""
                columns = ", ".join(idx.fields)
                where = f" WHERE {idx.where}" if idx.where else ""
                
                lines.append(
                    f"CREATE {unique}INDEX IF NOT EXISTS {idx_name} "
                    f"ON {entity.name}{using} ({columns}){where};"
                )
        
        return "\n".join(lines) if len(lines) > 1 else ""
    
    def _triggers(self, schema: ForgeSchema) -> str:
        lines = ["""-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION forge_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;"""]
        
        for entity in schema.entities:
            if entity.timestamps:
                lines.append(f"""
DROP TRIGGER IF EXISTS {entity.name}_update_timestamp ON {entity.name};
CREATE TRIGGER {entity.name}_update_timestamp
    BEFORE UPDATE ON {entity.name}
    FOR EACH ROW
    EXECUTE FUNCTION forge_update_timestamp();""")
        
        return "\n".join(lines)
    
    def _footer(self) -> str:
        return """COMMIT;

-- =============================================
-- Schema generation complete
-- ============================================="""