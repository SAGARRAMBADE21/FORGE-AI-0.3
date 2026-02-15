"""Migration engine for database version control."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from core.types import InferredModel

logger = logging.getLogger(__name__)


class MigrationEngine:
    """Generate and manage database migrations."""

    def __init__(self, migrations_dir: Path):
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

    async def create_migration(
        self,
        name: str,
        models: list[InferredModel],
        db_type: str = "postgresql",
    ) -> Path:
        """Create a new migration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_name = f"{timestamp}_{name}.sql"
        migration_file = self.migrations_dir / migration_name

        logger.info(f"Creating migration: {migration_name}")

        # Generate migration SQL
        from database_generation.schema_generator import SchemaGenerator
        
        # Use temp directory for schema generation
        temp_dir = self.migrations_dir / ".temp"
        temp_dir.mkdir(exist_ok=True)
        
        schema_gen = SchemaGenerator(temp_dir)
        files = await schema_gen.generate_schema(models, [], db_type)
        
        # Read generated schema
        schema_content = files["schema"].read_text()
        
        # Create migration with up/down sections
        migration_content = f"""-- Migration: {name}
-- Generated: {datetime.now().isoformat()}
-- Database: {db_type}

-- =============================================
-- UP
-- =============================================

{schema_content}

-- =============================================
-- DOWN (Rollback)
-- =============================================

{self._generate_down_migration(models)}
"""

        migration_file.write_text(migration_content, encoding="utf-8")
        
        # Cleanup temp
        for f in temp_dir.glob("*"):
            f.unlink()
        temp_dir.rmdir()

        logger.info(f"Migration created: {migration_file}")
        return migration_file

    def _generate_down_migration(self, models: list[InferredModel]) -> str:
        """Generate rollback SQL."""
        lines = []
        
        # Drop tables in reverse order (to handle foreign keys)
        for model in reversed(models):
            lines.append(f"DROP TABLE IF EXISTS {model.name.lower()} CASCADE;")
        
        return "\n".join(lines)

    async def apply_migration(self, migration_file: Path, db_manager):
        """Apply a migration to the database."""
        logger.info(f"Applying migration: {migration_file.name}")

        content = migration_file.read_text()
        
        # Extract UP section
        up_start = content.find("-- UP")
        down_start = content.find("-- DOWN")
        
        if up_start == -1 or down_start == -1:
            # Old format, just execute whole file
            up_sql = content
        else:
            up_sql = content[up_start:down_start]
            # Remove comment lines
            up_sql = "\n".join(
                line for line in up_sql.split("\n") 
                if not line.strip().startswith("--")
            )

        await db_manager.execute_sql(up_sql)
        
        # Record migration in migrations table
        await self._record_migration(db_manager, migration_file.name)

        logger.info(f"Migration applied: {migration_file.name}")

    async def apply_all_migrations(self, db_manager):
        """Apply all pending migrations."""
        # Get applied migrations
        applied = await self._get_applied_migrations(db_manager)

        # Get all migration files
        migration_files = sorted(self.migrations_dir.glob("*.sql"))

        # Apply pending migrations
        for migration_file in migration_files:
            if migration_file.name not in applied:
                await self.apply_migration(migration_file, db_manager)

    async def _record_migration(self, db_manager, migration_name: str):
        """Record migration in schema_migrations table."""
        # Create migrations table if not exists
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            migration VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        await db_manager.execute_sql(create_table_sql)
        
        # Insert migration record
        insert_sql = f"""
        INSERT INTO schema_migrations (migration) 
        VALUES ('{migration_name}')
        ON CONFLICT (migration) DO NOTHING;
        """
        
        await db_manager.execute_sql(insert_sql)

    async def _get_applied_migrations(self, db_manager) -> set[str]:
        """Get list of applied migrations."""
        try:
            # Query migrations table
            if hasattr(db_manager.connection, 'fetch'):
                # asyncpg
                rows = await db_manager.connection.fetch(
                    "SELECT migration FROM schema_migrations"
                )
                return {row['migration'] for row in rows}
            else:
                return set()
        except Exception as e:
            logger.warning(f"Could not fetch migrations: {e}")
            return set()

    def list_migrations(self) -> list[str]:
        """List all migration files."""
        return sorted([f.name for f in self.migrations_dir.glob("*.sql")])
