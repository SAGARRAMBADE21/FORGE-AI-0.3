"""Database manager for connection and database operations."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage database connections and operations."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.db_type = self._detect_db_type(connection_string)
        self.connection = None

    def _detect_db_type(self, conn_str: str) -> str:
        """Detect database type from connection string."""
        if conn_str.startswith("postgresql://") or conn_str.startswith("postgres://"):
            return "postgresql"
        elif conn_str.startswith("mysql://"):
            return "mysql"
        elif conn_str.startswith("mongodb://") or conn_str.startswith("mongodb+srv://"):
            return "mongodb"
        elif conn_str.startswith("sqlite://"):
            return "sqlite"
        elif conn_str.startswith("mariadb://"):
            return "mariadb"
        elif conn_str.startswith("oracle://"):
            return "oracle"
        elif conn_str.startswith("mssql://"):
            return "sqlserver"
        else:
            raise ValueError(f"Unknown database type in connection string: {conn_str}")

    async def connect(self, database: str | None = None):
        """Establish database connection."""
        logger.info(f"Connecting to {self.db_type} database...")

        if self.db_type == "postgresql":
            import asyncpg
            
            # Parse connection string
            conn_str = self.connection_string.replace("postgresql://", "").replace("postgres://", "")
            if database:
                conn_str = f"{conn_str}/{database}"
            
            self.connection = await asyncpg.connect(f"postgresql://{conn_str}")
            
        elif self.db_type == "mysql":
            import aiomysql
            
            # Parse connection string
            parts = self.connection_string.replace("mysql://", "").split("@")
            user_pass = parts[0].split(":")
            host_port = parts[1].split(":") if ":" in parts[1] else [parts[1], "3306"]
            
            self.connection = await aiomysql.connect(
                host=host_port[0],
                port=int(host_port[1]) if len(host_port) > 1 else 3306,
                user=user_pass[0],
                password=user_pass[1] if len(user_pass) > 1 else "",
                db=database,
            )
            
        elif self.db_type == "mongodb":
            from motor import motor_asyncio
            
            self.connection = motor_asyncio.AsyncIOMotorClient(self.connection_string)
            if database:
                self.connection = self.connection[database]
                
        elif self.db_type == "sqlite":
            import aiosqlite
            
            db_path = self.connection_string.replace("sqlite://", "")
            self.connection = await aiosqlite.connect(db_path)
            
        else:
            raise NotImplementedError(f"Database type {self.db_type} not yet implemented")

        logger.info(f"Connected to {self.db_type}")

    async def create_database(self, db_name: str):
        """Create a new database."""
        logger.info(f"Creating database: {db_name}")

        if self.db_type == "postgresql":
            import asyncpg
            
            # Connect without database
            conn_str = self.connection_string.replace("postgresql://", "").replace("postgres://", "")
            conn = await asyncpg.connect(f"postgresql://{conn_str}/postgres")
            
            # Check if database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            
            if not exists:
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"Database {db_name} created")
            else:
                logger.info(f"Database {db_name} already exists")
                
            await conn.close()
            
        elif self.db_type in ("mysql", "mariadb"):
            import aiomysql
            
            # Parse connection string
            parts = self.connection_string.replace("mysql://", "").replace("mariadb://", "").split("@")
            user_pass = parts[0].split(":")
            host_port = parts[1].split(":") if ":" in parts[1] else [parts[1], "3306"]
            
            conn = await aiomysql.connect(
                host=host_port[0],
                port=int(host_port[1]) if len(host_port) > 1 else 3306,
                user=user_pass[0],
                password=user_pass[1] if len(user_pass) > 1 else "",
            )
            
            cursor = await conn.cursor()
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            await cursor.close()
            conn.close()
            
            logger.info(f"Database {db_name} created")
            
        elif self.db_type == "mongodb":
            # MongoDB creates databases automatically
            logger.info(f"MongoDB database {db_name} will be created on first write")
            
        elif self.db_type == "sqlite":
            # SQLite creates file automatically
            logger.info(f"SQLite database will be created at {db_name}")

    async def execute_sql(self, sql: str):
        """Execute SQL statements."""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        logger.info("Executing SQL...")

        if self.db_type == "postgresql":
            # Split into individual statements
            statements = [s.strip() for s in sql.split(";") if s.strip()]
            
            async with self.connection.transaction():
                for stmt in statements:
                    await self.connection.execute(stmt)
                    
        elif self.db_type in ("mysql", "mariadb"):
            cursor = await self.connection.cursor()
            
            statements = [s.strip() for s in sql.split(";") if s.strip()]
            for stmt in statements:
                await cursor.execute(stmt)
                
            await self.connection.commit()
            await cursor.close()
            
        elif self.db_type == "sqlite":
            await self.connection.executescript(sql)
            await self.connection.commit()

        logger.info("SQL executed successfully")

    async def close(self):
        """Close database connection."""
        if self.connection:
            if self.db_type == "postgresql":
                await self.connection.close()
            elif self.db_type in ("mysql", "mariadb"):
                self.connection.close()
            elif self.db_type == "sqlite":
                await self.connection.close()
            elif self.db_type == "mongodb":
                self.connection.close()
                
            logger.info("Database connection closed")

    def save_connection_info(self, output_dir: Path, db_name: str):
        """Save connection information to file."""
        info = {
            "database_type": self.db_type,
            "database_name": db_name,
            "connection_string": self.connection_string,
        }
        
        info_file = output_dir / "connection_info.json"
        info_file.write_text(json.dumps(info, indent=2), encoding="utf-8")
        
        logger.info(f"Connection info saved to {info_file}")
