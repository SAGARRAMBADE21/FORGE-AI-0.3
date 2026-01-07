"""Template configuration for code generation."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class BackendFramework(str, Enum):
    """Supported backend frameworks."""
    EXPRESS = "express"      # TypeScript/Node.js
    NESTJS = "nestjs"        # TypeScript/Node.js
    FASTAPI = "fastapi"      # Python
    DJANGO = "django"        # Python
    FLASK = "flask"          # Python
    GIN = "gin"              # Go
    SPRING = "spring"        # Java
    DOTNET = "dotnet"        # C#


class DatabaseType(str, Enum):
    """Supported databases."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"


class ORMType(str, Enum):
    """Supported ORMs."""
    PRISMA = "prisma"
    TYPEORM = "typeorm"
    SQLALCHEMY = "sqlalchemy"
    DRIZZLE = "drizzle"


@dataclass
class TemplateConfig:
    """Template configuration."""
    framework: BackendFramework = BackendFramework.EXPRESS
    database: DatabaseType = DatabaseType.POSTGRESQL
    orm: ORMType = ORMType.PRISMA
    language: str = "typescript"
    output_dir: str = "backend"
    
    # Feature flags
    use_docker: bool = True
    use_testing: bool = True
    use_swagger: bool = True
    use_validation: bool = True
    use_logging: bool = True
    
    # Code style
    indent: int = 2
    quotes: str = "single"
    semicolons: bool = True
    
    # Paths
    src_dir: str = "src"
    models_dir: str = "models"
    controllers_dir: str = "controllers"
    services_dir: str = "services"
    repositories_dir: str = "repositories"
    middleware_dir: str = "middleware"
    routes_dir: str = "routes"
    tests_dir: str = "tests"
    config_dir: str = "config"
    
    def __post_init__(self):
        """Auto-detect language from framework if not explicitly set."""
        # Framework to language mapping
        framework_language_map = {
            BackendFramework.EXPRESS: "typescript",
            BackendFramework.NESTJS: "typescript",
            BackendFramework.FASTAPI: "python",
            BackendFramework.DJANGO: "python",
            BackendFramework.FLASK: "python",
            BackendFramework.GIN: "go",
            BackendFramework.SPRING: "java",
            BackendFramework.DOTNET: "csharp",
        }
        
        # Auto-detect language from framework
        if self.framework in framework_language_map:
            self.language = framework_language_map[self.framework]


# Default template mappings
PRISMA_TYPE_MAP = {
    "string": "String",
    "text": "String",
    "integer": "Int",
    "float": "Float",
    "decimal": "Decimal",
    "boolean": "Boolean",
    "datetime": "DateTime",
    "date": "DateTime",
    "json": "Json",
    "uuid": "String",
}

TYPESCRIPT_TYPE_MAP = {
    "string": "string",
    "text": "string",
    "integer": "number",
    "float": "number",
    "decimal": "number",
    "boolean": "boolean",
    "datetime": "Date",
    "date": "Date",
    "json": "Record<string, any>",
    "uuid": "string",
}

PYTHON_TYPE_MAP = {
    "string": "str",
    "text": "str",
    "integer": "int",
    "float": "float",
    "decimal": "Decimal",
    "boolean": "bool",
    "datetime": "datetime",
    "date": "date",
    "json": "dict",
    "uuid": "UUID",
}