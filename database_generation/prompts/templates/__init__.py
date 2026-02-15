from .postgresql_templates import POSTGRESQL_TEMPLATE_XML
from .mysql_templates import MYSQL_TEMPLATE_XML
from .mariadb_templates import MARIADB_TEMPLATE_XML
from .sqlite_templates import SQLITE_TEMPLATE_XML
from .sqlserver_templates import SQLSERVER_TEMPLATE_XML
from .oracle_templates import ORACLE_TEMPLATE_XML
from .mongodb_templates import MONGODB_TEMPLATE_XML
from .redis_templates import REDIS_TEMPLATE_XML

__all__ = [
    "POSTGRESQL_TEMPLATE_XML",
    "MYSQL_TEMPLATE_XML",
    "MARIADB_TEMPLATE_XML",
    "SQLITE_TEMPLATE_XML",
    "SQLSERVER_TEMPLATE_XML",
    "ORACLE_TEMPLATE_XML",
    "MONGODB_TEMPLATE_XML",
    "REDIS_TEMPLATE_XML",
]