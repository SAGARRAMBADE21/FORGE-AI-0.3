"""MCP stub - placeholder for Model Context Protocol support."""

# Stub classes to prevent import errors when mcp package is not installed

class Server:
    """Stub MCP Server class"""
    pass

class Tool:
    """Stub Tool class"""
    pass

class TextContent:
    """Stub TextContent class"""
    pass

class Resource:
    """Stub Resource class"""
    pass

class ResourceTemplate:
    """Stub ResourceTemplate class"""
    pass

def stdio_server():
    """Stub stdio_server function"""
    pass

# Export types
types = type('types', (), {
    'Tool': Tool,
    'TextContent': TextContent,
    'Resource': Resource,
    'ResourceTemplate': ResourceTemplate
})()

# Export server
server = type('server', (), {
    'Server': Server,
    'stdio': type('stdio', (), {'stdio_server': stdio_server})()
})()
