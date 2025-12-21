"""Prisma schema generator."""

import logging
from typing import Any

from core.types import InferredModel, InferredRelation, InferredFieldType, InferredRelationType
from config.templates_config import PRISMA_TYPE_MAP

logger = logging.getLogger(__name__)


class PrismaGenerator:
    """Generate Prisma schema from inferred models."""

    def generate(
        self,
        models: list[InferredModel],
        relations: list[InferredRelation],
        enums: dict[str, list[str]] | None = None
    ) -> str:
        """Generate complete Prisma schema."""
        parts = []

        # Generator and datasource
        parts.append(self._generate_header())

        # Enums
        if enums:
            for name, values in enums.items():
                parts.append(self._generate_enum(name, values))

        # Models
        for model in models:
            model_rels = [r for r in relations if r.source_model == model.name]
            parts.append(self._generate_model(model, model_rels, relations))

        return '\n\n'.join(parts)

    def _generate_header(self) -> str:
        """Generate schema header."""
        return '''generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}'''

    def _generate_enum(self, name: str, values: list[str]) -> str:
        """Generate enum definition."""
        values_str = '\n  '.join(values)
        return f'''enum {name} {{
  {values_str}
}}'''

    def _generate_model(
        self,
        model: InferredModel,
        outgoing_relations: list[InferredRelation],
        all_relations: list[InferredRelation]
    ) -> str:
        """Generate model definition."""
        lines = [f'model {model.name} {{']

        # Fields
        for field in model.fields:
            line = self._generate_field(field, model.name)
            lines.append(f'  {line}')

        # Relation fields
        for rel in outgoing_relations:
            if rel.relation_type == InferredRelationType.MANY_TO_ONE:
                lines.append(f'  {rel.source_field.rstrip("Id")} {rel.target_model}? @relation(fields: [{rel.source_field}], references: [{rel.target_field}])')

        # Inverse relations
        for rel in all_relations:
            if rel.target_model == model.name and rel.relation_type == InferredRelationType.MANY_TO_ONE:
                field_name = f'{rel.source_model.lower()}s'
                lines.append(f'  {field_name} {rel.source_model}[]')

        # Indexes
        if model.indexes:
            for idx in model.indexes:
                cols = ', '.join(idx)
                lines.append(f'  @@index([{cols}])')

        # Unique constraints
        if model.unique_constraints:
            for unique in model.unique_constraints:
                cols = ', '.join(unique)
                lines.append(f'  @@unique([{cols}])')

        lines.append('}')
        return '\n'.join(lines)

    def _generate_field(self, field, model_name: str) -> str:
        """Generate field definition."""
        parts = [field.name]

        # Type
        prisma_type = self._map_type(field.field_type)
        if field.nullable:
            prisma_type += '?'
        parts.append(prisma_type)

        # Attributes
        attrs = []

        if field.name == 'id':
            attrs.append('@id')
            if field.field_type == InferredFieldType.UUID:
                attrs.append('@default(uuid())')
            else:
                attrs.append('@default(autoincrement())')

        if field.unique and field.name != 'id':
            attrs.append('@unique')

        if field.name in ('createdAt', 'created_at'):
            attrs.append('@default(now())')

        if field.name in ('updatedAt', 'updated_at'):
            attrs.append('@updatedAt')

        if field.default is not None and field.name not in ('id', 'createdAt', 'updatedAt'):
            if isinstance(field.default, bool):
                attrs.append(f'@default({str(field.default).lower()})')
            elif isinstance(field.default, str):
                attrs.append(f'@default("{field.default}")')
            else:
                attrs.append(f'@default({field.default})')

        # Map to database column name if different
        if '_' in field.name:
            attrs.append(f'@map("{field.name}")')

        if attrs:
            parts.append(' '.join(attrs))

        return ' '.join(parts)

    def _map_type(self, field_type: InferredFieldType) -> str:
        """Map field type to Prisma type."""
        mapping = {
            InferredFieldType.STRING: 'String',
            InferredFieldType.TEXT: 'String',
            InferredFieldType.INTEGER: 'Int',
            InferredFieldType.FLOAT: 'Float',
            InferredFieldType.DECIMAL: 'Decimal',
            InferredFieldType.BOOLEAN: 'Boolean',
            InferredFieldType.DATETIME: 'DateTime',
            InferredFieldType.DATE: 'DateTime',
            InferredFieldType.JSON: 'Json',
            InferredFieldType.UUID: 'String',
        }
        return mapping.get(field_type, 'String')