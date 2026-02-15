"""Database orchestrator for FORGE - coordinates frontend analysis to database generation."""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional

from analyzers.frontend_analyzer import FrontendAnalyzer
from config.settings import Settings
from core.types import InferredModel, InferredRelation
from database_generation.database_manager import DatabaseManager
from database_generation.migration_engine import MigrationEngine
from database_generation.schema_generator import SchemaGenerator
from database_generation.seed_data_generator import SeedDataGenerator
from inference.model_inference_engine import ModelInferenceEngine
from inference.relationship_inferrer import RelationshipInferrer

logger = logging.getLogger(__name__)


class DatabaseOrchestrator:
    """Orchestrate end-to-end database generation from frontend analysis."""

    def __init__(
        self,
        frontend_path: Path,
        output_dir: Path,
        settings: Settings,
    ):
        self.frontend_path = Path(frontend_path)
        self.output_dir = Path(output_dir)
        self.settings = settings

        # Analyzers
        self.frontend_analyzer = FrontendAnalyzer(frontend_path)
        self.model_engine = ModelInferenceEngine()
        self.relation_inferrer = RelationshipInferrer()

        # Generators
        self.schema_generator = SchemaGenerator(output_dir)
        self.migration_engine = MigrationEngine(output_dir / "migrations")
        self.seed_generator = SeedDataGenerator(output_dir / "seeds")

    async def generate_database(
        self,
        db_type: str = "postgresql",
        skip_frontend: bool = False,
        records_per_model: int = 10,
        callback: Optional[Callable[[str, str], None]] = None,
    ) -> dict:
        """
        Complete database generation workflow.

        Steps:
        1. Analyze frontend (components, forms, API calls)
        2. Infer data models and relationships
        3. Generate database schema
        4. Create migrations
        5. Generate seed data

        Returns:
            Dictionary with paths to generated files
        """
        result = {
            "success": False,
            "models": [],
            "relations": [],
            "files": {},
            "errors": [],
        }

        try:
            # Step 1: Analyze Frontend
            if not skip_frontend:
                if callback:
                    callback("Frontend Analysis", "Scanning components and forms...")

                # Create indexer
                from indexers.unified_indexer import UnifiedIndexer
                indexer = UnifiedIndexer(self.frontend_path)
                await indexer.index_project()
                
                # Analyze with indexer
                analysis = await self.frontend_analyzer.analyze(indexer)

                # Extract models from analysis
                models = analysis.data_models
                
                # CRITICAL: Handle TypeScript timestamp fields for DataModel objects
                # DataModel uses FieldInfo, NOT InferredField
                from core.field_normalizer import is_timestamp_field, to_snake_case
                from core.types import FieldInfo
                
                for model in models:
                    # Remove TypeScript timestamp fields
                    model.fields = [
                        f for f in model.fields
                        if not is_timestamp_field(f.name)
                    ]
                    
                    # Normalize field names to snake_case and infer better types
                    normalized_fields = []
                    has_id = False
                    for field in model.fields:
                        # Convert camelCase to snake_case
                        normalized_name = to_snake_case(field.name)
                        
                        # Track if model already has ID field
                        if normalized_name == "id":
                            has_id = True
                        
                        # Improve type inference based on field name
                        field_type = field.field_type.lower() if field.field_type else "string"
                        
                        # Force UUID type for ID fields
                        if normalized_name == "id":
                            field_type = "uuid"
                        # Semantic type inference from field name
                        elif "description" in normalized_name.lower() or "bio" in normalized_name.lower() or "content" in normalized_name.lower() or "notes" in normalized_name.lower():
                            field_type = "text"  # TEXT for long text fields
                        elif "date" in normalized_name.lower() and "time" not in normalized_name.lower() and not normalized_name.lower().endswith("_at"):
                            field_type = "date"  # DATE for date-only fields (due_date, birth_date, etc.)
                        elif normalized_name.lower().endswith("_at") or "time" in normalized_name.lower() or "timestamp" in normalized_name.lower():
                            field_type = "datetime"  # DATETIME for timestamps
                        elif normalized_name.lower() in ["email", "url", "phone", "password"]:
                            field_type = "string"  # Keep as VARCHAR
                        
                        # Create normalized field
                        normalized_fields.append(
                            FieldInfo(
                                name=normalized_name,
                                field_type=field_type,
                                required=field.required if normalized_name == "id" else field.required,
                                nullable=False if normalized_name == "id" else field.nullable,
                                default=field.default if hasattr(field, 'default') else None,
                                array=field.array if hasattr(field, 'array') else False,
                                min_length=field.min_length if hasattr(field, 'min_length') else None,
                                max_length=field.max_length if hasattr(field, 'max_length') else None,
                                pattern=field.pattern if hasattr(field, 'pattern') else None,
                                validation=field.validation if hasattr(field, 'validation') else [],
                                metadata=field.metadata if hasattr(field, 'metadata') else {}
                            )
                        )
                    
                    model.fields = normalized_fields
                    
                    # Add ID field if not present
                    if not has_id:
                        model.fields.insert(
                            0,
                            FieldInfo(
                                name="id",
                                field_type="uuid",  # CHAR(36) for UUIDs
                                required=True,
                                nullable=False
                            )
                        )
                    
                    # Add SQL timestamp fields as FieldInfo objects
                    model.timestamps = True
                    model.fields.append(
                        FieldInfo(
                            name="created_at",
                            field_type="datetime",  # Matches InferredFieldType.DATETIME
                            required=True,
                            nullable=False
                        )
                    )
                    model.fields.append(
                        FieldInfo(
                            name="updated_at",
                            field_type="datetime",  # Matches InferredFieldType.DATETIME
                            required=True,
                            nullable=False
                        )
                    )
                
                # NOTE: Skip model_engine._add_common_fields() - it's for InferredModel not DataModel

                if callback:
                    callback("Relationship Analysis", f"Found {len(models)} models")

                # Infer relationships from field patterns only (API resources not compatible)
                relations = []
                model_names = {m.name.lower(): m.name for m in models}
                for model in models:
                    rels = self.relation_inferrer._infer_from_fields(model, model_names)
                    relations.extend(rels)

                logger.info(
                    f"Analysis complete: {len(models)} models, {len(relations)} relations"
                )
            else:
                # Load from cache or use provided models
                if callback:
                    callback("Loading", "Using existing models...")
                models = []
                relations = []

            result["models"] = models
            result["relations"] = relations

            if not models:
                logger.warning("No models found to generate database schema")
                result["errors"].append("No models found")
                return result

            # Step 2: Generate Schema
            if callback:
                callback("Schema Generation", f"Creating {db_type} schema...")

            schema_files = await self.schema_generator.generate_schema(
                models, relations, db_type
            )
            result["files"]["schema"] = schema_files

            logger.info(f"Schema generated: {list(schema_files.keys())}")

            # Step 3: Create Migration
            if callback:
                callback("Migration", "Creating migration files...")

            migration_file = await self.migration_engine.create_migration(
                "initial_schema", models, db_type
            )
            result["files"]["migration"] = migration_file

            logger.info(f"Migration created: {migration_file}")

            # Step 4: Generate Seed Data
            if callback:
                callback("Seed Data", f"Generating test data ({records_per_model} records per model)...")

            seed_files = await self.seed_generator.generate_seed_data(
                models, db_type, records_per_model
            )
            result["files"]["seeds"] = seed_files

            logger.info(f"Seed data generated: {list(seed_files.keys())}")

            # Step 5: Save summary
            if callback:
                callback("Finalizing", "Saving generation summary...")

            await self._save_summary(models, relations, db_type, result["files"])

            result["success"] = True
            logger.info("Database generation completed successfully")

        except Exception as e:
            logger.error(f"Database generation failed: {e}", exc_info=True)
            result["errors"].append(str(e))
            raise

        return result

    async def create_and_seed_database(
        self,
        connection_string: str,
        db_name: str,
        schema_file: Path,
        seed_dir: Path,
        callback: Optional[Callable[[str, str], None]] = None,
    ):
        """Create database and load schema + seed data."""
        db_manager = DatabaseManager(connection_string)

        try:
            # Create database
            if callback:
                callback("Database Creation", f"Creating database {db_name}...")

            await db_manager.create_database(db_name)

            # Connect to database
            if callback:
                callback("Connection", f"Connecting to {db_name}...")

            await db_manager.connect(db_name)

            # Load schema
            if callback:
                callback("Schema", "Creating tables and indexes...")

            schema_sql = schema_file.read_text(encoding="utf-8")
            await db_manager.execute_sql(schema_sql)

            # Load seed data
            if callback:
                callback("Seed Data", "Loading test data...")

            seed_files = sorted(seed_dir.glob("*.sql"))
            for seed_file in seed_files:
                logger.info(f"Loading seed data: {seed_file.name}")
                seed_sql = seed_file.read_text(encoding="utf-8")
                await db_manager.execute_sql(seed_sql)

            if callback:
                callback("Complete", f"Database {db_name} ready!")

            logger.info(f"Database {db_name} created and seeded successfully")

        finally:
            await db_manager.close()

    async def _save_summary(
        self,
        models: list[InferredModel],
        relations: list[InferredRelation],
        db_type: str,
        files: dict,
    ):
        """Save generation summary."""
        import json

        summary = {
            "database_type": db_type,
            "generated_at": datetime.now().isoformat(),
            "models": [
                {
                    "name": m.name,
                    "fields": len(m.fields),
                    "primary_key": getattr(m, 'primary_key', 'id'),
                    "timestamps": getattr(m, 'timestamps', False),
                    "soft_delete": getattr(m, 'soft_delete', False),
                }
                for m in models
            ],
            "relationships": [
                {
                    "source": r.source_model,
                    "target": r.target_model,
                    "type": r.relation_type.value,
                }
                for r in relations
            ],
            "files": {
                k: str(v) if isinstance(v, Path) else {k2: str(v2) for k2, v2 in v.items()}
                for k, v in files.items()
            },
        }

        summary_file = self.output_dir / "generation_summary.json"
        summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        logger.info(f"Summary saved: {summary_file}")

from datetime import datetime
