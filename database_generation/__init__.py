"""
Database generation module for FORGE - Complete Integration.

This module provides comprehensive database schema generation with multi-agent AI,
migration management, seed data creation, interactive editing, and MCP protocol support.

Features:
- Multi-Agent System: LeadArchitect, DataModeler, DBAExpert, SQLWriter, Reviewer
- Database Converters: PostgreSQL, MySQL, MongoDB, Oracle, MariaDB, SQLite, SQL Server  
- Domain Patterns: E-commerce, SaaS, Social, Marketplace, Content
- Interactive Editor: Schema editing with validation
- AI Engine: LLM-powered schema optimization
- Chat Interface: Conversational schema design
- MCP Servers: Model Context Protocol for PostgreSQL, MySQL, MongoDB
"""

# Core modules - always available
from .database_manager import DatabaseManager
from .orchestrator import DatabaseOrchestrator
from .migration_engine import MigrationEngine
from .schema_generator import SchemaGenerator
from .seed_data_generator import SeedDataGenerator

__all__ = [
    # Core
    "DatabaseManager",
    "DatabaseOrchestrator", 
    "MigrationEngine",
    "SchemaGenerator",
    "SeedDataGenerator",
]

# Advanced features - optional imports (may have dependencies)
try:
    from .agents.team_manager import TeamManager
    from .agents.lead_architect import LeadArchitectAgent
    from .agents.data_modeler import DataModelerAgent
    from .agents.dba_expert import DBAExpertAgent
    from .agents.sql_writer import SQLWriterAgent
    from .agents.reviewer import ReviewerAgent
    from .agents.chat_agent import ChatAgent
    
    __all__.extend([
        "TeamManager",
        "LeadArchitectAgent",
        "DataModelerAgent",
        "DBAExpertAgent",
        "SQLWriterAgent",
        "ReviewerAgent",
        "ChatAgent",
    ])
except ImportError as e:
    print(f"Warning: Multi-agent system not available: {e}")

try:
    from .converters.postgresql import PostgreSQLConverter
    from .converters.mysql import MySQLConverter
    from .converters.mongodb import MongoDBConverter
    from .converters.sqlite import SQLiteConverter
    from .converters.oracle import OracleConverter
    from .converters.mariadb import MariaDBConverter
    from .converters.sqlserver import SQLServerConverter
    
    __all__.extend([
        "PostgreSQLConverter",
        "MySQLConverter",
        "MongoDBConverter",
        "SQLiteConverter",
        "OracleConverter",
        "MariaDBConverter",
        "SQLServerConverter",
    ])
except ImportError as e:
    print(f"Warning: Database converters not available: {e}")

try:
    from .engine.ai_engine import AIEngine
    from .engine.schema_builder import SchemaBuilder
    # Note: Orchestrator class name may differ
    try:
        from .engine.orchestrator import AdvancedOrchestrator
    except ImportError:
        from .engine.orchestrator import Orchestrator as AdvancedOrchestrator
    
    __all__.extend([
        "AIEngine",
        "SchemaBuilder",
        "AdvancedOrchestrator",
    ])
except ImportError as e:
    print(f"Warning: AI engine not available: {e}")

try:
    from .editor.schema_editor import SchemaEditor
    from .editor.interactive import InteractiveEditor
    from .editor.validators import SchemaValidator
    
    __all__.extend([
        "SchemaEditor",
        "InteractiveEditor",
        "SchemaValidator",
    ])
except ImportError as e:
    print(f"Warning: Schema editor not available: {e}")

try:
    from .chat.assistant import ChatAssistant
    from .chat.session import ChatSession
    from .chat.command_handler import CommandHandler
    
    __all__.extend([
        "ChatAssistant",
        "ChatSession",
        "CommandHandler",
    ])
except ImportError as e:
    print(f"Warning: Chat interface not available: {e}")

try:
    from .mcp.hub import MCPHub
    # Note: Server class names may differ
    try:
        from .mcp.postgres_server import PostgresMCPServer
    except (ImportError, AttributeError):
        from .mcp.postgres_server import PostgreSQLMCPServer as PostgresMCPServer
    try:
        from .mcp.mysql_server import MySQLMCPServer
    except ImportError:
        MySQLMCPServer = None
    try:
        from .mcp.mongodb_server import MongoDBMCPServer
    except ImportError:
        MongoDBMCPServer = None
    
    exports = ["MCPHub"]
    if PostgresMCPServer: exports.append("PostgresMCPServer")
    if MySQLMCPServer: exports.append("MySQLMCPServer")
    if MongoDBMCPServer: exports.append("MongoDBMCPServer")
    __all__.extend(exports)
except ImportError as e:
    print(f"Warning: MCP servers not available: {e}")
