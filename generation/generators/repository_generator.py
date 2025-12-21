"""Repository layer generator."""

import logging
from core.types import InferredModel, InferredRelation, RepositoryDefinition

logger = logging.getLogger(__name__)


class RepositoryGenerator:
    """Generate repository classes."""

    def generate(
        self,
        model: InferredModel,
        repository: RepositoryDefinition | None,
        relations: list[InferredRelation]
    ) -> str:
        """Generate repository for a model."""
        model_name = model.name
        model_lower = model_name[0].lower() + model_name[1:]

        # Build import statements
        imports = [
            f"import {{ PrismaClient, {model_name}, Prisma }} from '@prisma/client';",
        ]

        # Build input types
        create_fields = self._get_create_fields(model)
        update_fields = self._get_update_fields(model)

        input_types = f'''
export interface Create{model_name}Input {{
{self._format_fields(create_fields, required=True)}
}}

export interface Update{model_name}Input {{
{self._format_fields(update_fields, required=False)}
}}

export interface FindOptions {{
  skip?: number;
  take?: number;
  orderBy?: Prisma.{model_name}OrderByWithRelationInput;
  include?: Prisma.{model_name}Include;
}}
'''

        # Build class
        class_def = f'''
export class {model_name}Repository {{
  constructor(private prisma: PrismaClient) {{}}

  async findById(id: string, include?: Prisma.{model_name}Include): Promise<{model_name} | null> {{
    return this.prisma.{model_lower}.findUnique({{
      where: {{ id }},
      include,
    }});
  }}

  async findMany(
    where?: Prisma.{model_name}WhereInput,
    options?: FindOptions
  ): Promise<{model_name}[]> {{
    return this.prisma.{model_lower}.findMany({{
      where,
      skip: options?.skip,
      take: options?.take,
      orderBy: options?.orderBy,
      include: options?.include,
    }});
  }}

  async findFirst(where: Prisma.{model_name}WhereInput): Promise<{model_name} | null> {{
    return this.prisma.{model_lower}.findFirst({{ where }});
  }}

  async create(data: Create{model_name}Input): Promise<{model_name}> {{
    return this.prisma.{model_lower}.create({{ data }});
  }}

  async createMany(data: Create{model_name}Input[]): Promise<number> {{
    const result = await this.prisma.{model_lower}.createMany({{ data }});
    return result.count;
  }}

  async update(id: string, data: Update{model_name}Input): Promise<{model_name}> {{
    return this.prisma.{model_lower}.update({{
      where: {{ id }},
      data,
    }});
  }}

  async upsert(
    where: Prisma.{model_name}WhereUniqueInput,
    create: Create{model_name}Input,
    update: Update{model_name}Input
  ): Promise<{model_name}> {{
    return this.prisma.{model_lower}.upsert({{
      where,
      create,
      update,
    }});
  }}

  async delete(id: string): Promise<void> {{
    await this.prisma.{model_lower}.delete({{ where: {{ id }} }});
  }}

  async deleteMany(where: Prisma.{model_name}WhereInput): Promise<number> {{
    const result = await this.prisma.{model_lower}.deleteMany({{ where }});
    return result.count;
  }}

  async count(where?: Prisma.{model_name}WhereInput): Promise<number> {{
    return this.prisma.{model_lower}.count({{ where }});
  }}

  async exists(where: Prisma.{model_name}WhereInput): Promise<boolean> {{
    const count = await this.count(where);
    return count > 0;
  }}
'''

        # Add unique field finders
        for field in model.fields:
            if field.unique and field.name != 'id':
                field_type = self._get_ts_type(field)
                class_def += f'''
  async findBy{field.name[0].upper()}{field.name[1:]}({field.name}: {field_type}): Promise<{model_name} | null> {{
    return this.prisma.{model_lower}.findUnique({{
      where: {{ {field.name} }},
    }});
  }}
'''

        # Add relation methods
        for rel in relations:
            if rel.relation_type.value == 'one_to_many':
                target_lower = rel.target_model[0].lower() + rel.target_model[1:]
                class_def += f'''
  async findWith{rel.target_model}s(id: string): Promise<{model_name} & {{ {target_lower}s: any[] }} | null> {{
    return this.prisma.{model_lower}.findUnique({{
      where: {{ id }},
      include: {{ {target_lower}s: true }},
    }});
  }}
'''

        class_def += '}'

        return '\n'.join(imports) + '\n' + input_types + class_def

    def _get_create_fields(self, model: InferredModel) -> list[tuple[str, str, bool]]:
        """Get fields for create input."""
        skip_fields = {'id', 'createdAt', 'updatedAt', 'created_at', 'updated_at'}
        fields = []
        
        for field in model.fields:
            if field.name in skip_fields:
                continue
            ts_type = self._get_ts_type(field)
            required = not field.nullable and field.default is None
            fields.append((field.name, ts_type, required))
        
        return fields

    def _get_update_fields(self, model: InferredModel) -> list[tuple[str, str, bool]]:
        """Get fields for update input."""
        skip_fields = {'id', 'createdAt', 'updatedAt', 'created_at', 'updated_at'}
        fields = []
        
        for field in model.fields:
            if field.name in skip_fields:
                continue
            ts_type = self._get_ts_type(field)
            fields.append((field.name, ts_type, False))
        
        return fields

    def _format_fields(self, fields: list[tuple[str, str, bool]], required: bool) -> str:
        """Format fields for interface."""
        lines = []
        for name, ts_type, is_required in fields:
            optional = '' if (required and is_required) else '?'
            lines.append(f'  {name}{optional}: {ts_type};')
        return '\n'.join(lines)

    def _get_ts_type(self, field) -> str:
        """Get TypeScript type for field."""
        mapping = {
            'string': 'string',
            'text': 'string',
            'integer': 'number',
            'float': 'number',
            'decimal': 'number',
            'boolean': 'boolean',
            'datetime': 'Date',
            'date': 'Date',
            'json': 'Record<string, any>',
            'uuid': 'string',
        }
        field_type = field.field_type.value if hasattr(field.field_type, 'value') else str(field.field_type)
        return mapping.get(field_type, 'any')