# MySQL converter
"""
MySQL Converter
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


class MySQLConverter(BaseConverter):
    """Converts ForgeSchema to MySQL DDL"""
    
    TYPE_MAP = {
        FieldType.UUID: "CHAR(36)",
        FieldType.STRING: "VARCHAR",
        FieldType.TEXT: "TEXT",
        FieldType.INTEGER: "INT",
        FieldType.BIGINT: "BIGINT",
        FieldType.DECIMAL: "DECIMAL",
        FieldType.FLOAT: "DOUBLE",
        FieldType.BOOLEAN: "TINYINT(1)",
        FieldType.DATE: "DATE",
        FieldType.TIME: "TIME",
        FieldType.TIMESTAMP: "TIMESTAMP",
        FieldType.JSON: "JSON",
        FieldType.ARRAY: "JSON",
        FieldType.ENUM: "ENUM",
        FieldType.BINARY: "BLOB",
    }
    
    def convert(self, schema: ForgeSchema) -> str:
        """Convert schema to MySQL DDL"""
        
        parts = [
            self._header(schema),
            self._tables(schema),
            self._indexes(schema),
            self._triggers(schema),
            self._footer()
        ]
        
        return "\n\n".join(filter(None, parts))
    
    def format_for_editor(self, ddl: str, editor: EditorType) -> str:
        """Format DDL for editor"""
        
        if editor == EditorType.MYSQL_WORKBENCH:
            return f"-- MySQL Workbench Compatible\n\n{ddl}"
        
        return ddl
    
    def _header(self, schema: ForgeSchema) -> str:
        db_name = schema.name.replace("-", "_")
        return f"""-- =============================================
-- FORGE Generated Schema: {schema.name}
-- Database: MySQL
-- App Type: {schema.app_type.value}
-- Generated: {datetime.now().isoformat()}
-- =============================================

SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL';

CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `{db_name}`;"""
    
    def _tables(self, schema: ForgeSchema) -> str:
        tables = ["-- Tables"]
        
        for entity in schema.entities:
            tables.append(self._table(entity))
        
        return "\n\n".join(tables)
    
    def _table(self, entity: EntityDef) -> str:
        lines = [f"-- Table: {entity.name}"]
        lines.append(f"CREATE TABLE IF NOT EXISTS `{entity.name}` (")
        
        field_lines = []
        constraints = []
        
        # Track which timestamp fields are already defined
        field_names = {f.name for f in entity.fields}
        
        for field in entity.fields:
            field_sql, field_constraints = self._field(field, entity.name)
            field_lines.append(field_sql)
            constraints.extend(field_constraints)
        
        # Timestamps (only add if not already in fields)
        if entity.timestamps:
            if 'created_at' not in field_names:
                field_lines.append("    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
            if 'updated_at' not in field_names:
                field_lines.append("    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        
        if entity.soft_delete:
            field_lines.append("    `deleted_at` TIMESTAMP NULL")
        
        # Add constraints
        field_lines.extend(constraints)
        
        lines.append(",\n".join(field_lines))
        lines.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
        
        return "\n".join(lines)
    
    def _field(self, field: FieldDef, table_name: str) -> tuple:
        parts = [f"    `{field.name}`"]
        constraints = []
        
        # Type
        sql_type = self._get_type(field)
        parts.append(sql_type)
        
        # Null
        if field.required:
            parts.append("NOT NULL")
        else:
            parts.append("NULL")
        
        # Default
        default_sql = self._get_default(field)
        if default_sql:
            parts.append(f"DEFAULT {default_sql}")
        
        # Primary key
        if field.primary_key:
            constraints.append(f"    PRIMARY KEY (`{field.name}`)")
        
        # Unique
        if field.unique and not field.primary_key:
            constraints.append(f"    UNIQUE KEY `uk_{table_name}_{field.name}` (`{field.name}`)")
        
        # Foreign key
        if field.reference:
            ref = field.reference
            on_delete = ref.on_delete.value.upper().replace("_", " ")
            on_update = ref.on_update.value.upper().replace("_", " ")
            constraints.append(
                f"    CONSTRAINT `fk_{table_name}_{field.name}` "
                f"FOREIGN KEY (`{field.name}`) REFERENCES `{ref.entity}` (`{ref.field}`) "
                f"ON DELETE {on_delete} ON UPDATE {on_update}"
            )
        
        return " ".join(parts), constraints
    
    def _get_type(self, field: FieldDef) -> str:
        if field.type == FieldType.STRING:
            length = field.length or 255
            return f"VARCHAR({length})"
        
        if field.type == FieldType.DECIMAL:
            precision = field.precision or 10
            scale = field.scale or 2
            return f"DECIMAL({precision}, {scale})"
        
        if field.type == FieldType.ENUM and field.enum_values:
            values = ", ".join(f"'{v}'" for v in field.enum_values)
            return f"ENUM({values})"
        
        return self.TYPE_MAP.get(field.type, "TEXT")
    
    def _get_default(self, field: FieldDef) -> str:
        if field.default_function:
            mapping = {
                "uuid_generate_v4()": "(UUID())",
                "NOW()": "CURRENT_TIMESTAMP",
            }
            return mapping.get(field.default_function, field.default_function)
        
        if field.default is not None:
            if isinstance(field.default, bool):
                return "1" if field.default else "0"
            if isinstance(field.default, str):
                return f"'{field.default}'"
            return str(field.default)
        
        return ""
    
    def _indexes(self, schema: ForgeSchema) -> str:
        lines = ["-- Indexes"]
        
        for entity in schema.entities:
            for idx in entity.indexes:
                if idx.unique:  # Skip unique (handled in table)
                    continue
                
                idx_name = idx.name or f"idx_{entity.name}_{'_'.join(idx.fields)}"
                idx_type = "FULLTEXT " if idx.type.value == "fulltext" else ""
                columns = ", ".join(f"`{f}`" for f in idx.fields)
                
                lines.append(f"CREATE {idx_type}INDEX `{idx_name}` ON `{entity.name}` ({columns});")
        
        return "\n".join(lines) if len(lines) > 1 else ""
    
    def _triggers(self, schema: ForgeSchema) -> str:
        triggers = ["-- Triggers for UUID generation"]
        
        for entity in schema.entities:
            pk_field = next((f for f in entity.fields if f.primary_key), None)
            if pk_field and pk_field.type == FieldType.UUID:
                triggers.append(f"""
DELIMITER ;;
CREATE TRIGGER `{entity.name}_before_insert`
BEFORE INSERT ON `{entity.name}`
FOR EACH ROW
BEGIN
    IF NEW.`{pk_field.name}` IS NULL OR NEW.`{pk_field.name}` = '' THEN
        SET NEW.`{pk_field.name}` = UUID();
    END IF;
END;;
DELIMITER ;""")
        
        return "\n".join(triggers) if len(triggers) > 1 else ""
    
    def _footer(self) -> str:
        return """SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;

-- =============================================
-- Schema generation complete
-- ============================================="""