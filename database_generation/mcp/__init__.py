"""
MCP (Model Context Protocol) servers for database integration.

Provides MCP servers for PostgreSQL, MySQL, and MongoDB that can be
connected to by AI agents and external tools.
"""

from .hub import MCPHub

# Optional server imports
try:
    from .postgres_server import PostgreSQLMCPServer
except ImportError:
    PostgreSQLMCPServer = None

try:
    from .mysql_server import MySQLMCPServer
except ImportError:
    MySQLMCPServer = None

try:
    from .mongodb_server import MongoDBMCPServer
except ImportError:
    MongoDBMCPServer = None


__all__ = ["MCPHub"]

if PostgreSQLMCPServer:
    __all__.append("PostgreSQLMCPServer")
if MySQLMCPServer:
    __all__.append("MySQLMCPServer")
if MongoDBMCPServer:
    __all__.append("MongoDBMCPServer")
