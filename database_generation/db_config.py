# Configuration
"""
FORGE Configuration
"""

import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class AIConfig(BaseModel):
    """AI configuration"""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    max_tokens: int = 8192
    temperature: float = 0.3


class MCPConfig(BaseModel):
    """MCP server configuration"""
    postgres_enabled: bool = True
    mysql_enabled: bool = True
    mongodb_enabled: bool = True


class ForgeConfig(BaseModel):
    """Main configuration"""
    ai: AIConfig = AIConfig()
    mcp: MCPConfig = MCPConfig()
    output_dir: str = "./output"
    
    @classmethod
    def load(cls) -> "ForgeConfig":
        return cls(
            ai=AIConfig(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model=os.getenv("FORGE_MODEL", "gpt-4o-mini"),
            ),
            output_dir=os.getenv("FORGE_OUTPUT_DIR", "./output")
        )


config = ForgeConfig.load()