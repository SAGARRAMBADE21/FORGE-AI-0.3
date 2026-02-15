# PostgreSQL MCP server
"""
PostgreSQL MCP Server - Complete Implementation
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Sequence
from contextlib import asynccontextmanager

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource, ResourceTemplate
except ImportError:
    from database_generation.mcp_stub import Server, Tool, TextContent, Resource, ResourceTemplate, stdio_server


class PostgreSQLMCPServer:
    """MCP Server for PostgreSQL database operations"""
    
    def __init__(self):
        self.server = Server("forge-postgres-mcp")
        self.connection = None
        self.connection_params: Dict[str, Any] = {}
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP request handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="connect_database",
                    description="Connect to a PostgreSQL database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "Database host"},
                            "port": {"type": "integer", "description": "Database port", "default": 5432},
                            "database": {"type": "string", "description": "Database name"},
                            "user": {"type": "string", "description": "Username"},
                            "password": {"type": "string", "description": "Password"},
                        },
                        "required": ["host", "database", "user", "password"]
                    }
                ),
                Tool(
                    name="disconnect_database",
                    description="Disconnect from the database",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="execute_schema",
                    description="Execute FORGE-generated schema",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string", "description": "SQL schema to execute"},
                            "use_transaction": {"type": "boolean", "default": True}
                        },
                        "required": ["sql"]
                    }
                ),
                Tool(
                    name="execute_query",
                    description="Execute a SQL query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string", "description": "SQL query"},
                            "params": {"type": "array", "description": "Query parameters"}
                        },
                        "required": ["sql"]
                    }
                ),
                Tool(
                    name="get_schema_info",
                    description="Get current database schema information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schema_name": {"type": "string", "default": "public"}
                        }
                    }
                ),
                Tool(
                    name="get_table_info",
                    description="Get detailed information about a table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "Table name"},
                            "schema_name": {"type": "string", "default": "public"}
                        },
                        "required": ["table_name"]
                    }
                ),
                Tool(
                    name="validate_sql",
                    description="Validate SQL syntax without executing",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string", "description": "SQL to validate"}
                        },
                        "required": ["sql"]
                    }
                ),
                Tool(
                    name="export_for_pgadmin",
                    description="Format SQL for pgAdmin",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string", "description": "SQL to format"}
                        },
                        "required": ["sql"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            try:
                if name == "connect_database":
                    result = await self._connect(arguments)
                elif name == "disconnect_database":
                    result = await self._disconnect()
                elif name == "execute_schema":
                    result = await self._execute_schema(arguments)
                elif name == "execute_query":
                    result = await self._execute_query(arguments)
                elif name == "get_schema_info":
                    result = await self._get_schema_info(arguments)
                elif name == "get_table_info":
                    result = await self._get_table_info(arguments)
                elif name == "validate_sql":
                    result = await self._validate_sql(arguments)
                elif name == "export_for_pgadmin":
                    result = await self._export_for_pgadmin(arguments)
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            if not self.connection:
                return []
            
            try:
                cursor = self.connection.cursor()
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = cursor.fetchall()
                cursor.close()
                
                return [
                    Resource(
                        uri=f"postgres://tables/{table[0]}",
                        name=table[0],
                        description=f"Table: {table[0]}",
                        mimeType="application/json"
                    )
                    for table in tables
                ]
            except Exception:
                return []
    
    async def _connect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to PostgreSQL database"""
        if not psycopg2:
            return {"success": False, "error": "psycopg2 not installed"}
        
        try:
            self.connection_params = {
                "host": args["host"],
                "port": args.get("port", 5432),
                "database": args["database"],
                "user": args["user"],
                "password": args["password"]
            }
            
            self.connection = psycopg2.connect(**self.connection_params)
            
            # Get version info
            cursor = self.connection.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            
            return {
                "success": True,
                "message": "Connected successfully",
                "database": args["database"],
                "host": args["host"],
                "version": version
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _disconnect(self) -> Dict[str, Any]:
        """Disconnect from database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            return {"success": True, "message": "Disconnected"}
        return {"success": True, "message": "Not connected"}
    
    async def _execute_schema(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute schema DDL"""
        if not self.connection:
            return {"success": False, "error": "Not connected to database"}
        
        sql = args["sql"]
        use_transaction = args.get("use_transaction", True)
        
        try:
            cursor = self.connection.cursor()
            
            if use_transaction:
                # SQL should already have BEGIN/COMMIT
                cursor.execute(sql)
            else:
                self.connection.autocommit = True
                cursor.execute(sql)
                self.connection.autocommit = False
            
            self.connection.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": "Schema executed successfully"
            }
            
        except Exception as e:
            self.connection.rollback()
            return {"success": False, "error": str(e)}
    
    async def _execute_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a SQL query"""
        if not self.connection:
            return {"success": False, "error": "Not connected to database"}
        
        sql = args["sql"]
        params = args.get("params", [])
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(sql, params)
            
            # Check if it's a SELECT query
            if cursor.description:
                rows = cursor.fetchall()
                result = {
                    "success": True,
                    "rows": [dict(row) for row in rows],
                    "rowcount": len(rows),
                    "columns": [desc[0] for desc in cursor.description]
                }
            else:
                self.connection.commit()
                result = {
                    "success": True,
                    "rowcount": cursor.rowcount,
                    "message": f"Query affected {cursor.rowcount} rows"
                }
            
            cursor.close()
            return result
            
        except Exception as e:
            self.connection.rollback()
            return {"success": False, "error": str(e)}
    
    async def _get_schema_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get database schema information"""
        if not self.connection:
            return {"success": False, "error": "Not connected to database"}
        
        schema_name = args.get("schema_name", "public")
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Get tables
            cursor.execute("""
                SELECT 
                    t.table_name,
                    obj_description((quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass) as comment
                FROM information_schema.tables t
                WHERE t.table_schema = %s AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name
            """, (schema_name,))
            
            tables = []
            for table in cursor.fetchall():
                # Get columns for each table
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema_name, table["table_name"]))
                
                columns = [dict(col) for col in cursor.fetchall()]
                
                # Get indexes
                cursor.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = %s AND tablename = %s
                """, (schema_name, table["table_name"]))
                
                indexes = [dict(idx) for idx in cursor.fetchall()]
                
                tables.append({
                    "name": table["table_name"],
                    "comment": table["comment"],
                    "columns": columns,
                    "indexes": indexes
                })
            
            cursor.close()
            
            return {
                "success": True,
                "schema": schema_name,
                "tables": tables
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_table_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed table information"""
        if not self.connection:
            return {"success": False, "error": "Not connected to database"}
        
        table_name = args["table_name"]
        schema_name = args.get("schema_name", "public")
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Get columns
            cursor.execute("""
                SELECT *
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (schema_name, table_name))
            columns = [dict(col) for col in cursor.fetchall()]
            
            # Get constraints
            cursor.execute("""
                SELECT 
                    conname as name,
                    contype as type,
                    pg_get_constraintdef(oid) as definition
                FROM pg_constraint
                WHERE conrelid = %s::regclass
            """, (f"{schema_name}.{table_name}",))
            constraints = [dict(con) for con in cursor.fetchall()]
            
            # Get indexes
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = %s AND tablename = %s
            """, (schema_name, table_name))
            indexes = [dict(idx) for idx in cursor.fetchall()]
            
            # Get row count estimate
            cursor.execute("""
                SELECT reltuples::bigint as estimate
                FROM pg_class
                WHERE relname = %s
            """, (table_name,))
            row_count = cursor.fetchone()
            
            cursor.close()
            
            return {
                "success": True,
                "table": table_name,
                "schema": schema_name,
                "columns": columns,
                "constraints": constraints,
                "indexes": indexes,
                "estimated_rows": row_count["estimate"] if row_count else 0
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _validate_sql(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SQL without executing"""
        if not self.connection:
            return {"success": False, "error": "Not connected to database"}
        
        sql = args["sql"]
        
        try:
            cursor = self.connection.cursor()
            
            # Use EXPLAIN to validate without executing
            # Wrap in transaction and rollback
            cursor.execute("BEGIN")
            
            # Try to prepare the statement
            statements = self._split_sql(sql)
            validated = []
            
            for stmt in statements:
                if stmt.strip():
                    try:
                        cursor.execute(stmt)
                        validated.append({
                            "statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "valid": True
                        })
                    except Exception as e:
                        validated.append({
                            "statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "valid": False,
                            "error": str(e)
                        })
            
            cursor.execute("ROLLBACK")
            cursor.close()
            
            all_valid = all(v["valid"] for v in validated)
            
            return {
                "success": True,
                "valid": all_valid,
                "statements": validated
            }
            
        except Exception as e:
            self.connection.rollback()
            return {"success": False, "error": str(e)}
    
    async def _export_for_pgadmin(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Format SQL for pgAdmin"""
        sql = args["sql"]
        
        formatted = f"""-- =============================================
-- pgAdmin 4 Export
-- Generated by FORGE MCP Server
-- =============================================

\\set ON_ERROR_STOP on

{sql}
"""
        
        return {
            "success": True,
            "formatted_sql": formatted,
            "editor": "pgadmin"
        }
    
    def _split_sql(self, sql: str) -> List[str]:
        """Split SQL into individual statements"""
        # Simple split - could be enhanced for complex cases
        statements = []
        current = ""
        in_string = False
        in_dollar_quote = False
        
        i = 0
        while i < len(sql):
            char = sql[i]
            
            # Handle dollar quoting
            if char == '$' and not in_string:
                # Check for dollar quote start/end
                match_end = sql.find('$', i + 1)
                if match_end > i:
                    tag = sql[i:match_end + 1]
                    if not in_dollar_quote:
                        in_dollar_quote = True
                    elif sql[i:].startswith(tag):
                        in_dollar_quote = False
            
            # Handle string
            if char == "'" and not in_dollar_quote:
                in_string = not in_string
            
            # Split on semicolon outside strings
            if char == ';' and not in_string and not in_dollar_quote:
                statements.append(current.strip())
                current = ""
            else:
                current += char
            
            i += 1
        
        if current.strip():
            statements.append(current.strip())
        
        return statements
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point"""
    server = PostgreSQLMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
