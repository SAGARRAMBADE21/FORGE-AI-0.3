"""Template engine for code generation."""

import re
import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.templates_config import (
    TemplateConfig, PRISMA_TYPE_MAP, TYPESCRIPT_TYPE_MAP, PYTHON_TYPE_MAP
)

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Jinja2-based template engine with code-specific helpers.
    """

    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = templates_dir or Path(__file__).parent / "templates"
        
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Register custom filters
        self._register_filters()
        
        # Register custom globals
        self._register_globals()

    def _register_filters(self):
        """Register custom Jinja filters."""
        self._env.filters['camelCase'] = self._to_camel_case
        self._env.filters['PascalCase'] = self._to_pascal_case
        self._env.filters['snake_case'] = self._to_snake_case
        self._env.filters['SCREAMING_SNAKE'] = self._to_screaming_snake
        self._env.filters['kebab_case'] = self._to_kebab_case
        self._env.filters['pluralize'] = self._pluralize
        self._env.filters['singularize'] = self._singularize
        self._env.filters['prismaType'] = self._to_prisma_type
        self._env.filters['tsType'] = self._to_typescript_type
        self._env.filters['pyType'] = self._to_python_type
        self._env.filters['quote'] = self._quote
        self._env.filters['indent'] = self._indent
        self._env.filters['ljust'] = lambda s, width: str(s).ljust(width)
        self._env.filters['lower'] = lambda s: str(s).lower()
        self._env.filters['upper'] = lambda s: str(s).upper()

    def _register_globals(self):
        """Register global variables and functions."""
        self._env.globals['now'] = self._get_timestamp
        self._env.globals['range'] = range
        self._env.globals['enumerate'] = enumerate

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with context."""
        try:
            template = self._env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            # Try built-in template if file not found
            if template_name in BUILTIN_TEMPLATES:
                logger.debug(f"Using built-in template: {template_name}")
                return self.render_string(BUILTIN_TEMPLATES[template_name], context)
            logger.error(f"Template render error ({template_name}): {e}")
            raise

    def render_string(self, template_str: str, context: dict[str, Any]) -> str:
        """Render a template string with context."""
        try:
            template = self._env.from_string(template_str)
            return template.render(**context)
        except Exception as e:
            logger.error(f"String template render error: {e}")
            raise

    # Filters
    @staticmethod
    def _to_camel_case(s: str) -> str:
        """Convert to camelCase."""
        parts = re.split(r'[-_\s]+', s)
        return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])

    @staticmethod
    def _to_pascal_case(s: str) -> str:
        """Convert to PascalCase."""
        parts = re.split(r'[-_\s]+', s)
        return ''.join(p.capitalize() for p in parts)

    @staticmethod
    def _to_snake_case(s: str) -> str:
        """Convert to snake_case."""
        s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)
        s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
        return s.replace('-', '_').replace(' ', '_').lower()

    @staticmethod
    def _to_screaming_snake(s: str) -> str:
        """Convert to SCREAMING_SNAKE_CASE."""
        return TemplateEngine._to_snake_case(s).upper()

    @staticmethod
    def _to_kebab_case(s: str) -> str:
        """Convert to kebab-case."""
        return TemplateEngine._to_snake_case(s).replace('_', '-')

    @staticmethod
    def _pluralize(s: str) -> str:
        """Simple pluralization."""
        if s.endswith('y'):
            return s[:-1] + 'ies'
        if s.endswith(('s', 'x', 'z', 'ch', 'sh')):
            return s + 'es'
        return s + 's'

    @staticmethod
    def _singularize(s: str) -> str:
        """Simple singularization."""
        if s.endswith('ies'):
            return s[:-3] + 'y'
        if s.endswith('es') and len(s) > 3:
            if s[:-2].endswith(('s', 'x', 'z', 'ch', 'sh')):
                return s[:-2]
        if s.endswith('s') and not s.endswith('ss'):
            return s[:-1]
        return s

    @staticmethod
    def _to_prisma_type(field_type: str) -> str:
        """Convert field type to Prisma type."""
        return PRISMA_TYPE_MAP.get(field_type, 'String')

    @staticmethod
    def _to_typescript_type(field_type: str) -> str:
        """Convert field type to TypeScript type."""
        return TYPESCRIPT_TYPE_MAP.get(field_type, 'any')

    @staticmethod
    def _to_python_type(field_type: str) -> str:
        """Convert field type to Python type."""
        return PYTHON_TYPE_MAP.get(field_type, 'Any')

    @staticmethod
    def _quote(s: str, quote_char: str = "'") -> str:
        """Quote a string."""
        return f"{quote_char}{s}{quote_char}"

    @staticmethod
    def _indent(s: str, width: int = 2, first: bool = False) -> str:
        """Indent text."""
        indent_str = ' ' * width
        lines = s.split('\n')
        if first:
            return '\n'.join(indent_str + line for line in lines)
        return lines[0] + '\n' + '\n'.join(indent_str + line for line in lines[1:])

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# Built-in templates as strings (for when template files don't exist)
BUILTIN_TEMPLATES = {
    'prisma/schema.prisma.j2': '''
// This is your Prisma schema file
// Generated by FORGE code generation

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

{% for enum_name, enum_values in enums.items() %}
enum {{ enum_name }} {
  {% for value in enum_values %}
  {{ value }}
  {% endfor %}
}

{% endfor %}
{% for model in models %}
model {{ model.name }} {
  {% for field in model.fields %}
  {{ field.name | ljust(20) }} {{ field.field_type | prismaType }}{% if field.array %}[]{% endif %}{% if field.nullable %}?{% endif %}{% if field.unique %} @unique{% endif %}{% if field.name == 'id' %} @id @default(uuid()){% endif %}{% if field.name in ['createdAt', 'updatedAt'] %} @default(now()){% endif %}
  {% endfor %}
  {% for rel in relations if rel.source_model == model.name %}
  {{ rel.target_model | camelCase }} {{ rel.target_model }}{% if rel.type == 'one_to_many' %}[]{% endif %}{% if rel.field %} @relation(fields: [{{ rel.field }}], references: [id]){% endif %}
  {% endfor %}
}

{% endfor %}
''',

    'typescript/types.ts.j2': '''
// Generated types for {{ model.name }}

export interface {{ model.name }} {
  {% for field in model.fields %}
  {{ field.name }}: {{ field.field_type | tsType }}{% if field.array %}[]{% endif %}{% if field.nullable %} | null{% endif %};
  {% endfor %}
}

export interface Create{{ model.name }}Input {
  {% for field in model.fields if field.name not in ['id', 'createdAt', 'updatedAt'] %}
  {{ field.name }}{% if field.nullable %}?{% endif %}: {{ field.field_type | tsType }}{% if field.array %}[]{% endif %};
  {% endfor %}
}

export interface Update{{ model.name }}Input {
  {% for field in model.fields if field.name not in ['id', 'createdAt', 'updatedAt'] %}
  {{ field.name }}?: {{ field.field_type | tsType }}{% if field.array %}[]{% endif %};
  {% endfor %}
}
''',

    'prisma/model.prisma.j2': '''
model {{ model.name }} {
  {% for field in model.fields %}
  {{ field.name | ljust(20) }} {{ field.field_type | prismaType }}{% if field.nullable %}?{% endif %}{% if field.unique %} @unique{% endif %}{% if field.name == 'id' %} @id @default(uuid()){% endif %}{% if field.name in ['createdAt', 'updatedAt'] %} @default(now()){% endif %}
  {% endfor %}
  {% for rel in relations if rel.source_model == model.name %}
  {{ rel.source_field | ljust(20) }} {{ rel.target_model }}{% if rel.relation_type.value == 'one_to_many' %}[]{% endif %} @relation(fields: [{{ rel.source_field }}Id], references: [id])
  {% endfor %}
}
''',

    'typescript/repository.ts.j2': '''
import { PrismaClient, {{ model.name }} } from '@prisma/client';

export interface Create{{ model.name }}Input {
  {% for field in model.fields if field.name not in ['id', 'createdAt', 'updatedAt'] %}
  {{ field.name }}{% if field.nullable %}?{% endif %}: {{ field.field_type | tsType }};
  {% endfor %}
}

export interface Update{{ model.name }}Input {
  {% for field in model.fields if field.name not in ['id', 'createdAt', 'updatedAt'] %}
  {{ field.name }}?: {{ field.field_type | tsType }};
  {% endfor %}
}

export class {{ model.name }}Repository {
  constructor(private prisma: PrismaClient) {}

  async findById(id: string): Promise<{{ model.name }} | null> {
    return this.prisma.{{ model.name | camelCase }}.findUnique({ where: { id } });
  }

  async findMany(where?: Partial<{{ model.name }}>): Promise<{{ model.name }}[]> {
    return this.prisma.{{ model.name | camelCase }}.findMany({ where });
  }

  async create(data: Create{{ model.name }}Input): Promise<{{ model.name }}> {
    return this.prisma.{{ model.name | camelCase }}.create({ data });
  }

  async update(id: string, data: Update{{ model.name }}Input): Promise<{{ model.name }}> {
    return this.prisma.{{ model.name | camelCase }}.update({ where: { id }, data });
  }

  async delete(id: string): Promise<void> {
    await this.prisma.{{ model.name | camelCase }}.delete({ where: { id } });
  }

  async count(where?: Partial<{{ model.name }}>): Promise<number> {
    return this.prisma.{{ model.name | camelCase }}.count({ where });
  }
}
''',

    'typescript/service.ts.j2': '''
import { {{ model.name }}, Prisma } from '@prisma/client';
import { {{ model.name }}Repository, Create{{ model.name }}Input, Update{{ model.name }}Input } from '../repositories/{{ model.name | camelCase }}.repository';

export class {{ model.name }}Service {
  constructor(private repository: {{ model.name }}Repository) {}

  async getById(id: string): Promise<{{ model.name }}> {
    const item = await this.repository.findById(id);
    if (!item) {
      throw new Error('{{ model.name }} not found');
    }
    return item;
  }

  async getAll(filter?: Partial<{{ model.name }}>): Promise<{{ model.name }}[]> {
    return this.repository.findMany(filter);
  }

  async create(data: Create{{ model.name }}Input): Promise<{{ model.name }}> {
    // Add business logic here
    return this.repository.create(data);
  }

  async update(id: string, data: Update{{ model.name }}Input): Promise<{{ model.name }}> {
    await this.getById(id); // Ensure exists
    // Add business logic here
    return this.repository.update(id, data);
  }

  async delete(id: string): Promise<void> {
    await this.getById(id); // Ensure exists
    // Add business logic here
    await this.repository.delete(id);
  }
}
''',

    'typescript/controller.ts.j2': '''
import { Request, Response, NextFunction } from 'express';
import { {{ model.name }}Service } from '../services/{{ model.name | camelCase }}.service';

export class {{ model.name }}Controller {
  constructor(private service: {{ model.name }}Service) {}

  getAll = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const items = await this.service.getAll(req.query);
      res.json(items);
    } catch (error) {
      next(error);
    }
  };

  getById = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const item = await this.service.getById(req.params.id);
      res.json(item);
    } catch (error) {
      next(error);
    }
  };

  create = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const item = await this.service.create(req.body);
      res.status(201).json(item);
    } catch (error) {
      next(error);
    }
  };

  update = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const item = await this.service.update(req.params.id, req.body);
      res.json(item);
    } catch (error) {
      next(error);
    }
  };

  delete = async (req: Request, res: Response, next: NextFunction) => {
    try {
      await this.service.delete(req.params.id);
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  };
}
''',

    'typescript/routes.ts.j2': '''
import { Router } from 'express';
{% for resource in resources %}
import { {{ resource.name | PascalCase }}Controller } from '../controllers/{{ resource.name | camelCase }}.controller';
{% endfor %}
import { authenticate } from '../middleware/auth';
import { validate } from '../middleware/validate';

export function createRoutes(
  {% for resource in resources %}
  {{ resource.name | camelCase }}Controller: {{ resource.name | PascalCase }}Controller,
  {% endfor %}
): Router {
  const router = Router();

  {% for resource in resources %}
  // {{ resource.name | PascalCase }} routes
  {% for endpoint in resource.endpoints %}
  router.{{ endpoint.method | lower }}(
    '{{ endpoint.path }}',
    {% if endpoint.requires_auth %}authenticate,{% endif %}
    {% if endpoint.validation_schema %}validate({{ endpoint.validation_schema }}),{% endif %}
    {{ resource.name | camelCase }}Controller.{{ endpoint.handler }}
  );
  {% endfor %}

  {% endfor %}
  return router;
}
''',

    'typescript/auth.middleware.ts.j2': '''
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

export interface AuthRequest extends Request {
  user?: any;
}

export const authenticate = async (req: AuthRequest, res: Response, next: NextFunction) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};
''',

    'typescript/auth.service.ts.j2': '''
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { PrismaClient } from '@prisma/client';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

export class AuthService {
  constructor(private prisma: PrismaClient) {}

  async register(email: string, password: string, name: string) {
    const hashedPassword = await bcrypt.hash(password, 10);
    
    const user = await this.prisma.user.create({
      data: {
        email,
        password: hashedPassword,
        name,
      },
    });

    const token = this.generateToken(user.id, user.email);
    return { user: this.sanitizeUser(user), token };
  }

  async login(email: string, password: string) {
    const user = await this.prisma.user.findUnique({ where: { email } });
    
    if (!user) {
      throw new Error('User not found');
    }

    const valid = await bcrypt.compare(password, user.password);
    if (!valid) {
      throw new Error('Invalid password');
    }

    const token = this.generateToken(user.id, user.email);
    return { user: this.sanitizeUser(user), token };
  }

  private generateToken(userId: string, email: string): string {
    return jwt.sign({ userId, email }, JWT_SECRET, { expiresIn: '7d' });
  }

  private sanitizeUser(user: any) {
    const { password, ...sanitized } = user;
    return sanitized;
  }
}
''',

    'typescript/auth.controller.ts.j2': '''
import { Request, Response, NextFunction } from 'express';
import { AuthService } from '../services/auth.service';

export class AuthController {
  constructor(private authService: AuthService) {}

  register = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { email, password, name } = req.body;
      const result = await this.authService.register(email, password, name);
      res.status(201).json(result);
    } catch (error) {
      next(error);
    }
  };

  login = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { email, password } = req.body;
      const result = await this.authService.login(email, password);
      res.json(result);
    } catch (error) {
      next(error);
    }
  };
}
''',
}