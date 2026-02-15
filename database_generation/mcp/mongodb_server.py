# MongoDB MCP server
"""
MongoDB MCP Server
"""

import asyncio
import json
from typing import Any, Dict, List, Sequence

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:
    MongoClient = None

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    from database_generation.mcp_stub import Server, Tool, TextContent, stdio_server


class MongoDBMCPServer:
    """MCP Server for MongoDB database operations"""
    
    def __init__(self):
        self.server = Server("forge-mongodb-mcp")
        self.client = None
        self.db = None
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP request handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="connect_database",
                    description="Connect to MongoDB",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "uri": {"type": "string", "description": "MongoDB connection URI"},
                            "database": {"type": "string", "description": "Database name"},
                        },
                        "required": ["uri", "database"]
                    }
                ),
                Tool(
                    name="disconnect_database",
                    description="Disconnect from MongoDB",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="execute_schema",
                    description="Execute FORGE schema (create collections, validators, indexes)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schema": {
                                "type": "object",
                                "description": "Schema definition with collections"
                            }
                        },
                        "required": ["schema"]
                    }
                ),
                Tool(
                    name="create_collection",
                    description="Create a collection with validation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "validator": {"type": "object"},
                            "indexes": {"type": "array"}
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="get_schema_info",
                    description="Get database collections and schema info",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="execute_command",
                    description="Execute a MongoDB command",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "object"}
                        },
                        "required": ["command"]
                    }
                ),
                Tool(
                    name="export_for_compass",
                    description="Export schema for MongoDB Compass",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schema": {"type": "object"}
                        },
                        "required": ["schema"]
                    }
                ),
                Tool(
                    name="export_for_mongosh",
                    description="Export as mongosh script",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schema": {"type": "object"}
                        },
                        "required": ["schema"]
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
                elif name == "create_collection":
                    result = await self._create_collection(arguments)
                elif name == "get_schema_info":
                    result = await self._get_schema_info()
                elif name == "execute_command":
                    result = await self._execute_command(arguments)
                elif name == "export_for_compass":
                    result = await self._export_for_compass(arguments)
                elif name == "export_for_mongosh":
                    result = await self._export_for_mongosh(arguments)
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
                
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    async def _connect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to MongoDB"""
        if MongoClient is None:
            return {"success": False, "error": "pymongo not installed"}
        
        try:
            self.client = MongoClient(args["uri"])
            self.db = self.client[args["database"]]
            
            # Test connection
            server_info = self.client.server_info()
            
            return {
                "success": True,
                "message": "Connected successfully",
                "database": args["database"],
                "version": server_info.get("version")
            }
            
        except PyMongoError as e:
            return {"success": False, "error": str(e)}
    
    async def _disconnect(self) -> Dict[str, Any]:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            return {"success": True, "message": "Disconnected"}
        return {"success": True, "message": "Not connected"}
    
    async def _execute_schema(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute schema (create collections and indexes)"""
        if not self.db:
            return {"success": False, "error": "Not connected to database"}
        
        schema = args["schema"]
        results = []
        
        try:
            for collection in schema.get("collections", []):
                # Create collection with validator
                try:
                    self.db.create_collection(
                        collection["name"],
                        validator=collection.get("validator"),
                        validationLevel=collection.get("validationLevel", "moderate")
                    )
                    results.append({
                        "type": "create_collection",
                        "name": collection["name"],
                        "success": True
                    })
                except PyMongoError as e:
                    if "already exists" in str(e):
                        results.append({
                            "type": "create_collection",
                            "name": collection["name"],
                            "success": True,
                            "note": "Collection already exists"
                        })
                    else:
                        raise
                
                # Create indexes
                for index in collection.get("indexes", []):
                    self.db[collection["name"]].create_index(
                        list(index["keys"].items()),
                        **index.get("options", {})
                    )
                    results.append({
                        "type": "create_index",
                        "collection": collection["name"],
                        "keys": index["keys"],
                        "success": True
                    })
            
            return {
                "success": True,
                "message": "Schema executed successfully",
                "results": results
            }
            
        except PyMongoError as e:
            return {"success": False, "error": str(e), "completed": results}
    
    async def _create_collection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single collection"""
        if not self.db:
            return {"success": False, "error": "Not connected to database"}
        
        try:
            options = {}
            if args.get("validator"):
                options["validator"] = {"$jsonSchema": args["validator"]}
            
            self.db.create_collection(args["name"], **options)
            
            # Create indexes
            for index in args.get("indexes", []):
                self.db[args["name"]].create_index(
                    list(index["keys"].items()),
                    **index.get("options", {})
                )
            
            return {
                "success": True,
                "collection": args["name"],
                "indexes_created": len(args.get("indexes", []))
            }
            
        except PyMongoError as e:
            return {"success": False, "error": str(e)}
    
    async def _get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information"""
        if not self.db:
            return {"success": False, "error": "Not connected to database"}
        
        try:
            collections = []
            
            for coll_name in self.db.list_collection_names():
                coll_info = self.db.command("listCollections", filter={"name": coll_name})
                indexes = list(self.db[coll_name].list_indexes())
                stats = self.db.command("collStats", coll_name)
                
                collections.append({
                    "name": coll_name,
                    "options": coll_info["cursor"]["firstBatch"][0].get("options", {}),
                    "indexes": indexes,
                    "document_count": stats.get("count", 0),
                    "size": stats.get("size", 0)
                })
            
            return {
                "success": True,
                "database": self.db.name,
                "collections": collections
            }
            
        except PyMongoError as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a MongoDB command"""
        if not self.db:
            return {"success": False, "error": "Not connected to database"}
        
        try:
            result = self.db.command(args["command"])
            return {"success": True, "result": result}
        except PyMongoError as e:
            return {"success": False, "error": str(e)}
    
    async def _export_for_compass(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Export schema for MongoDB Compass"""
        schema = args["schema"]
        
        # Compass prefers JSON schema format
        compass_format = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "databases": [{
                "name": schema.get("database", "forge_db"),
                "collections": [
                    {
                        "name": coll["name"],
                        "schema": coll.get("validator", {}).get("$jsonSchema", {}),
                        "indexes": coll.get("indexes", [])
                    }
                    for coll in schema.get("collections", [])
                ]
            }]
        }
        
        return {
            "success": True,
            "format": compass_format,
            "editor": "mongodb_compass"
        }
    
    async def _export_for_mongosh(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Export as mongosh script"""
        schema = args["schema"]
        db_name = schema.get("database", "forge_db")
        
        lines = [
            "// =============================================",
            "// FORGE MongoDB Schema",
            "// Generated by FORGE MCP Server",
            "// =============================================",
            "",
            f"use {db_name};",
            ""
        ]
        
        for coll in schema.get("collections", []):
            lines.append(f"// Collection: {coll['name']}")
            
            validator_json = json.dumps(coll.get("validator", {}), indent=2)
            lines.append(f"""db.createCollection("{coll['name']}", {{
  validator: {validator_json},
  validationLevel: "{coll.get('validationLevel', 'moderate')}"
}});
""")
            
            for index in coll.get("indexes", []):
                keys_json = json.dumps(index["keys"])
                options_json = json.dumps(index.get("options", {}))
                lines.append(f'db.{coll["name"]}.createIndex({keys_json}, {options_json});')
            
            lines.append("")
        
        lines.append('print("FORGE schema applied successfully");')
        
        return {
            "success": True,
            "script": "\n".join(lines),
            "editor": "mongosh"
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
    server = MongoDBMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()