# generation/prompts/database/__init__.py
"""
Database Prompts - Multi-framework ORM support
"""

from .indexing_prompt import INDEXING_PROMPT
from .nosql_prompt import NOSQL_PROMPT
from .schema_design_prompt import SCHEMA_DESIGN_PROMPT
from .sharding_replication_prompt import SHARDING_REPLICATION_PROMPT
from .sql_prompt import SQL_PROMPT
from .transactions_prompt import TRANSACTIONS_PROMPT

# ORM-specific prompts for each framework
from .orm_sqlalchemy_prompt import ORM_SQLALCHEMY_PROMPT
from .orm_prisma_prompt import ORM_PRISMA_PROMPT
from .orm_typeorm_prompt import ORM_TYPEORM_PROMPT
from .orm_drizzle_prompt import ORM_DRIZZLE_PROMPT
from .orm_gorm_prompt import ORM_GORM_PROMPT
from .orm_efcore_prompt import ORM_EFCORE_PROMPT
from .orm_django_prompt import ORM_DJANGO_PROMPT
from .orm_hibernate_prompt import ORM_HIBERNATE_PROMPT

DATABASE_PROMPTS = {
    # Core database prompts
    "sql": SQL_PROMPT,
    "nosql": NOSQL_PROMPT,
    "schema_design": SCHEMA_DESIGN_PROMPT,
    "indexing": INDEXING_PROMPT,
    "transactions": TRANSACTIONS_PROMPT,
    "sharding_replication": SHARDING_REPLICATION_PROMPT,
    
    # ORM-specific prompts (mapped by framework)
    "orm_sqlalchemy": ORM_SQLALCHEMY_PROMPT,   # FastAPI, Flask
    "orm_prisma": ORM_PRISMA_PROMPT,           # Next.js, Express
    "orm_typeorm": ORM_TYPEORM_PROMPT,         # NestJS, Express
    "orm_drizzle": ORM_DRIZZLE_PROMPT,         # Modern TypeScript
    "orm_gorm": ORM_GORM_PROMPT,               # Gin, Fiber, Echo
    "orm_efcore": ORM_EFCORE_PROMPT,           # ASP.NET Core
    "orm_django": ORM_DJANGO_PROMPT,           # Django
    "orm_hibernate": ORM_HIBERNATE_PROMPT,     # Spring Boot
}

# Framework to ORM mapping
FRAMEWORK_ORM_MAP = {
    "fastapi": "orm_sqlalchemy",
    "flask": "orm_sqlalchemy",
    "django": "orm_django",
    "express": "orm_prisma",
    "nestjs": "orm_typeorm",
    "nextjs": "orm_prisma",
    "spring": "orm_hibernate",
    "springboot": "orm_hibernate",
    "dotnet": "orm_efcore",
    "aspnet": "orm_efcore",
    "gin": "orm_gorm",
    "fiber": "orm_gorm",
    "echo": "orm_gorm",
}

__all__ = [
    "DATABASE_PROMPTS",
    "FRAMEWORK_ORM_MAP",
    "SQL_PROMPT",
    "NOSQL_PROMPT",
    "SCHEMA_DESIGN_PROMPT",
    "INDEXING_PROMPT",
    "TRANSACTIONS_PROMPT",
    "SHARDING_REPLICATION_PROMPT",
    "ORM_SQLALCHEMY_PROMPT",
    "ORM_PRISMA_PROMPT",
    "ORM_TYPEORM_PROMPT",
    "ORM_DRIZZLE_PROMPT",
    "ORM_GORM_PROMPT",
    "ORM_EFCORE_PROMPT",
    "ORM_DJANGO_PROMPT",
    "ORM_HIBERNATE_PROMPT",
]


