"""Test generator."""

import logging
from core.types import InferredModel, ServiceDefinition

logger = logging.getLogger(__name__)


class TestGenerator:
    """Generate test files."""

    def generate_repository_tests(self, model: InferredModel) -> str:
        """Generate repository tests."""
        model_name = model.name
        model_lower = model_name[0].lower() + model_name[1:]

        return f'''import {{ describe, it, expect, beforeEach, afterEach, vi }} from 'vitest';
import {{ PrismaClient }} from '@prisma/client';
import {{ mockDeep, mockReset, DeepMockProxy }} from 'vitest-mock-extended';
import {{ {model_name}Repository }} from '../repositories/{model_lower}.repository';

describe('{model_name}Repository', () => {{
  let prisma: DeepMockProxy<PrismaClient>;
  let repository: {model_name}Repository;

  beforeEach(() => {{
    prisma = mockDeep<PrismaClient>();
    repository = new {model_name}Repository(prisma);
  }});

  afterEach(() => {{
    mockReset(prisma);
  }});

  describe('findById', () => {{
    it('should return {model_lower} when found', async () => {{
      const mock{model_name} = {{
        id: '1',
        createdAt: new Date(),
        updatedAt: new Date(),
      }};

      prisma.{model_lower}.findUnique.mockResolvedValue(mock{model_name} as any);

      const result = await repository.findById('1');

      expect(result).toEqual(mock{model_name});
      expect(prisma.{model_lower}.findUnique).toHaveBeenCalledWith({{
        where: {{ id: '1' }},
        include: undefined,
      }});
    }});

    it('should return null when not found', async () => {{
      prisma.{model_lower}.findUnique.mockResolvedValue(null);

      const result = await repository.findById('999');

      expect(result).toBeNull();
    }});
  }});

  describe('findMany', () => {{
    it('should return array of {model_lower}s', async () => {{
      const mock{model_name}s = [
        {{ id: '1', createdAt: new Date(), updatedAt: new Date() }},
        {{ id: '2', createdAt: new Date(), updatedAt: new Date() }},
      ];

      prisma.{model_lower}.findMany.mockResolvedValue(mock{model_name}s as any);

      const result = await repository.findMany();

      expect(result).toHaveLength(2);
    }});
  }});

  describe('create', () => {{
    it('should create and return {model_lower}', async () => {{
      const input = {{
        // Add required fields
      }};

      const mock{model_name} = {{
        id: '1',
        ...input,
        createdAt: new Date(),
        updatedAt: new Date(),
      }};

      prisma.{model_lower}.create.mockResolvedValue(mock{model_name} as any);

      const result = await repository.create(input as any);

      expect(result).toEqual(mock{model_name});
      expect(prisma.{model_lower}.create).toHaveBeenCalledWith({{
        data: input,
      }});
    }});
  }});

  describe('update', () => {{
    it('should update and return {model_lower}', async () => {{
      const input = {{
        // Add fields to update
      }};

      const mock{model_name} = {{
        id: '1',
        ...input,
        createdAt: new Date(),
        updatedAt: new Date(),
      }};

      prisma.{model_lower}.update.mockResolvedValue(mock{model_name} as any);

      const result = await repository.update('1', input as any);

      expect(result).toEqual(mock{model_name});
    }});
  }});

  describe('delete', () => {{
    it('should delete {model_lower}', async () => {{
      prisma.{model_lower}.delete.mockResolvedValue({{ id: '1' }} as any);

      await repository.delete('1');

      expect(prisma.{model_lower}.delete).toHaveBeenCalledWith({{
        where: {{ id: '1' }},
      }});
    }});
  }});

  describe('count', () => {{
    it('should return count', async () => {{
      prisma.{model_lower}.count.mockResolvedValue(5);

      const result = await repository.count();

      expect(result).toBe(5);
    }});
  }});
}});
'''

    def generate_service_tests(self, service: ServiceDefinition, model: InferredModel | None) -> str:
        """Generate service tests."""
        service_name = service.name
        model_name = model.name if model else 'Entity'
        model_lower = model_name[0].lower() + model_name[1:]

        return f'''import {{ describe, it, expect, beforeEach, vi }} from 'vitest';
import {{ {service_name} }} from '../services/{model_lower}.service';
import {{ {model_name}Repository }} from '../repositories/{model_lower}.repository';

describe('{service_name}', () => {{
  let service: {service_name};
  let mockRepository: {{
    findById: ReturnType<typeof vi.fn>;
    findMany: ReturnType<typeof vi.fn>;
    create: ReturnType<typeof vi.fn>;
    update: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
    count: ReturnType<typeof vi.fn>;
  }};

  beforeEach(() => {{
    mockRepository = {{
      findById: vi.fn(),
      findMany: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      count: vi.fn(),
    }};

    service = new {service_name}(mockRepository as unknown as {model_name}Repository);
  }});

  describe('getById', () => {{
    it('should return {model_lower} when found', async () => {{
      const mock{model_name} = {{ id: '1', createdAt: new Date() }};
      mockRepository.findById.mockResolvedValue(mock{model_name});

      const result = await service.getById('1');

      expect(result).toEqual(mock{model_name});
    }});

    it('should throw error when not found', async () => {{
      mockRepository.findById.mockResolvedValue(null);

      await expect(service.getById('999')).rejects.toThrow('{model_name} not found');
    }});
  }});

  describe('getAll', () => {{
    it('should return paginated results', async () => {{
      const mockItems = [{{ id: '1' }}, {{ id: '2' }}];
      mockRepository.findMany.mockResolvedValue(mockItems);
      mockRepository.count.mockResolvedValue(2);

      const result = await service.getAll(undefined, {{ page: 1, limit: 10 }});

      expect(result.data).toEqual(mockItems);
      expect(result.total).toBe(2);
      expect(result.page).toBe(1);
    }});
  }});

  describe('create', () => {{
    it('should create {model_lower}', async () => {{
      const input = {{ /* required fields */ }};
      const created = {{ id: '1', ...input }};
      mockRepository.create.mockResolvedValue(created);

      const result = await service.create(input as any);

      expect(result).toEqual(created);
      expect(mockRepository.create).toHaveBeenCalled();
    }});
  }});

  describe('update', () => {{
    it('should update {model_lower}', async () => {{
      const existing = {{ id: '1', createdAt: new Date() }};
      const input = {{ /* fields to update */ }};
      const updated = {{ ...existing, ...input }};

      mockRepository.findById.mockResolvedValue(existing);
      mockRepository.update.mockResolvedValue(updated);

      const result = await service.update('1', input as any);

      expect(result).toEqual(updated);
    }});

    it('should throw if {model_lower} not found', async () => {{
      mockRepository.findById.mockResolvedValue(null);

      await expect(service.update('999', {{}} as any)).rejects.toThrow();
    }});
  }});

  describe('delete', () => {{
    it('should delete {model_lower}', async () => {{
      const existing = {{ id: '1' }};
      mockRepository.findById.mockResolvedValue(existing);
      mockRepository.delete.mockResolvedValue(undefined);

      await service.delete('1');

      expect(mockRepository.delete).toHaveBeenCalledWith('1');
    }});
  }});
}});
'''

    def generate_controller_tests(self, controller_name: str, model: InferredModel | None) -> str:
        """Generate controller tests."""
        model_name = model.name if model else 'Entity'
        model_lower = model_name[0].lower() + model_name[1:]

        return f'''import {{ describe, it, expect, beforeEach, vi }} from 'vitest';
import {{ Request, Response }} from 'express';
import {{ {controller_name} }} from '../controllers/{model_lower}.controller';

describe('{controller_name}', () => {{
  let controller: {controller_name};
  let mockService: any;
  let mockReq: Partial<Request>;
  let mockRes: Partial<Response>;
  let mockNext: ReturnType<typeof vi.fn>;

  beforeEach(() => {{
    mockService = {{
      getById: vi.fn(),
      getAll: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    }};

    controller = new {controller_name}(mockService);

    mockReq = {{
      params: {{}},
      query: {{}},
      body: {{}},
    }};

    mockRes = {{
      status: vi.fn().mockReturnThis(),
      json: vi.fn().mockReturnThis(),
      send: vi.fn().mockReturnThis(),
    }};

    mockNext = vi.fn();
  }});

  describe('getAll', () => {{
    it('should return list of items', async () => {{
      const mockData = {{
        data: [{{ id: '1' }}, {{ id: '2' }}],
        total: 2,
        page: 1,
        limit: 20,
      }};
      mockService.getAll.mockResolvedValue(mockData);

      await controller.getAll(
        mockReq as Request,
        mockRes as Response,
        mockNext
      );

      expect(mockRes.json).toHaveBeenCalledWith(expect.objectContaining({{
        success: true,
        data: mockData.data,
      }}));
    }});
  }});

  describe('getById', () => {{
    it('should return item by id', async () => {{
      const mockItem = {{ id: '1' }};
      mockReq.params = {{ id: '1' }};
      mockService.getById.mockResolvedValue(mockItem);

      await controller.getById(
        mockReq as Request,
        mockRes as Response,
        mockNext
      );

      expect(mockRes.json).toHaveBeenCalledWith(expect.objectContaining({{
        success: true,
        data: mockItem,
      }}));
    }});

    it('should return 404 when not found', async () => {{
      mockReq.params = {{ id: '999' }};
      const error = new Error('{model_name} not found');
      (error as any).name = '{model_name}NotFoundError';
      mockService.getById.mockRejectedValue(error);

      await controller.getById(
        mockReq as Request,
        mockRes as Response,
        mockNext
      );

      expect(mockRes.status).toHaveBeenCalledWith(404);
    }});
  }});

  describe('create', () => {{
    it('should create and return item', async () => {{
      const input = {{ name: 'test' }};
      const created = {{ id: '1', ...input }};
      mockReq.body = input;
      mockService.create.mockResolvedValue(created);

      await controller.create(
        mockReq as Request,
        mockRes as Response,
        mockNext
      );

      expect(mockRes.status).toHaveBeenCalledWith(201);
      expect(mockRes.json).toHaveBeenCalledWith(expect.objectContaining({{
        success: true,
        data: created,
      }}));
    }});
  }});

  describe('update', () => {{
    it('should update and return item', async () => {{
      const input = {{ name: 'updated' }};
      const updated = {{ id: '1', ...input }};
      mockReq.params = {{ id: '1' }};
      mockReq.body = input;
      mockService.update.mockResolvedValue(updated);

      await controller.update(
        mockReq as Request,
        mockRes as Response,
        mockNext
      );

      expect(mockRes.json).toHaveBeenCalledWith(expect.objectContaining({{
        success: true,
        data: updated,
      }}));
    }});
  }});

  describe('delete', () => {{
    it('should delete item', async () => {{
      mockReq.params = {{ id: '1' }};
      mockService.delete.mockResolvedValue(undefined);

      await controller.delete(
        mockReq as Request,
        mockRes as Response,
        mockNext
      );

      expect(mockRes.status).toHaveBeenCalledWith(204);
    }});
  }});
}});
'''

    def generate_e2e_tests(self, model: InferredModel) -> str:
        """Generate E2E tests."""
        model_name = model.name
        model_lower = model_name[0].lower() + model_name[1:]
        model_plural = model_lower + 's'

        return f'''import {{ describe, it, expect, beforeAll, afterAll }} from 'vitest';
import request from 'supertest';
import {{ app }} from '../index';
import {{ PrismaClient }} from '@prisma/client';

const prisma = new PrismaClient();

describe('{model_name} API E2E', () => {{
  let created{model_name}Id: string;

  beforeAll(async () => {{
    // Setup test database
    await prisma.$connect();
  }});

  afterAll(async () => {{
    // Cleanup
    await prisma.{model_lower}.deleteMany({{
      where: {{ id: created{model_name}Id }},
    }});
    await prisma.$disconnect();
  }});

  describe('POST /api/{model_plural}', () => {{
    it('should create a new {model_lower}', async () => {{
      const response = await request(app)
        .post('/api/{model_plural}')
        .send({{
          // Add required fields
        }})
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data.id).toBeDefined();
      created{model_name}Id = response.body.data.id;
    }});

    it('should return 400 for invalid data', async () => {{
      const response = await request(app)
        .post('/api/{model_plural}')
        .send({{}})
        .expect(400);

      expect(response.body.success).toBe(false);
    }});
  }});

  describe('GET /api/{model_plural}', () => {{
    it('should return list of {model_plural}', async () => {{
      const response = await request(app)
        .get('/api/{model_plural}')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(Array.isArray(response.body.data)).toBe(true);
    }});

    it('should support pagination', async () => {{
      const response = await request(app)
        .get('/api/{model_plural}?page=1&limit=10')
        .expect(200);

      expect(response.body.meta).toBeDefined();
      expect(response.body.meta.page).toBe(1);
    }});
  }});

  describe('GET /api/{model_plural}/:id', () => {{
    it('should return {model_lower} by id', async () => {{
      const response = await request(app)
        .get(`/api/{model_plural}/${{created{model_name}Id}}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.id).toBe(created{model_name}Id);
    }});

    it('should return 404 for non-existent id', async () => {{
      const response = await request(app)
        .get('/api/{model_plural}/non-existent-id')
        .expect(404);

      expect(response.body.success).toBe(false);
    }});
  }});

  describe('PUT /api/{model_plural}/:id', () => {{
    it('should update {model_lower}', async () => {{
      const response = await request(app)
        .put(`/api/{model_plural}/${{created{model_name}Id}}`)
        .send({{
          // Add fields to update
        }})
        .expect(200);

      expect(response.body.success).toBe(true);
    }});
  }});

  describe('DELETE /api/{model_plural}/:id', () => {{
    it('should delete {model_lower}', async () => {{
      await request(app)
        .delete(`/api/{model_plural}/${{created{model_name}Id}}`)
        .expect(204);

      // Verify deleted
      await request(app)
        .get(`/api/{model_plural}/${{created{model_name}Id}}`)
        .expect(404);
    }});
  }});
}});
'''

    def generate_test_setup(self) -> str:
        """Generate test setup file."""
        return '''import { beforeAll, afterAll } from 'vitest';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

beforeAll(async () => {
  // Connect to test database
  await prisma.$connect();
});

afterAll(async () => {
  // Disconnect
  await prisma.$disconnect();
});

export { prisma };
'''

    def generate_vitest_config(self) -> str:
        """Generate Vitest configuration."""
        return '''import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.d.ts',
        'tests/',
      ],
    },
    include: ['tests/**/*.test.ts', 'src/**/*.test.ts'],
    testTimeout: 10000,
  },
});
'''