"""Controller generator."""

import logging
from core.types import InferredModel
from synthesis.api_architect import ControllerDefinition

logger = logging.getLogger(__name__)


class ControllerGenerator:
    """Generate Express controllers."""

    def generate(
        self,
        controller: ControllerDefinition,
        model: InferredModel | None
    ) -> str:
        """Generate controller class."""
        model_name = model.name if model else controller.resource.capitalize()
        model_lower = model_name[0].lower() + model_name[1:]
        service_name = f'{model_name}Service'

        imports = f'''import {{ Request, Response, NextFunction }} from 'express';
import {{ {service_name} }} from '../services/{model_lower}.service';
import {{ Create{model_name}Input, Update{model_name}Input }} from '../repositories/{model_lower}.repository';
'''

        # Response helpers
        helpers = '''
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: { message: string; code?: string };
  meta?: { page?: number; limit?: number; total?: number };
}

function success<T>(res: Response, data: T, meta?: ApiResponse<T>['meta'], status = 200) {
  res.status(status).json({ success: true, data, meta });
}

function error(res: Response, message: string, status = 500, code?: string) {
  res.status(status).json({ success: false, error: { message, code } });
}
'''

        # Controller class
        class_def = f'''
export class {controller.name} {{
  constructor(private service: {service_name}) {{}}

  /**
   * GET / - Get all items
   */
  getAll = async (req: Request, res: Response, next: NextFunction): Promise<void> => {{
    try {{
      const {{ page, limit, sortBy, sortOrder, ...filter }} = req.query;
      
      const result = await this.service.getAll(
        filter as any,
        {{
          page: page ? parseInt(page as string) : undefined,
          limit: limit ? parseInt(limit as string) : undefined,
          sortBy: sortBy as string,
          sortOrder: sortOrder as 'asc' | 'desc',
        }}
      );

      success(res, result.data, {{
        page: result.page,
        limit: result.limit,
        total: result.total,
      }});
    }} catch (err) {{
      next(err);
    }}
  }};

  /**
   * GET /:id - Get item by ID
   */
  getById = async (req: Request, res: Response, next: NextFunction): Promise<void> => {{
    try {{
      const {{ id }} = req.params;
      const item = await this.service.getById(id);
      success(res, item);
    }} catch (err) {{
      if ((err as Error).name === '{model_name}NotFoundError') {{
        error(res, (err as Error).message, 404, 'NOT_FOUND');
        return;
      }}
      next(err);
    }}
  }};

  /**
   * POST / - Create new item
   */
  create = async (req: Request, res: Response, next: NextFunction): Promise<void> => {{
    try {{
      const data: Create{model_name}Input = req.body;
      const created = await this.service.create(data);
      success(res, created, undefined, 201);
    }} catch (err) {{
      if ((err as Error).name === '{model_name}ValidationError') {{
        error(res, (err as Error).message, 400, 'VALIDATION_ERROR');
        return;
      }}
      next(err);
    }}
  }};

  /**
   * PUT /:id - Update item
   */
  update = async (req: Request, res: Response, next: NextFunction): Promise<void> => {{
    try {{
      const {{ id }} = req.params;
      const data: Update{model_name}Input = req.body;
      const updated = await this.service.update(id, data);
      success(res, updated);
    }} catch (err) {{
      if ((err as Error).name === '{model_name}NotFoundError') {{
        error(res, (err as Error).message, 404, 'NOT_FOUND');
        return;
      }}
      if ((err as Error).name === '{model_name}ValidationError') {{
        error(res, (err as Error).message, 400, 'VALIDATION_ERROR');
        return;
      }}
      next(err);
    }}
  }};

  /**
   * PATCH /:id - Partial update
   */
  patch = async (req: Request, res: Response, next: NextFunction): Promise<void> => {{
    try {{
      const {{ id }} = req.params;
      const data: Partial<Update{model_name}Input> = req.body;
      const updated = await this.service.update(id, data);
      success(res, updated);
    }} catch (err) {{
      if ((err as Error).name === '{model_name}NotFoundError') {{
        error(res, (err as Error).message, 404, 'NOT_FOUND');
        return;
      }}
      next(err);
    }}
  }};

  /**
   * DELETE /:id - Delete item
   */
  delete = async (req: Request, res: Response, next: NextFunction): Promise<void> => {{
    try {{
      const {{ id }} = req.params;
      await this.service.delete(id);
      res.status(204).send();
    }} catch (err) {{
      if ((err as Error).name === '{model_name}NotFoundError') {{
        error(res, (err as Error).message, 404, 'NOT_FOUND');
        return;
      }}
      next(err);
    }}
  }};
}}
'''

        return imports + helpers + class_def