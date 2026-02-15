from .database_fundamentals import DATABASE_FUNDAMENTALS_XML
from .data_types import DATA_TYPES_XML
from .indexing import INDEXING_XML
from .normalization import NORMALIZATION_XML
from .relationships import RELATIONSHIPS_XML
from .performance import PERFORMANCE_XML
from .security import SECURITY_XML
from .anti_patterns import ANTI_PATTERNS_XML
from .postgresql import POSTGRESQL_XML
from .mysql import MYSQL_XML
from .mongodb import MONGODB_XML
from .sqlite import SQLITE_XML
from .sqlserver import SQLSERVER_XML
from .oracle import ORACLE_XML
from .mariadb import MARIADB_XML
from .redis import REDIS_XML

COMPLETE_KNOWLEDGE_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<forge_knowledge_base version="2.0">
{DATABASE_FUNDAMENTALS_XML}
{DATA_TYPES_XML}
{NORMALIZATION_XML}
{RELATIONSHIPS_XML}
{INDEXING_XML}
{PERFORMANCE_XML}
{SECURITY_XML}
{ANTI_PATTERNS_XML}
<databases>
{POSTGRESQL_XML}
{MYSQL_XML}
{MONGODB_XML}
{SQLITE_XML}
{SQLSERVER_XML}
{ORACLE_XML}
{MARIADB_XML}
{REDIS_XML}
</databases>
</forge_knowledge_base>
"""

__all__ = [
    "DATABASE_FUNDAMENTALS_XML", "DATA_TYPES_XML", "INDEXING_XML", "NORMALIZATION_XML",
    "RELATIONSHIPS_XML", "PERFORMANCE_XML", "SECURITY_XML", "ANTI_PATTERNS_XML",
    "POSTGRESQL_XML", "MYSQL_XML", "MONGODB_XML", "SQLITE_XML",
    "SQLSERVER_XML", "ORACLE_XML", "MARIADB_XML", "REDIS_XML", "COMPLETE_KNOWLEDGE_XML"
]
