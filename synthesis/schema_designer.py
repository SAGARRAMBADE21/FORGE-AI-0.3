"""Design database schema from inferred models."""

import logging
from datetime import datetime

from core.types import (
    InferredModel, InferredField, InferredRelation, InferredFieldType,
    InferredRelationType, DatabaseSchema, DatabaseTable, DatabaseColumn,
    DatabaseIndex, Migration
)
from core.utils import generate_id
from config.templates_config import PRISMA_TYPE_MAP

logger = logging.getLogger(__name__)


class SchemaDesigner:
    """
    Convert inferred models to database schema.
    
    Responsibilities:
    - Map field types to database types
    - Design foreign keys and indexes
    - Create junction tables for M:M
    - Generate migrations
    """

    def __init__(self, database_type: str = "postgresql"):
        self.database_type = database_type

    async def design_schema(
        self,
        models: list[InferredModel],
        relations: list[InferredRelation]
    ) -> DatabaseSchema:
        """Design complete database schema."""
        tables = []
        enums = {}

        # Create tables for models
        for model in models:
            table, model_enums = self._model_to_table(model)
            tables.append(table)
            enums.update(model_enums)

        # Create junction tables for M:M relations
        for rel in relations:
            if rel.relation_type == InferredRelationType.MANY_TO_MANY:
                if not rel.through_model:
                    junction = self._create_junction_table(rel)
                    tables.append(junction)

        # Add foreign key constraints
        tables = self._add_foreign_keys(tables, relations)

        # Optimize indexes
        tables = self._optimize_indexes(tables, relations)

        logger.info(f"Designed schema with {len(tables)} tables")
        return DatabaseSchema(tables=tables, enums=enums)

    def _model_to_table(self, model: InferredModel) -> tuple[DatabaseTable, dict]:
        """Convert model to database table."""
        columns = []
        enums = {}
        indexes = []

        for field in model.fields:
            col, field_enum = self._field_to_column(field, model.name)
            columns.append(col)
            
            if field_enum:
                enums[field_enum[0]] = field_enum[1]

            # Create index for indexed fields
            if field.indexed and not field.unique:
                indexes.append(DatabaseIndex(
                    name=f"idx_{model.name.lower()}_{field.name}",
                    columns=[field.name],
                    unique=False
                ))

        # Primary key
        pk_columns = [model.primary_key] if model.primary_key else ['id']

        # Multi-column indexes
        for idx_cols in model.indexes:
            indexes.append(DatabaseIndex(
                name=f"idx_{model.name.lower()}_{'_'.join(idx_cols)}",
                columns=idx_cols,
                unique=False
            ))

        # Unique constraints
        for unique_cols in model.unique_constraints:
            indexes.append(DatabaseIndex(
                name=f"uq_{model.name.lower()}_{'_'.join(unique_cols)}",
                columns=unique_cols,
                unique=True
            ))

        return DatabaseTable(
            name=model.name,
            columns=columns,
            indexes=indexes,
            primary_key=pk_columns,
            foreign_keys=[]
        ), enums

    def _field_to_column(
        self, 
        field: InferredField, 
        model_name: str
    ) -> tuple[DatabaseColumn, tuple | None]:
        """Convert field to database column."""
        db_type = self._map_type(field.field_type)
        enum_def = None

        # Handle enums
        if field.field_type == InferredFieldType.ENUM and field.enum_values:
            enum_name = f"{model_name}{field.name.capitalize()}"
            db_type = enum_name
            enum_def = (enum_name, field.enum_values)

        # Handle text for longer strings
        if field.field_type == InferredFieldType.STRING:
            if field.constraints.get('max_length', 0) > 255:
                db_type = 'TEXT'

        return DatabaseColumn(
            name=field.name,
            db_type=db_type,
            nullable=field.nullable,
            primary_key=field.name == 'id',
            unique=field.unique,
            default=self._map_default(field),
            references=None
        ), enum_def

    def _map_type(self, field_type: InferredFieldType) -> str:
        """Map field type to database type."""
        mapping = {
            InferredFieldType.STRING: 'VARCHAR(255)',
            InferredFieldType.TEXT: 'TEXT',
            InferredFieldType.INTEGER: 'INTEGER',
            InferredFieldType.FLOAT: 'DOUBLE PRECISION',
            InferredFieldType.DECIMAL: 'DECIMAL(10,2)',
            InferredFieldType.BOOLEAN: 'BOOLEAN',
            InferredFieldType.DATETIME: 'TIMESTAMP WITH TIME ZONE',
            InferredFieldType.DATE: 'DATE',
            InferredFieldType.JSON: 'JSONB',
            InferredFieldType.UUID: 'UUID',
        }
        return mapping.get(field_type, 'VARCHAR(255)')

    def _map_default(self, field: InferredField) -> str | None:
        """Map field default to SQL default."""
        if field.default is None:
            if field.name == 'id' and field.field_type == InferredFieldType.UUID:
                return 'gen_random_uuid()'
            if field.name in ('createdAt', 'created_at'):
                return 'CURRENT_TIMESTAMP'
            if field.name in ('updatedAt', 'updated_at'):
                return 'CURRENT_TIMESTAMP'
            return None

        if isinstance(field.default, bool):
            return 'TRUE' if field.default else 'FALSE'
        if isinstance(field.default, (int, float)):
            return str(field.default)
        if isinstance(field.default, str):
            return f"'{field.default}'"

        return None

    def _create_junction_table(self, relation: InferredRelation) -> DatabaseTable:
        """Create junction table for M:M relation."""
        table_name = f"{relation.source_model}{relation.target_model}"

        return DatabaseTable(
            name=table_name,
            columns=[
                DatabaseColumn(
                    name=f"{relation.source_model.lower()}Id",
                    db_type='UUID',
                    nullable=False,
                    references=f"{relation.source_model}.id"
                ),
                DatabaseColumn(
                    name=f"{relation.target_model.lower()}Id",
                    db_type='UUID',
                    nullable=False,
                    references=f"{relation.target_model}.id"
                ),
                DatabaseColumn(
                    name='createdAt',
                    db_type='TIMESTAMP WITH TIME ZONE',
                    nullable=False,
                    default='CURRENT_TIMESTAMP'
                ),
            ],
            indexes=[
                DatabaseIndex(
                    name=f"idx_{table_name.lower()}_unique",
                    columns=[f"{relation.source_model.lower()}Id", f"{relation.target_model.lower()}Id"],
                    unique=True
                )
            ],
            primary_key=[f"{relation.source_model.lower()}Id", f"{relation.target_model.lower()}Id"],
            foreign_keys=[
                {
                    'column': f"{relation.source_model.lower()}Id",
                    'references': f"{relation.source_model}.id",
                    'on_delete': 'CASCADE'
                },
                {
                    'column': f"{relation.target_model.lower()}Id",
                    'references': f"{relation.target_model}.id",
                    'on_delete': 'CASCADE'
                }
            ]
        )

    def _add_foreign_keys(
        self,
        tables: list[DatabaseTable],
        relations: list[InferredRelation]
    ) -> list[DatabaseTable]:
        """Add foreign key constraints to tables."""
        table_map = {t.name: t for t in tables}

        for rel in relations:
            if rel.relation_type in (InferredRelationType.MANY_TO_ONE, InferredRelationType.ONE_TO_ONE):
                if rel.source_model in table_map:
                    table = table_map[rel.source_model]
                    
                    # Find the FK column
                    for col in table.columns:
                        if col.name == rel.source_field:
                            col.references = f"{rel.target_model}.{rel.target_field}"
                            table.foreign_keys.append({
                                'column': rel.source_field,
                                'references': f"{rel.target_model}.{rel.target_field}",
                                'on_delete': 'CASCADE' if rel.cascade_delete else 'SET NULL'
                            })
                            break

        return tables

    def _optimize_indexes(
        self,
        tables: list[DatabaseTable],
        relations: list[InferredRelation]
    ) -> list[DatabaseTable]:
        """Add optimized indexes based on query patterns."""
        for table in tables:
            existing = {tuple(idx.columns) for idx in table.indexes}

            # Index all foreign keys
            for fk in table.foreign_keys:
                col = fk['column']
                if (col,) not in existing:
                    table.indexes.append(DatabaseIndex(
                        name=f"idx_{table.name.lower()}_{col}",
                        columns=[col],
                        unique=False
                    ))
                    existing.add((col,))

        return tables

    def generate_migrations(self, schema: DatabaseSchema) -> list[Migration]:
        """Generate migrations for schema."""
        migrations = []

        # Initial migration
        up_sql = self._generate_create_sql(schema)
        down_sql = self._generate_drop_sql(schema)

        migrations.append(Migration(
            id=generate_id(),
            name='initial_schema',
            up_sql=up_sql,
            down_sql=down_sql
        ))

        return migrations

    def _generate_create_sql(self, schema: DatabaseSchema) -> str:
        """Generate CREATE TABLE statements."""
        statements = []

        # Create enums first
        for enum_name, values in schema.enums.items():
            values_str = ', '.join(f"'{v}'" for v in values)
            statements.append(f"CREATE TYPE {enum_name} AS ENUM ({values_str});")

        # Create tables
        for table in schema.tables:
            statements.append(self._table_to_create_sql(table))

        return '\n\n'.join(statements)

    def _table_to_create_sql(self, table: DatabaseTable) -> str:
        """Generate CREATE TABLE for a single table."""
        lines = [f"CREATE TABLE {table.name} ("]
        
        col_defs = []
        for col in table.columns:
            col_def = f"  {col.name} {col.db_type}"
            if not col.nullable:
                col_def += " NOT NULL"
            if col.unique:
                col_def += " UNIQUE"
            if col.default:
                col_def += f" DEFAULT {col.default}"
            col_defs.append(col_def)

        # Primary key
        if table.primary_key:
            col_defs.append(f"  PRIMARY KEY ({', '.join(table.primary_key)})")

        # Foreign keys
        for fk in table.foreign_keys:
            ref_table, ref_col = fk['references'].split('.')
            on_delete = fk.get('on_delete', 'NO ACTION')
            col_defs.append(
                f"  FOREIGN KEY ({fk['column']}) REFERENCES {ref_table}({ref_col}) ON DELETE {on_delete}"
            )

        lines.append(',\n'.join(col_defs))
        lines.append(");")

        # Indexes
        for idx in table.indexes:
            unique = "UNIQUE " if idx.unique else ""
            lines.append(
                f"CREATE {unique}INDEX {idx.name} ON {table.name} ({', '.join(idx.columns)});"
            )

        return '\n'.join(lines)

    def _generate_drop_sql(self, schema: DatabaseSchema) -> str:
        """Generate DROP statements for rollback."""
        statements = []

        # Drop tables in reverse order
        for table in reversed(schema.tables):
            statements.append(f"DROP TABLE IF EXISTS {table.name} CASCADE;")

        # Drop enums
        for enum_name in schema.enums:
            statements.append(f"DROP TYPE IF EXISTS {enum_name};")

        return '\n'.join(statements)