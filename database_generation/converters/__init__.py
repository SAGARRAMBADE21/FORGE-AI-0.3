"""
Database Converters
"""

from database_generation.db_types import DatabaseType
from database_generation.converters.postgresql import PostgreSQLConverter
from database_generation.converters.mysql import MySQLConverter
from database_generation.converters.mongodb import MongoDBConverter


def get_converter(database_type: DatabaseType):
    """Get converter for database type"""
    
    converters = {
        DatabaseType.POSTGRESQL: PostgreSQLConverter,
        DatabaseType.MYSQL: MySQLConverter,
        DatabaseType.MONGODB: MongoDBConverter,
    }
    
    converter_class = converters.get(database_type)
    return converter_class() if converter_class else None


__all__ = [
    "get_converter",
    "PostgreSQLConverter",
    "MySQLConverter",
    "MongoDBConverter"
]