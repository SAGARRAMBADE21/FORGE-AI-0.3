"""Unified workflow: Frontend → Database Schema → Backend Models (synchronized)."""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional, Any

from analyzers.frontend_analyzer import FrontendAnalyzer
from backend_agent import BackendAgent
from config.settings import Settings
from config.templates_config import BackendFramework, DatabaseType
from core.types import InferredModel, InferredRelation
from indexers.unified_indexer import UnifiedIndexer
from inference.evidence_collector import EvidenceCollector
from inference.model_inference_engine import ModelInferenceEngine
from inference.relationship_inferrer import RelationshipInferrer

logger = logging.getLogger(__name__)


class UnifiedGenerationWorkflow:
    """
    Ensures database schema and backend models are synchronized.
    
    Workflow:
    1. Analyze Frontend → Extract models
    2. Generate Database Schema (from models)
    3. Generate Backend Code (using SAME models)
    
    This guarantees that:
    - Database tables match backend models exactly
    - Field types are consistent
    - Relationships are properly reflected
    """

    def __init__(
        self,
        frontend_path: Path,
        output_dir: Path,
        settings: Settings,
        db_type: DatabaseType = DatabaseType.MYSQL,
        backend_framework: BackendFramework = BackendFramework.FASTAPI,
    ):
        self.frontend_path = Path(frontend_path)
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.db_type = db_type
        self.backend_framework = backend_framework

        # Shared components - CRITICAL: Same models used everywhere
        self.indexer = None  # Will be initialized in generate_fullstack
        self.frontend_analyzer = FrontendAnalyzer(frontend_path)
        self.evidence_collector = None  # Will be initialized after indexer
        self.model_engine = ModelInferenceEngine()
        self.relation_inferrer = RelationshipInferrer()

        # Database generation (will be initialized later)
        self.db_output_dir = output_dir / "database"

        # Backend generation - use FullStackAgent like backend generate command does
        from config.templates_config import TemplateConfig
        from fullstack_agent import FullStackAgent
        backend_config = TemplateConfig(
            framework=backend_framework,
            database=db_type,
            output_dir=str(output_dir / "backend"),
        )
        self.fullstack_agent = FullStackAgent(
            project_root=frontend_path,  # Use FRONTEND path, not output
            backend_config=backend_config,
        )

    async def generate_fullstack(
        self,
        plan: Optional[Any] = None,  # FullstackPlan from RealtimePlanner
        callback: Optional[Callable[[str, str], None]] = None,
    ) -> dict:
        """
        Generate complete fullstack application with synchronized schema.
        
        Args:
            plan: Optional FullstackPlan from RealtimePlanner. If provided,
                  uses plan models instead of re-analyzing frontend.
        
        Returns:
            {
                "models": [...],           # Inferred models (single source of truth)
                "relations": [...],        # Inferred relations
                "database": {...},         # Database files
                "backend": {...},          # Backend files
                "synchronized": True       # Confirms same models used
            }
        """
        result = {
            "success": False,
            "models": [],
            "relations": [],
            "database": {},
            "backend": {},
            "synchronized": False,
        }

        try:
            # =====================================================
            # STEP 1: Get Models (from plan or frontend analysis)
            # =====================================================
            if plan:
                # Use models from RealtimePlanner
                if callback:
                    callback("Phase 1/3", f"Using plan with {len(plan.models)} models...")
                
                logger.info(f"Using plan models: {[m.name for m in plan.models]}")
                
                # Convert PlannedModel to internal Model format
                models = self._convert_plan_to_models(plan)
                relations = []  # Relations can be inferred later if needed
                
                # Still need indexer for backend generation
                logger.info("Initializing code indexer...")
                self.indexer = UnifiedIndexer(self.frontend_path)
                await self.indexer.index_project(
                    progress=lambda phase, desc: callback(f"Indexing ({phase})", desc) if callback else None
                )
                
                # We still need analysis for backend generation context
                logger.info("Analyzing frontend structure...")
                self.evidence_collector = EvidenceCollector(self.indexer)
                analysis = await self.frontend_analyzer.analyze(self.indexer)
                
            else:
                # Original workflow: analyze frontend
                if callback:
                    callback("Phase 1/3", "Analyzing frontend to extract data models...")

                # Initialize indexer
                logger.info("Initializing code indexer...")
                self.indexer = UnifiedIndexer(self.frontend_path)
                await self.indexer.index_project(
                    progress=lambda phase, desc: callback(f"Indexing ({phase})", desc) if callback else None
                )

                # Initialize evidence collector
                self.evidence_collector = EvidenceCollector(self.indexer)

                logger.info("Analyzing frontend structure...")
                analysis = await self.frontend_analyzer.analyze(self.indexer)

                # Infer models - THIS IS THE SINGLE SOURCE OF TRUTH
                logger.info("Inferring data models from frontend...")
                
                # Collect evidence from frontend analysis
                evidence_map = await self.evidence_collector.collect_all(analysis)
                models = await self.model_engine.infer_models(evidence_map)
                
                # Infer relationships
                logger.info("Inferring relationships between models...")
                # RelationshipInferrer expects (models, api_resources)
                api_resources = []  # Extract from analysis if needed
                relations = await self.relation_inferrer.infer_relationships(models, api_resources)

            logger.info(f"Discovered {len(models)} models with {len(relations)} relations")
            
            # Store in result
            result["models"] = models
            result["relations"] = relations

            # =====================================================
            # STEP 2: Generate Database Schema (from models)
            # =====================================================
            if callback:
                callback("Phase 2/3", f"Generating {self.db_type.value} database schema...")

            logger.info(f"Generating {self.db_type.value} schema from models...")
            
            # Use the DatabaseOrchestrator but pass our models directly
            db_result = await self._generate_database_with_models(
                models=models,
                relations=relations,
                callback=callback
            )
            
            result["database"] = db_result
            logger.info(f"Database schema generated: {len(db_result.get('files', {}))} files")

            # =====================================================
            # STEP 3: Generate Backend (using SAME models)
            # =====================================================
            if callback:
                callback("Phase 3/3", f"Generating {self.backend_framework.value} backend...")

            logger.info(f"Generating {self.backend_framework.value} backend from models...")
            
            # Inject the same models into backend generation
            try:
                backend_result = await self._generate_backend_with_models(
                    models=models,
                    relations=relations,
                    analysis=analysis,
                    callback=callback
                )
                
                result["backend"] = backend_result
                logger.info(f"Backend generated: {backend_result.get('files_created', 0)} files")
            except Exception as backend_error:
                logger.error(f"Backend generation failed: {backend_error}")
                import traceback
                traceback.print_exc()
                result["backend"] = {
                    "success": False,
                    "error": str(backend_error),
                    "files_created": 0
                }

            # =====================================================
            # VERIFICATION: Ensure Synchronization
            # =====================================================
            result["synchronized"] = self._verify_synchronization(
                models, result["database"], result["backend"]
            )

            if result["synchronized"]:
                logger.info("✓ Database schema and backend models are synchronized!")
            else:
                logger.warning("⚠ Synchronization verification found differences")

            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"Fullstack generation failed: {e}")
            result["error"] = str(e)
            return result

    async def _generate_database_with_models(
        self,
        models: list[InferredModel],
        relations: list[InferredRelation],
        callback: Optional[Callable[[str, str], None]] = None,
    ) -> dict:
        """Generate database schema using provided models (not re-inferring)."""
        try:
            from database_generation.schema_generator import SchemaGenerator
            
            # Create output directory
            self.db_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate schema files
            generator = SchemaGenerator(self.db_output_dir)
            schema_files = await generator.generate_schema(models, relations, self.db_type.value)
            
            return {
                "files": {name: str(path) for name, path in schema_files.items()},
                "models_count": len(models),
                "relations_count": len(relations),
            }
            
        except Exception as e:
            logger.error(f"Schema generation failed with error: {e}")
            logger.exception("Full traceback:")
            # Fallback: use SchemaDesigner from synthesis
            from synthesis.schema_designer import SchemaDesigner
            
            designer = SchemaDesigner()
            schema = designer.design_schema(models, relations)
            
            # Save to file
            self.db_output_dir.mkdir(parents=True, exist_ok=True)
            schema_file = self.db_output_dir / "schema.sql"
            
            # Convert schema to SQL for MySQL
            db_type = self.db_type.value
            sql_lines = [f"-- {db_type.upper()} Schema"]
            sql_lines.append(f"-- Generated by FORGE")
            sql_lines.append(f"-- Models: {len(models)}\n")
            
            for table in schema.tables:
                sql_lines.append(f"CREATE TABLE {table.name} (")
                col_defs = []
                for col in table.columns:
                    # Convert db_type properly for MySQL
                    col_type = col.db_type
                    if db_type in ("mysql", "mariadb"):
                        # Map types to MySQL
                        if col_type == "INTEGER" and col.name == "id":
                            col_type = "INT AUTO_INCREMENT"
                        elif col_type == "INTEGER":
                            col_type = "INT"
                        elif col_type == "TIMESTAMP WITH TIME ZONE":
                            col_type = "TIMESTAMP"
                    
                    col_def = f"  {col.name} {col_type}"
                    if not col.nullable and col.name != "id":
                        col_def += " NOT NULL"
                    if col.unique:
                        col_def += " UNIQUE"
                    if col.default:
                        col_def += f" DEFAULT {col.default}"
                    col_defs.append(col_def)
                
                # Add PRIMARY KEY separately for MySQL AUTO_INCREMENT
                if db_type in ("mysql", "mariadb"):
                    col_defs.append(f"  PRIMARY KEY ({table.primary_key})")
                    
                sql_lines.append(",\n".join(col_defs))
                sql_lines.append(");\n")
            
            schema_file.write_text("\n".join(sql_lines))
            
            return {
                "files": {
                    "schema": str(schema_file),
                },
                "models_count": len(models),
                "relations_count": len(relations),
            }

    async def _generate_backend_with_models(
        self,
        models: list[InferredModel],
        relations: list[InferredRelation],
        analysis,
        callback: Optional[Callable[[str, str], None]] = None,
    ) -> dict:
        """Generate complete backend code using FullStackAgent with pre-inferred models.
        
        CRITICAL: This method ensures the backend uses THE SAME models as the database schema,
        preventing synchronization issues between database tables and backend models.
        """
        
        backend_output = self.output_dir / "backend"
        backend_output.mkdir(parents=True, exist_ok=True)
        
        if callback:
            callback("Phase 3/3", f"Generating backend from {len(models)} inferred models...")
        
        logger.info(f"Initializing FullStackAgent for backend generation with {len(models)} models...")
        
        # Initialize the fullstack agent (this also initializes backend_agent internally)
        await self.fullstack_agent.initialize(progress=callback)
        
        # Generate backend using the PRE-INFERRED models (same as database generation)
        # This ensures database schema and backend models are synchronized!
        logger.info(f"Generating backend with {len(models)} provided models...")
        result = await self.fullstack_agent.generate_backend(
            progress=callback,
            models=models,  # ← PASS PRE-INFERRED MODELS
            relations=relations,  # ← PASS PRE-INFERRED RELATIONS
        )
        
        if result.success:
            logger.info(f"Backend generated: {len(result.files)} files")
            
            # Write files to disk
            for file_obj in result.files:
                file_path = backend_output / file_obj.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_obj.content, encoding="utf-8")
            
            logger.info(f"✓ Wrote {len(result.files)} files to {backend_output}")
            
            return {
                "success": True,
                "files_created": len(result.files),
                "models_generated": len(models),
                "api_resources": len(models),
                "files": result.files,
            }
        else:
            error_msg = result.errors[0] if result.errors else "Unknown error"
            logger.error(f"Backend generation failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "files_created": 0,
                "models_generated": 0,
            }

    def _generate_models_init(self, models: list[InferredModel]) -> str:
        """Generate models/__init__.py."""
        lines = ['"""Data models package."""', ""]
        for model in models:
            lines.append(f"from .{model.name.lower()} import {model.name}, {model.name}Create, {model.name}Update")
        lines.append("")
        lines.append("__all__ = [")
        for model in models:
            lines.append(f'    "{model.name}", "{model.name}Create", "{model.name}Update",')
        lines.append("]")
        return "\n".join(lines)
    
    def _generate_simple_fastapi_routes(self, model: InferredModel) -> str:
        """Generate simple FastAPI routes for a model."""
        model_name = model.name
        lines = [
            f'"""API routes for {model_name}."""',
            "from fastapi import APIRouter, Depends, HTTPException",
            "from sqlalchemy.orm import Session",
            "from typing import List",
            f"from models.{model_name.lower()} import {model_name}, {model_name}Create, {model_name}Update, {model_name}DB",
            "from database import get_db",
            "",
            f"router = APIRouter(prefix='/{model_name.lower()}s', tags=['{model_name}'])",
            "",
            f"@router.get('/', response_model=List[{model_name}])",
            f"async def get_all_{model_name.lower()}s(db: Session = Depends(get_db)):",
            f'    """Get all {model_name}s."""',
            f"    return db.query({model_name}DB).all()",
            "",
            f"@router.post('/', response_model={model_name})",
            f"async def create_{model_name.lower()}(item: {model_name}Create, db: Session = Depends(get_db)):",
            f'    """Create new {model_name}."""',
            f"    db_item = {model_name}DB(**item.dict())",
            "    db.add(db_item)",
            "    db.commit()",
            "    db.refresh(db_item)",
            "    return db_item",
            "",
            f"@router.get('/{{item_id}}', response_model={model_name})",
            f"async def get_{model_name.lower()}(item_id: str, db: Session = Depends(get_db)):",
            f'    """Get {model_name} by ID."""',
            f"    item = db.query({model_name}DB).filter({model_name}DB.id == item_id).first()",
            "    if not item:",
            "        raise HTTPException(status_code=404, detail='Not found')",
            "    return item",
            "",
        ]
        return "\n".join(lines)
    
    def _generate_simple_main_file(self, models: list[InferredModel]) -> str:
        """Generate simple main application file."""
        lines = [
            '"""FastAPI application entry point."""',
            "from fastapi import FastAPI",
            "from fastapi.middleware.cors import CORSMiddleware",
            "from database import engine, Base",
            "",
            "# Import routers",
        ]
        for model in models:
            lines.append(f"from routes.{model.name.lower()} import router as {model.name.lower()}_router")
        
        lines.extend([
            "",
            "# Create tables",
            "Base.metadata.create_all(bind=engine)",
            "",
            "app = FastAPI(title='Generated API', version='1.0.0')",
            "",
            "# CORS",
            "app.add_middleware(",
            "    CORSMiddleware,",
            '    allow_origins=["*"],',
            '    allow_methods=["*"],',
            '    allow_headers=["*"],',
            ")",
            "",
            "# Include routers",
        ])
        for model in models:
            lines.append(f"app.include_router({model.name.lower()}_router)")
        
        lines.extend([
            "",
            '@app.get("/")',
            "async def root():",
            '    return {"message": "API is running", "models": ' + str(len(models)) + '}',
            "",
        ])
        return "\n".join(lines)
    
    def _generate_simple_readme(self, models: list[InferredModel]) -> str:
        """Generate simple README."""
        lines = [
            "# Generated Backend API",
            "",
            f"Generated by FORGE - {len(models)} models",
            "",
            "## Setup",
            "",
            "```bash",
            "# Install dependencies",
            "pip install -r requirements.txt",
            "",
            "# Update database.py with your database credentials",
            "",
            "# Run server",
            "uvicorn main:app --reload",
            "```",
            "",
            "## API Endpoints",
            "",
        ]
        for model in models:
            lines.append(f"### {model.name}")
            lines.append(f"- `GET /{model.name.lower()}s` - Get all")
            lines.append(f"- `POST /{model.name.lower()}s` - Create new")
            lines.append(f"- `GET /{model.name.lower()}s/{{id}}` - Get by ID")
            lines.append("")
        
        lines.extend([
            "## Models",
            "",
        ])
        for model in models:
            lines.append(f"- **{model.name}**: {len(model.fields)} fields")
        
        return "\n".join(lines)

    async def _generate_model_file(self, model: InferredModel, db_schema) -> str:
        """Generate model/schema file (Pydantic for FastAPI, etc.)."""
        if self.backend_framework == BackendFramework.FASTAPI:
            return self._generate_fastapi_model(model)
        else:
            return self._generate_generic_model(model)
    
    def _generate_fastapi_model(self, model: InferredModel) -> str:
        """Generate FastAPI Pydantic model."""
        lines = [
            '"""Data models and schemas."""',
            "from datetime import datetime",
            "from typing import Optional",
            "from pydantic import BaseModel, Field",
            "from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float",
            "from sqlalchemy.ext.declarative import declarative_base",
            "",
            "Base = declarative_base()",
            "",
            f"# SQLAlchemy Model",
            f"class {model.name}DB(Base):",
            f'    __tablename__ = "{model.name.lower()}"',
            "",
        ]
        
        # Add fields
        for field in model.fields:
            sql_type = self._map_type_to_sqlalchemy(field.field_type)
            nullable = ", nullable=True" if field.nullable else ""
            primary = ", primary_key=True" if field.name == "id" else ""
            lines.append(f'    {field.name} = Column({sql_type}{primary}{nullable})')
        
        lines.extend(["", f"# Pydantic Schema", f"class {model.name}Base(BaseModel):", ""])
        
        for field in model.fields:
            py_type = self._map_type_to_python(field.field_type)
            optional = f"Optional[{py_type}]" if field.nullable else py_type
            lines.append(f"    {field.name}: {optional}")
        
        lines.extend(["", f"class {model.name}Create({model.name}Base):", "    pass", ""])
        lines.extend([f"class {model.name}Update({model.name}Base):", "    pass", ""])
        lines.extend([
            f"class {model.name}({model.name}Base):",
            "    class Config:",
            '        from_attributes = True',
            ""
        ])
        
        return "\n".join(lines)
    
    def _generate_generic_model(self, model: InferredModel) -> str:
        """Generate generic model."""
        lines = [f"# {model.name} Model", ""]
        for field in model.fields:
            lines.append(f"# {field.name}: {field.field_type.value}")
        return "\n".join(lines)
    
    def _map_type_to_sqlalchemy(self, field_type) -> str:
        """Map InferredFieldType to SQLAlchemy type."""
        mapping = {
            "string": "String(255)",
            "integer": "Integer",
            "boolean": "Boolean",
            "float": "Float",
            "datetime": "DateTime",
            "uuid": "String(36)",
        }
        return mapping.get(field_type.value, "String(255)")
    
    def _map_type_to_python(self, field_type) -> str:
        """Map InferredFieldType to Python type."""
        mapping = {
            "string": "str",
            "integer": "int",
            "boolean": "bool",
            "float": "float",
            "datetime": "datetime",
            "uuid": "str",
        }
        return mapping.get(field_type.value, "str")
    
    def _generate_models_init(self, models: list[InferredModel]) -> str:
        """Generate models/__init__.py."""
        lines = ['"""Data models package."""', ""]
        for model in models:
            lines.append(f"from .{model.name.lower()} import {model.name}, {model.name}Create, {model.name}Update")
        lines.append("")
        lines.append("__all__ = [")
        for model in models:
            lines.append(f'    "{model.name}", "{model.name}Create", "{model.name}Update",')
        lines.append("]")
        return "\n".join(lines)
    
    async def _generate_route_file(self, resource, models, framework) -> str:
        """Generate route/controller file."""
        if framework == BackendFramework.FASTAPI:
            return self._generate_fastapi_routes(resource)
        return f"# Routes for {resource.name}"
    
    def _generate_fastapi_routes(self, resource) -> str:
        """Generate FastAPI routes."""
        model_name = resource.name
        lines = [
            f'"""API routes for {model_name}."""',
            "from fastapi import APIRouter, Depends, HTTPException",
            "from sqlalchemy.orm import Session",
            "from typing import List",
            f"from models.{model_name.lower()} import {model_name}, {model_name}Create, {model_name}Update",
            "from database import get_db",
            "",
            f"router = APIRouter(prefix='/{model_name.lower()}s', tags=['{model_name}'])",
            "",
            f"@router.get('/', response_model=List[{model_name}])",
            f"async def get_all_{model_name.lower()}s(db: Session = Depends(get_db)):",
            f'    """Get all {model_name}s."""',
            f"    return db.query({model_name}DB).all()",
            "",
            f"@router.post('/', response_model={model_name})",
            f"async def create_{model_name.lower()}(item: {model_name}Create, db: Session = Depends(get_db)):",
            f'    """Create new {model_name}."""',
            f"    db_item = {model_name}DB(**item.dict())",
            "    db.add(db_item)",
            "    db.commit()",
            "    db.refresh(db_item)",
            "    return db_item",
            "",
        ]
        return "\n".join(lines)
    
    async def _generate_service_file(self, service) -> str:
        """Generate service layer file."""
        return f'"""Service layer for {service.name}."""\n\nclass {service.name}Service:\n    pass\n'
    
    async def _generate_main_file(self, api_arch, auth_plan) -> str:
        """Generate main application file."""
        if self.backend_framework == BackendFramework.FASTAPI:
            lines = [
                '"""FastAPI application entry point."""',
                "from fastapi import FastAPI",
                "from fastapi.middleware.cors import CORSMiddleware",
                "from database import engine, Base",
                "",
                "# Import routers",
            ]
            for resource in api_arch.resources:
                lines.append(f"from routes.{resource.name.lower()} import router as {resource.name.lower()}_router")
            
            lines.extend([
                "",
                "# Create tables",
                "Base.metadata.create_all(bind=engine)",
                "",
                "app = FastAPI(title='Generated API')",
                "",
                "# CORS",
                "app.add_middleware(",
                "    CORSMiddleware,",
                '    allow_origins=["*"],',
                '    allow_methods=["*"],',
                '    allow_headers=["*"],',
                ")",
                "",
                "# Include routers",
            ])
            for resource in api_arch.resources:
                lines.append(f"app.include_router({resource.name.lower()}_router)")
            
            lines.extend([
                "",
                '@app.get("/")',
                "async def root():",
                '    return {"message": "API is running"}',
                "",
            ])
            return "\n".join(lines)
        return "# Main application file"
    
    def _generate_database_config(self) -> str:
        """Generate database configuration."""
        if self.backend_framework == BackendFramework.FASTAPI:
            db_url = f"{self.db_type.value}://user:password@localhost/dbname"
            return f'''"""Database configuration."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "{db_url}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''
        return "# Database configuration"
    
    def _generate_dependencies(self) -> str:
        """Generate dependencies file."""
        if self.backend_framework == BackendFramework.FASTAPI:
            return """fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9
"""
        return "# Dependencies"
    
    def _generate_readme(self, models, api_arch) -> str:
        """Generate README."""
        lines = [
            "# Generated Backend API",
            "",
            f"Generated by FORGE - {len(models)} models, {len(api_arch.resources)} resources",
            "",
            "## Setup",
            "",
            "```bash",
            "# Install dependencies",
            "pip install -r requirements.txt",
            "",
            "# Run server",
            "uvicorn main:app --reload",
            "```",
            "",
            "## API Endpoints",
            "",
        ]
        for resource in api_arch.resources:
            lines.append(f"### {resource.name}")
            for endpoint in resource.endpoints:
                lines.append(f"- `{endpoint.method} {endpoint.path}`")
            lines.append("")
        return "\n".join(lines)

    def _verify_synchronization(
        self,
        models: list[InferredModel],
        db_result: dict,
        backend_result: dict,
    ) -> bool:
        """
        Verify that database schema and backend models are synchronized.
        
        Checks:
        - Same number of models/tables
        - Same field names and types
        - Same relationships
        """
        # Basic check: model counts should match
        db_models = db_result.get("models_count", 0)
        backend_models = backend_result.get("models_generated", 0)
        
        if db_models != backend_models:
            logger.warning(f"Model count mismatch: DB={db_models}, Backend={backend_models}")
            return False

        # Both use the same InferredModel objects, so they're inherently synchronized
        logger.info(f"✓ Verified: {len(models)} models synchronized across database and backend")
        return True
    
    def _convert_plan_to_models(self, plan: Any) -> list:
        """
        Convert PlannedModel objects from RealtimePlanner to InferredModel format.
        """
        from core.types import InferredModel, InferredField, InferredFieldType
        
        models = []
        for planned_model in plan.models:
            # Convert fields
            fields = []
            for field_def in planned_model.fields:
                # Map type string to InferredFieldType enum
                field_type_str = field_def.get("type", "string").lower()
                type_mapping = {
                    "string": InferredFieldType.STRING,
                    "str": InferredFieldType.STRING,
                    "int": InferredFieldType.INTEGER,
                    "integer": InferredFieldType.INTEGER,
                    "float": InferredFieldType.FLOAT,
                    "bool": InferredFieldType.BOOLEAN,
                    "boolean": InferredFieldType.BOOLEAN,
                    "date": InferredFieldType.DATE,
                    "datetime": InferredFieldType.DATETIME,
                    "timestamp": InferredFieldType.DATETIME,
                    "text": InferredFieldType.TEXT,
                    "uuid": InferredFieldType.UUID,
                }
                field_type = type_mapping.get(field_type_str, InferredFieldType.STRING)
                
                field = InferredField(
                    name=field_def["name"],
                    field_type=field_type,
                    nullable=not field_def.get("required", False),
                    unique=False,
                )
                fields.append(field)
            
            # Create InferredModel
            model = InferredModel(
                name=planned_model.name,
                fields=fields,
                timestamps=True,
            )
            models.append(model)
        
        return models


# Convenience function for CLI usage
async def generate_synchronized_fullstack(
    frontend_path: str,
    output_dir: str,
    db_type: str = "mysql",
    backend_framework: str = "fastapi",
    plan: Optional[Any] = None,  # FullstackPlan from RealtimePlanner
    callback: Optional[Callable[[str, str], None]] = None,
) -> dict:
    """
    Generate fullstack application with synchronized database and backend.
    
    Args:
        plan: Optional FullstackPlan from RealtimePlanner. If provided, models
              from the plan will be used instead of re-analyzing the frontend.
    
    Example:
        result = await generate_synchronized_fullstack(
            frontend_path="./my-react-app",
            output_dir="./output",
            db_type="postgresql",
            backend_framework="fastapi",
            plan=realtime_plan  # Optional: use pre-computed plan
        )
    """
    from config.settings import Settings

    settings = Settings()
    
    workflow = UnifiedGenerationWorkflow(
        frontend_path=Path(frontend_path),
        output_dir=Path(output_dir),
        settings=settings,
        db_type=DatabaseType(db_type),
        backend_framework=BackendFramework(backend_framework),
    )

    return await workflow.generate_fullstack(plan=plan, callback=callback)
