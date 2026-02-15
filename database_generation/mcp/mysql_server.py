# MySQL MCP server
"""
MySQL MCP Server
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Sequence

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    mysql = None

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource
except ImportError:
    from database_generation.mcp_stub import Server, Tool, TextContent, Resource, stdio_server


class MySQLMCPServer:
    """MCP Server for MySQL database operations"""
    
    def __init__(self):
        self.server = Server("forge-mysql-mcp")
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
                    description="Connect to a MySQL database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string"},
                            "port": {"type": "integer", "default": 3306},
                            "database": {"type": "string"},
                            "user": {"type": "string"},
                            "password": {"type": "string"},
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
                            "sql": {"type": "string"},
                            "disable_fk_checks": {"type": "boolean", "default": True}
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
                            "sql": {"type": "string"},
                            "params": {"type": "array"}
                        },
                        "required": ["sql"]
                    }
                ),
                Tool(
                    name="get_schema_info",
                    description="Get database schema information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "database": {"type": "string"}
                        }
                    }
                ),
                Tool(
                    name="export_for_workbench",
                    description="Format SQL for MySQL Workbench",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string"}
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
                elif name == "export_for_workbench":
                    result = await self._export_for_workbench(arguments)
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
                
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    async def _connect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to MySQL database"""
        if mysql is None:
            return {"success": False, "error": "mysql-connector-python not installed"}
        
        try:
            self.connection_params = {
                "host": args["host"],
                "port": args.get("port", 3306),
                "database": args["database"],
                "user": args["user"],
                "password": args["password"]
            }
            
            self.connection = mysql.connector.connect(**self.connection_params)
            
            cursor = self.connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            
            return {
                "success": True,
                "message": "Connected successfully",
                "database": args["database"],
                "version": version
            }
            
        except MySQLError as e:
            return {"success": False, "error": str(e)}
    
    async def _disconnect(self) -> Dict[str, Any]:
        """Disconnect from database"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
            return {"success": True, "message": "Disconnected"}
        return {"success": True, "message": "Not connected"}
    
    async def _execute_schema(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute schema DDL"""
        if not self.connection or not self.connection.is_connected():
            return {"success": False, "error": "Not connected to database"}
        
        sql = args["sql"]
        disable_fk_checks = args.get("disable_fk_checks", True)
        
        try:
            cursor = self.connection.cursor()
            
            if disable_fk_checks:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            # Execute each statement
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            
            if disable_fk_checks:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            self.connection.commit()
            cursor.close()
            
            return {"success": True, "message": "Schema executed successfully"}
            
        except MySQLError as e:
            self.connection.rollback()
            return {"success": False, "error": str(e)}
    
    async def _execute_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a SQL query"""
        if not self.connection or not self.connection.is_connected():
            return {"success": False, "error": "Not connected to database"}
        
        sql = args["sql"]
        params = args.get("params", [])
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            
            if cursor.description:
                rows = cursor.fetchall()
                result = {
                    "success": True,
                    "rows": rows,
                    "rowcount": len(rows)
                }
            else:
                self.connection.commit()
                result = {
                    "success": True,
                    "rowcount": cursor.rowcount
                }
            
            cursor.close()
            return result
            
        except MySQLError as e:
            return {"success": False, "error": str(e)}
    
    async def _get_schema_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get database schema information"""
        if not self.connection or not self.connection.is_connected():
            return {"success": False, "error": "Not connected to database"}
        
        database = args.get("database") or self.connection_params.get("database")
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Get tables
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_ROWS, ENGINE, TABLE_COMMENT
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
            """, (database,))
            
            tables = []
            for table in cursor.fetchall():
                # Get columns
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, 
                           COLUMN_DEFAULT, COLUMN_KEY, EXTRA
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (database, table["TABLE_NAME"]))
                
                columns = cursor.fetchall()
                
                tables.append({
                    "name": table["TABLE_NAME"],
                    "rows": table["TABLE_ROWS"],
                    "engine": table["ENGINE"],
                    "comment": table["TABLE_COMMENT"],
                    "columns": columns
                })
            
            cursor.close()
            
            return {
                "success": True,
                "database": database,
                "tables": tables
            }
            
        except MySQLError as e:
            return {"success": False, "error": str(e)}
    
    async def _export_for_workbench(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Format SQL for MySQL Workbench"""
        sql = args["sql"]
        
        formatted = f"""-- =============================================
-- MySQL Workbench Export
-- Generated by FORGE MCP Server
-- =============================================

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL';

{sql}

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
"""
        
        return {
            "success": True,
            "formatted_sql": formatted,
            "editor": "mysql_workbench"
        }
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    server = MySQLMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()