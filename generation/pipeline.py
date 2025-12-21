"""Code generation pipeline."""

import logging
import asyncio
from pathlib import Path
from dataclasses import dataclass

from core.types import (
    InferredModel, InferredRelation, ApiResourceContract,
    AuthRequirements, DatabaseSchema, GeneratedFile, GenerationResult,
    BackendArchitecture
)
from core.utils import generate_id
from config.templates_config import TemplateConfig
from generation.template_engine import TemplateEngine, BUILTIN_TEMPLATES
from generation.llm_generator import LLMCodeGenerator
from synthesis.api_architect import ApiArchitecture
from synthesis.service_architect import ServiceArchitecture
from synthesis.auth_planner import AuthPlan

logger = logging.getLogger(__name__)


@dataclass
class GenerationContext:
    """Context for code generation."""
    models: list[InferredModel]
    relations: list[InferredRelation]
    api_resources: list[ApiResourceContract]
    api_architecture: ApiArchitecture
    service_architecture: ServiceArchitecture
    auth_requirements: AuthRequirements
    auth_plan: AuthPlan
    schema: DatabaseSchema
    config: TemplateConfig


class CodeGenerationPipeline:
    """
    Multi-stage code generation pipeline.
    
    Stages:
    1. Prisma schema
    2. Types/interfaces
    3. Repositories
    4. Services
    5. Controllers
    6. Routes
    7. Middleware
    8. Tests
    9. Config files
    10. Docker
    """

    def __init__(self, config: TemplateConfig | None = None):
        self.config = config or TemplateConfig()
        self._template_engine = TemplateEngine()
        self._llm_generator = LLMCodeGenerator()
        self._generated_files: list[GeneratedFile] = []

    async def generate(self, context: GenerationContext) -> GenerationResult:
        """Run the full generation pipeline."""
        self._generated_files = []
        errors = []
        warnings = []

        try:
            # Stage 1: Prisma schema
            logger.info("Stage 1: Generating Prisma schema...")
            await self._generate_prisma_schema(context)

            # Stage 2: Types
            logger.info("Stage 2: Generating types...")
            await self._generate_types(context)

            # Stage 3: Repositories
            logger.info("Stage 3: Generating repositories...")
            await self._generate_repositories(context)

            # Stage 4: Services
            logger.info("Stage 4: Generating services...")
            await self._generate_services(context)

            # Stage 5: Controllers
            logger.info("Stage 5: Generating controllers...")
            await self._generate_controllers(context)

            # Stage 6: Routes
            logger.info("Stage 6: Generating routes...")
            await self._generate_routes(context)

            # Stage 7: Middleware
            logger.info("Stage 7: Generating middleware...")
            await self._generate_middleware(context)

            # Stage 8: Auth
            logger.info("Stage 8: Generating auth...")
            await self._generate_auth(context)

            # Stage 9: Tests
            if self.config.use_testing:
                logger.info("Stage 9: Generating tests...")
                await self._generate_tests(context)

            # Stage 10: Config
            logger.info("Stage 10: Generating config files...")
            await self._generate_config(context)

            # Stage 11: Docker
            if self.config.use_docker:
                logger.info("Stage 11: Generating Docker files...")
                await self._generate_docker(context)

            # Stage 12: Main entry point
            logger.info("Stage 12: Generating main entry...")
            await self._generate_main(context)

        except Exception as e:
            logger.error(f"Generation error: {e}")
            errors.append(str(e))

        return GenerationResult(
            success=len(errors) == 0,
            files=self._generated_files,
            errors=errors,
            warnings=warnings,
            stats={
                'total_files': len(self._generated_files),
                'models': len(context.models),
                'endpoints': sum(len(r.endpoints) for r in context.api_resources),
            }
        )

    async def _generate_prisma_schema(self, ctx: GenerationContext):
        """Generate Prisma schema."""
        content = self._render_template('prisma/schema.prisma.j2', {
            'models': ctx.models,
            'relations': ctx.relations,
            'enums': ctx.schema.enums if ctx.schema else {},
        })

        self._add_file(
            'prisma/schema.prisma',
            content,
            'prisma',
            'prisma_generator'
        )

    async def _generate_types(self, ctx: GenerationContext):
        """Generate TypeScript types."""
        # Filter out Create/Update input types - they'll be generated from the template
        actual_models = [
            m for m in ctx.models 
            if not (m.name.startswith('Create') or m.name.startswith('Update'))
        ]
        
        for model in actual_models:
            content = self._render_template('typescript/types.ts.j2', {
                'model': model,
            })
            
            self._add_file(
                f'{self.config.src_dir}/types/{model.name.lower()}.types.ts',
                content,
                'typescript',
                'types_generator'
            )

        # Index file
        exports = '\n'.join(
            f"export * from './{m.name.lower()}.types';"
            for m in actual_models
        )
        self._add_file(
            f'{self.config.src_dir}/types/index.ts',
            exports,
            'typescript',
            'types_generator'
        )

    async def _generate_repositories(self, ctx: GenerationContext):
        """Generate repository layer."""
        # Filter out Create/Update input types
        actual_models = [
            m for m in ctx.models 
            if not (m.name.startswith('Create') or m.name.startswith('Update'))
        ]
        
        for model in actual_models:
            # Find repository definition
            repo_def = next(
                (r for r in ctx.service_architecture.repositories if r.model == model.name),
                None
            )

            content = self._render_template('typescript/repository.ts.j2', {
                'model': model,
                'repository': repo_def,
                'relations': [r for r in ctx.relations if r.source_model == model.name],
            })

            self._add_file(
                f'{self.config.src_dir}/{self.config.repositories_dir}/{model.name.lower()}.repository.ts',
                content,
                'typescript',
                'repository_generator'
            )

        # Index file
        exports = '\n'.join(
            f"export * from './{m.name.lower()}.repository';"
            for m in actual_models
        )
        self._add_file(
            f'{self.config.src_dir}/{self.config.repositories_dir}/index.ts',
            exports,
            'typescript',
            'repository_generator'
        )

    async def _generate_services(self, ctx: GenerationContext):
        """Generate service layer."""
        for service in ctx.service_architecture.services:
            model = next(
                (m for m in ctx.models if m.name.lower() in service.name.lower()),
                None
            )

            # Skip if model not found
            if not model:
                logger.warning(f"No model found for service {service.name}, skipping")
                continue

            content = self._render_template('typescript/service.ts.j2', {
                'service': service,
                'model': model,
            })

            service_name = service.name.replace('Service', '').lower()
            self._add_file(
                f'{self.config.src_dir}/{self.config.services_dir}/{service_name}.service.ts',
                content,
                'typescript',
                'service_generator'
            )

        # Index file (only if we have services)
        export_list = [
            f"export * from './{s.name.replace('Service', '').lower()}.service';"
            for s in ctx.service_architecture.services
            if any(m.name.lower() in s.name.lower() for m in ctx.models)
        ]
        if export_list:
            exports = '\n'.join(export_list)
            self._add_file(
                f'{self.config.src_dir}/{self.config.services_dir}/index.ts',
                exports,
                'typescript',
                'service_generator'
            )

    async def _generate_controllers(self, ctx: GenerationContext):
        """Generate controllers."""
        for controller in ctx.api_architecture.controllers:
            model = next(
                (m for m in ctx.models if m.name.lower() == controller.resource.lower()),
                None
            )

            # Skip if model not found
            if not model:
                logger.warning(f"No model found for controller {controller.name}, skipping")
                continue

            content = self._render_template('typescript/controller.ts.j2', {
                'controller': controller,
                'model': model,
            })

            ctrl_name = controller.name.replace('Controller', '').lower()
            self._add_file(
                f'{self.config.src_dir}/{self.config.controllers_dir}/{ctrl_name}.controller.ts',
                content,
                'typescript',
                'controller_generator'
            )

        # Index file (only if we have controllers)
        export_list = [
            f"export * from './{c.name.replace('Controller', '').lower()}.controller';"
            for c in ctx.api_architecture.controllers
            if any(m.name.lower() == c.resource.lower() for m in ctx.models)
        ]
        if export_list:
            exports = '\n'.join(export_list)
            self._add_file(
                f'{self.config.src_dir}/{self.config.controllers_dir}/index.ts',
                exports,
                'typescript',
                'controller_generator'
            )

    async def _generate_routes(self, ctx: GenerationContext):
        """Generate routes."""
        content = self._render_template('typescript/routes.ts.j2', {
            'resources': ctx.api_resources,
            'routes': ctx.api_architecture.routes,
            'controllers': ctx.api_architecture.controllers,
        })

        self._add_file(
            f'{self.config.src_dir}/{self.config.routes_dir}/index.ts',
            content,
            'typescript',
            'route_generator'
        )

    async def _generate_middleware(self, ctx: GenerationContext):
        """Generate middleware."""
        # Error handler
        error_handler = '''
import { Request, Response, NextFunction } from 'express';

export interface AppError extends Error {
  statusCode?: number;
  code?: string;
}

export const errorHandler = (
  err: AppError,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const statusCode = err.statusCode || 500;
  
  res.status(statusCode).json({
    success: false,
    error: {
      message: err.message,
      code: err.code || 'INTERNAL_ERROR',
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
    },
  });
};
'''
        self._add_file(
            f'{self.config.src_dir}/{self.config.middleware_dir}/errorHandler.ts',
            error_handler,
            'typescript',
            'middleware_generator'
        )

        # Validation middleware
        validation = '''
import { Request, Response, NextFunction } from 'express';
import { ZodSchema } from 'zod';

export const validate = (schema: ZodSchema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      schema.parse({
        body: req.body,
        query: req.query,
        params: req.params,
      });
      next();
    } catch (error) {
      res.status(400).json({
        success: false,
        error: { message: 'Validation failed', details: error },
      });
    }
  };
};
'''
        self._add_file(
            f'{self.config.src_dir}/{self.config.middleware_dir}/validate.ts',
            validation,
            'typescript',
            'middleware_generator'
        )

        # Request logger
        logger_middleware = '''
import { Request, Response, NextFunction } from 'express';

export const requestLogger = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.path} ${res.statusCode} ${duration}ms`);
  });
  
  next();
};
'''
        self._add_file(
            f'{self.config.src_dir}/{self.config.middleware_dir}/logger.ts',
            logger_middleware,
            'typescript',
            'middleware_generator'
        )

        # Index
        exports = '''
export * from './errorHandler';
export * from './validate';
export * from './logger';
export * from './auth';
'''
        self._add_file(
            f'{self.config.src_dir}/{self.config.middleware_dir}/index.ts',
            exports,
            'typescript',
            'middleware_generator'
        )

    async def _generate_auth(self, ctx: GenerationContext):
        """Generate auth implementation."""
        auth_middleware = self._render_template('typescript/auth.middleware.ts.j2', {
            'auth': ctx.auth_requirements,
            'plan': ctx.auth_plan,
        })

        self._add_file(
            f'{self.config.src_dir}/{self.config.middleware_dir}/auth.ts',
            auth_middleware,
            'typescript',
            'auth_generator'
        )

        # Auth service
        auth_service = self._render_template('typescript/auth.service.ts.j2', {
            'auth': ctx.auth_requirements,
            'plan': ctx.auth_plan,
        })

        self._add_file(
            f'{self.config.src_dir}/{self.config.services_dir}/auth.service.ts',
            auth_service,
            'typescript',
            'auth_generator'
        )

        # Auth controller
        auth_controller = self._render_template('typescript/auth.controller.ts.j2', {
            'auth': ctx.auth_requirements,
            'plan': ctx.auth_plan,
        })

        self._add_file(
            f'{self.config.src_dir}/{self.config.controllers_dir}/auth.controller.ts',
            auth_controller,
            'typescript',
            'auth_generator'
        )

    async def _generate_tests(self, ctx: GenerationContext):
        """Generate tests."""
        for service in ctx.service_architecture.services:
            test_content = await self._llm_generator.generate_test(
                'service',
                service.name,
                [{'name': m.name, 'parameters': m.parameters, 'return_type': m.return_type}
                 for m in service.methods]
            )

            service_name = service.name.replace('Service', '').lower()
            self._add_file(
                f'{self.config.tests_dir}/{service_name}.service.test.ts',
                test_content,
                'typescript',
                'test_generator'
            )

    async def _generate_config(self, ctx: GenerationContext):
        """Generate configuration files."""
        # package.json
        package_json = self._render_template('config/package.json.j2', {
            'config': self.config,
            'dependencies': self._get_dependencies(ctx),
        })
        self._add_file('package.json', package_json, 'json', 'config_generator')

        # tsconfig.json
        tsconfig = '''{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}'''
        self._add_file('tsconfig.json', tsconfig, 'json', 'config_generator')

        # .env.example
        env_vars = ['DATABASE_URL=postgresql://user:pass@localhost:5432/db']
        env_vars.extend(ctx.auth_plan.env_vars)
        env_example = '\n'.join(f'{v}=' for v in env_vars)
        self._add_file('.env.example', env_example, 'env', 'config_generator')

    async def _generate_docker(self, ctx: GenerationContext):
        """Generate Docker files."""
        dockerfile = '''FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
'''
        self._add_file('Dockerfile', dockerfile, 'dockerfile', 'docker_generator')

        # docker-compose.yml
        compose = '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
