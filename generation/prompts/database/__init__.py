# generation/prompts/database/__init__.py
"""
Database Prompts
"""

from .indexing_prompt import INDEXING_PROMPT
from .nosql_prompt import NOSQL_PROMPT
from .schema_design_prompt import SCHEMA_DESIGN_PROMPT
from .sharding_replication_prompt import SHARDING_REPLICATION_PROMPT
from .sql_prompt import SQL_PROMPT
from .transactions_prompt import TRANSACTIONS_PROMPT

DATABASE_PROMPTS = {
    "sql": SQL_PROMPT,
    "nosql": NOSQL_PROMPT,
    "schema_design": SCHEMA_DESIGN_PROMPT,
    "indexing": INDEXING_PROMPT,
    "transactions": TRANSACTIONS_PROMPT,
    "sharding_replication": SHARDING_REPLICATION_PROMPT,
}

__all__ = [
    "DATABASE_PROMPTS",
    "SQL_PROMPT",
    "NOSQL_PROMPT",
    "SCHEMA_DESIGN_PROMPT",
    "INDEXING_PROMPT",
    "TRANSACTIONS_PROMPT",
    "SHARDING_REPLICATION_PROMPT",
]
