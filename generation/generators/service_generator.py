"""Service layer generator."""

import logging
from core.types import InferredModel, ServiceDefinition, ServiceMethod

logger = logging.getLogger(__name__)


class ServiceGenerator:
    """Generate service classes with business logic."""

    def generate(
        self,
        service: ServiceDefinition,
        model: InferredModel | None
    ) -> str:
        """Generate service class."""
        service_name = service.name
        model_name = model.name if model else 'Entity'
        model_lower = model_name[0].lower() + model_name[1:]

        # Imports
        imports = [
            f"import {{ {model_name} }} from '@prisma/client';",
            f"import {{ {model_name}Repository, Create{model_name}Input, Update{model_name}Input }} from '../repositories/{model_lower}.repository';",
        ]

        if 'AuthService' in service.dependencies:
            imports.append("import { AuthService } from './auth.service';")

        # Error classes
        error_class = f'''
export class {model_name}NotFoundError extends Error {{
  constructor(id: string) {{
    super(`{model_name} with id ${{id}} not found`);
    this.name = '{model_name}NotFoundError';
  }}
}}

export class {model_name}ValidationError extends Error {{
  constructor(message: string) {{
    super(message);
    this.name = '{model_name}ValidationError';
  }}
}}
'''

        # Service class
        class_def = f'''
export class {service_name} {{
  constructor(
    private repository: {model_name}Repository,
  ) {{}}

  /**
   * Get {model_name} by ID
   */
  async getById(id: string): Promise<{model_name}> {{
    const item = await this.repository.findById(id);
    if (!item) {{
      throw new {model_name}NotFoundError(id);
    }}
    return item;
  }}

  /**
   * Get all {model_name}s with optional filtering
   */
  async getAll(filter?: Partial<{model_name}>, options?: {{
    page?: number;
    limit?: number;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  }}): Promise<{{
    data: {model_name}[];
    total: number;
    page: number;
    limit: number;
  }}> {{
    const page = options?.page || 1;
    const limit = options?.limit || 20;
    const skip = (page - 1) * limit;

    const [data, total] = await Promise.all([
      this.repository.findMany(filter, {{
        skip,
        take: limit,
        orderBy: options?.sortBy 
          ? {{ [options.sortBy]: options.sortOrder || 'asc' }}
          : {{ createdAt: 'desc' }},
      }}),
      this.repository.count(filter),
    ]);

    return {{ data, total, page, limit }};
  }}

  /**
   * Create new {model_name}
   */
  async create(data: Create{model_name}Input): Promise<{model_name}> {{
    // Validate input
    this.validateCreateInput(data);
    
    // Business logic before create
    const processedData = await this.beforeCreate(data);
    
    // Create
    const created = await this.repository.create(processedData);
    
    // Business logic after create
    await this.afterCreate(created);
    
    return created;
  }}

  /**
   * Update existing {model_name}
   */
  async update(id: string, data: Update{model_name}Input): Promise<{model_name}> {{
    // Ensure exists
    const existing = await this.getById(id);
    
    // Validate input
    this.validateUpdateInput(data, existing);
    
    // Business logic before update
    const processedData = await this.beforeUpdate(id, data, existing);
    
    // Update
    const updated = await this.repository.update(id, processedData);
    
    // Business logic after update
    await this.afterUpdate(updated, existing);
    
    return updated;
  }}

  /**
   * Delete {model_name}
   */
  async delete(id: string): Promise<void> {{
    // Ensure exists
    const existing = await this.getById(id);
    
    // Business logic before delete
    await this.beforeDelete(id, existing);
    
    // Delete
    await this.repository.delete(id);
    
    // Business logic after delete
    await this.afterDelete(existing);
  }}

  // ========== Validation Methods ==========

  private validateCreateInput(data: Create{model_name}Input): void {{
    // Add custom validation logic here
  }}

  private validateUpdateInput(data: Update{model_name}Input, existing: {model_name}): void {{
    // Add custom validation logic here
  }}

  // ========== Lifecycle Hooks ==========

  private async beforeCreate(data: Create{model_name}Input): Promise<Create{model_name}Input> {{
    // Add pre-create logic here
    return data;
  }}

  private async afterCreate(created: {model_name}): Promise<void> {{
    // Add post-create logic here (e.g., send notifications, emit events)
  }}

  private async beforeUpdate(
    id: string,
    data: Update{model_name}Input,
    existing: {model_name}
  ): Promise<Update{model_name}Input> {{
    // Add pre-update logic here
    return data;
  }}

  private async afterUpdate(updated: {model_name}, previous: {model_name}): Promise<void> {{
    // Add post-update logic here
  }}

  private async beforeDelete(id: string, existing: {model_name}): Promise<void> {{
    // Add pre-delete logic here (e.g., check dependencies)
  }}

  private async afterDelete(deleted: {model_name}): Promise<void> {{
    // Add post-delete logic here
  }}
}}
'''

        return '\n'.join(imports) + '\n' + error_class + class_def