'''
        self._add_file('docker-compose.yml', compose, 'yaml', 'docker_generator')

    async def _generate_main(self, ctx: GenerationContext):
        """Generate main entry point."""
        main_ts = self._render_template('typescript/main.ts.j2', {
            'config': self.config,
            'models': ctx.models,
            'services': ctx.service_architecture.services,
            'controllers': ctx.api_architecture.controllers,
        })

        self._add_file(f'{self.config.src_dir}/index.ts', main_ts, 'typescript', 'main_generator')

    def _render_template(self, template_name: str, context: dict) -> str:
        """Render a template, falling back to built-in if file not found."""
        try:
            return self._template_engine.render(template_name, context)
        except Exception:
            # Try built-in template
            if template_name in BUILTIN_TEMPLATES:
                return self._template_engine.render_string(
                    BUILTIN_TEMPLATES[template_name],
                    context
                )
            # Return placeholder
            return f"// TODO: Generate {template_name}\n// Context: {list(context.keys())}"

    def _add_file(self, path: str, content: str, file_type: str, generator: str):
        """Add a generated file."""
        self._generated_files.append(GeneratedFile(
            path=path,
            content=content,
            file_type=file_type,
            generator=generator
        ))

    def _get_dependencies(self, ctx: GenerationContext) -> dict:
        """Get npm dependencies based on context."""
        deps = {
            'express': '^4.18.0',
            '@prisma/client': '^5.0.0',
            'zod': '^3.22.0',
            'dotenv': '^16.0.0',
        }

        dev_deps = {
            'typescript': '^5.0.0',
            'prisma': '^5.0.0',
            '@types/express': '^4.17.0',
            '@types/node': '^20.0.0',
        }

        # Auth dependencies
        if ctx.auth_requirements.strategy.value == 'jwt':
            deps['jsonwebtoken'] = '^9.0.0'
            deps['bcryptjs'] = '^2.4.0'
            dev_deps['@types/jsonwebtoken'] = '^9.0.0'
            dev_deps['@types/bcryptjs'] = '^2.4.0'

        # OAuth
        if ctx.auth_requirements.oauth_providers:
            deps['passport'] = '^0.7.0'
            for provider in ctx.auth_requirements.oauth_providers:
                deps[f'passport-{provider.name}'] = 'latest'

        # Testing
        if self.config.use_testing:
            dev_deps['vitest'] = '^1.0.0'
            dev_deps['@vitest/coverage-v8'] = '^1.0.0'

        return {'dependencies': deps, 'devDependencies': dev_deps}