# Base converter
"""
Base Converter
"""

from abc import ABC, abstractmethod
from database_generation.db_types import ForgeSchema, EditorType


class BaseConverter(ABC):
    """Base class for database converters"""
    
    @abstractmethod
    def convert(self, schema: ForgeSchema) -> str:
        """Convert schema to database-specific DDL"""
        pass
    
    @abstractmethod
    def format_for_editor(self, ddl: str, editor: EditorType) -> str:
        """Format DDL for specific editor"""
        pass