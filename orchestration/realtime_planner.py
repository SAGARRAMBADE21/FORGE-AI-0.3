"""
Real-Time Intelligent Fullstack Planner.

LLM-powered planner that dynamically discovers and plans backend components
with streaming output and interactive modification - like Antigravity.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from generation.llm_generator import LLMGenerator

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PLAN DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class PlannedModel:
    """A model discovered from frontend analysis."""
    name: str
    fields: list[dict] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {"name": self.name, "fields": self.fields, "relationships": self.relationships}


@dataclass
class PlannedEndpoint:
    """An API endpoint to be generated."""
    method: str
    path: str
    description: str
    request_body: Optional[dict] = None
    response_type: str = "json"
    auth_required: bool = False
    
    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "path": self.path,
            "description": self.description,
            "auth_required": self.auth_required
        }


@dataclass
class PlannedMiddleware:
    """Middleware to be added."""
    name: str
    description: str
    config: dict = field(default_factory=dict)


@dataclass
class FullstackPlan:
    """Complete fullstack generation plan."""
    models: list[PlannedModel] = field(default_factory=list)
    endpoints: list[PlannedEndpoint] = field(default_factory=list)
    middleware: list[PlannedMiddleware] = field(default_factory=list)
    database_type: str = "postgresql"
    backend_framework: str = "fastapi"
    auth_type: Optional[str] = None
    estimated_files: int = 0
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "models": [m.to_dict() for m in self.models],
            "endpoints": [e.to_dict() for e in self.endpoints],
            "middleware": [{"name": m.name, "description": m.description} for m in self.middleware],
            "database_type": self.database_type,
            "backend_framework": self.backend_framework,
            "auth_type": self.auth_type,
            "estimated_files": self.estimated_files,
            "warnings": self.warnings,
        }


# ═══════════════════════════════════════════════════════════════════════════
# PLANNER PROMPTS
# ═══════════════════════════════════════════════════════════════════════════

PLANNING_SYSTEM_PROMPT = """You are an expert fullstack development team planner. 
Analyze the frontend code and create a comprehensive backend plan.

Your task is to discover and plan:
1. **Core domain data models only** (e.g., User, Product, Order, Todo)
   - DO NOT include UI types like FormData, Props, State, Context, Config
   - Focus on entities that will be stored in the database
2. API endpoints (CRUD + custom)
3. Authentication requirements
4. Middleware needs
5. Database schema considerations

IMPORTANT: Ignore TypeScript types used only for UI/forms like:
- *FormData, *Form, *Schema (form validation)
- *Context, *ContextType (React context)
- *Props, *State (component props/state)
- *Filter, *Config (UI configuration)
- *Toast, *Action, *Event (UI interactions)

Output each discovery on a new line in this format:
[MODEL] ModelName: field1:type, field2:type | relations: RelatedModel
[ENDPOINT] METHOD /path - description | auth:yes/no
[AUTH] type - description
[MIDDLEWARE] name - description
[WARNING] message

Be thorough but concise. Think like a professional development team focusing on CORE BUSINESS ENTITIES."""

ADDITION_SYSTEM_PROMPT = """You are a fullstack planner. The user wants to add a component to their backend plan.

Based on their request, output the additions in this format:
[MODEL] ModelName: field1:type, field2:type
[ENDPOINT] METHOD /path - description | auth:yes/no
[MIDDLEWARE] name - description
[CONFIG] key=value

Keep additions focused and relevant to the request."""


# ═══════════════════════════════════════════════════════════════════════════
# REALTIME PLANNER
# ═══════════════════════════════════════════════════════════════════════════


class RealtimePlanner:
    """
    LLM-powered real-time planning like Antigravity.
    
    Features:
    - Streaming discovery of components
    - Dynamic addition via user requests
    - Interactive modification before generation
    """
    
    def __init__(
        self,
        frontend_path: Path,
        config: dict,
        llm: Optional[LLMGenerator] = None,
    ):
        self.frontend_path = Path(frontend_path)
        self.config = config
        self.llm = llm or LLMGenerator()
        self.plan = FullstackPlan(
            database_type=config.get("database", "postgresql"),
            backend_framework=config.get("framework", "fastapi"),
        )
        
    async def create_plan_streaming(
        self,
        callback: Callable[[str, str, Any], None] = None,
    ) -> FullstackPlan:
        """
        Create plan with streaming output.
        
        Args:
            callback: Called for each discovery - callback(type, message, data)
                      type: "model", "endpoint", "auth", "middleware", "warning", "status"
        """
        if callback:
            callback("status", "Analyzing frontend structure...", None)
        
        # Gather frontend context
        frontend_context = await self._gather_frontend_context()
        
        if callback:
            callback("status", "Planning backend components...", None)
        
        # Create planning prompt
        user_prompt = f"""Analyze this frontend code and plan the backend:

Frontend Framework: {frontend_context.get('framework', 'unknown')}
Database Target: {self.plan.database_type}
Backend Framework: {self.plan.backend_framework}

Key Files Found:
{frontend_context.get('file_summary', 'No files analyzed')}

API Calls Detected:
{frontend_context.get('api_calls', 'None detected')}

Data Structures Found:
{frontend_context.get('data_structures', 'None detected')}

Create a comprehensive backend plan. Output each component as you discover it."""

        # Generate plan (non-streaming for now, parse incrementally)
        try:
            response = await self.llm.generate(
                system_prompt=PLANNING_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            
            # Parse response line by line
            await self._parse_plan_response(response, callback)
            
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            if callback:
                callback("warning", f"LLM error: {str(e)}", None)
        
        # Calculate estimates
        self._calculate_estimates()
        
        return self.plan
    
    async def add_component(
        self,
        request: str,
        callback: Callable[[str, str, Any], None] = None,
    ) -> None:
        """
        Dynamically add component based on user request.
        
        Examples:
            "add rate limiting"
            "add caching with Redis"
            "add file upload for products"
        """
        if callback:
            callback("status", f"Planning: {request}", None)
        
        # Current plan context
        current_models = ", ".join(m.name for m in self.plan.models) or "none"
        current_endpoints = len(self.plan.endpoints)
        
        user_prompt = f"""Current plan has: {current_models} models, {current_endpoints} endpoints, {self.plan.backend_framework} framework.

User request: {request}

Add the necessary components for this feature."""

        try:
            response = await self.llm.generate(
                system_prompt=ADDITION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            
            await self._parse_plan_response(response, callback)
            self._calculate_estimates()
            
        except Exception as e:
            logger.error(f"Component addition failed: {e}")
            if callback:
                callback("warning", f"Failed to add: {str(e)}", None)
    
    async def modify_plan(
        self,
        modification: str,
        callback: Callable[[str, str, Any], None] = None,
    ) -> None:
        """Modify existing plan based on feedback."""
        # For now, treat modifications as additions
        await self.add_component(modification, callback)
    
    async def _gather_frontend_context(self) -> dict:
        """Gather context from frontend files with multiple detection methods."""
        context = {
            "framework": "unknown",
            "file_summary": "",
            "api_calls": "",
            "data_structures": "",
            "zod_models": "",
            "ast_models": "",
        }
        
        try:
            # Method 1: TypeScript AST Analysis (highest accuracy ~95%)
            try:
                from analyzers.typescript_ast_analyzer import TypeScriptASTAnalyzer
                ast_analyzer = TypeScriptASTAnalyzer(self.frontend_path)
                ast_models = ast_analyzer.extract_domain_models()
                
                if ast_models:
                    ast_model_names = [m["name"] for m in ast_models]
                    context["ast_models"] = ", ".join(ast_model_names[:15])
                    logger.info(f"Found {len(ast_models)} domain models via AST: {ast_model_names}")
                    
                    # If AST found models, trust it and skip other methods
                    if len(ast_models) >= 1:
                        context["data_structures"] = context["ast_models"]
                        return context
            except Exception as e:
                logger.debug(f"AST analysis unavailable: {e}")
            
            # Method 2: Extract from Zod schemas (preferred for modern React apps)
            try:
                from analyzers.zod_schema_extractor import ZodSchemaExtractor
                zod_extractor = ZodSchemaExtractor(self.frontend_path)
                zod_schemas = zod_extractor.extract_schemas()
                
                if zod_schemas:
                    zod_model_names = [s["name"] for s in zod_schemas]
                    context["zod_models"] = ", ".join(zod_model_names[:10])
                    logger.info(f"Found {len(zod_schemas)} Zod schemas: {zod_model_names}")
                    
                    # If Zod found models, use them
                    if len(zod_schemas) >= 1:
                        context["data_structures"] = context["zod_models"]
            except Exception as e:
                logger.debug(f"Zod extraction unavailable: {e}")
            
            # Method 3: Regex fallback (scan TypeScript files with file-path aware filtering)
            files_found = []
            api_patterns = []
            type_patterns = []
            
            # Common frontend file patterns
            extensions = [".tsx", ".ts", ".jsx", ".js", ".vue", ".svelte"]
            
            for ext in extensions:
                for file_path in self.frontend_path.rglob(f"*{ext}"):
                    # Skip node_modules
                    if "node_modules" in str(file_path):
                        continue
                    
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        rel_path = file_path.relative_to(self.frontend_path)
                        files_found.append(str(rel_path))
                        
                        # Detect framework
                        if "react" in content.lower() or "useState" in content:
                            context["framework"] = "React"
                        elif "vue" in content.lower():
                            context["framework"] = "Vue"
                        elif "angular" in content.lower():
                            context["framework"] = "Angular"
                        
                        # Find API calls
                        api_matches = re.findall(
                            r'(fetch|axios|api)\s*[\.\(]\s*[\'"`]([^\'"`]+)[\'"`]',
                            content, re.IGNORECASE
                        )
                        for _, endpoint in api_matches:
                            if endpoint not in api_patterns:
                                api_patterns.append(endpoint)
                        
                        # Find TypeScript interfaces/types (only if not already found via AST/Zod)
                        if not context["data_structures"]:
                            from utils.domain_model_filter import is_domain_model
                            
                            type_matches = re.findall(
                                r'(?:interface|type)\s+(\w+)\s*[{=]',
                                content
                            )
                            for t in type_matches:
                                # Pass file path for location-aware filtering
                                if t not in type_patterns and not t.startswith("_") and is_domain_model(t, str(rel_path)):
                                    type_patterns.append(t)
                        
                    except Exception:
                        continue
            
            # Build context strings
            context["file_summary"] = "\n".join(files_found[:20])
            if len(files_found) > 20:
                context["file_summary"] += f"\n... and {len(files_found) - 20} more files"
            
            context["api_calls"] = "\n".join(api_patterns[:15]) or "No explicit API calls found"
            
            # Use regex types only if no AST/Zod models found
            if not context["data_structures"]:
                context["data_structures"] = ", ".join(type_patterns[:10]) or "No explicit types found"
            
        except Exception as e:
            logger.warning(f"Failed to gather frontend context: {e}")
        
        return context
    
    async def _parse_plan_response(
        self,
        response: str,
        callback: Callable[[str, str, Any], None] = None,
    ) -> None:
        """Parse LLM response and update plan."""
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            
            try:
                if line.startswith("[MODEL]"):
                    model = self._parse_model_line(line)
                    if model and not any(m.name == model.name for m in self.plan.models):
                        self.plan.models.append(model)
                        if callback:
                            fields_str = ", ".join(f["name"] for f in model.fields[:3])
                            callback("model", f"{model.name} ({fields_str})", model)
                
                elif line.startswith("[ENDPOINT]"):
                    endpoint = self._parse_endpoint_line(line)
                    if endpoint:
                        self.plan.endpoints.append(endpoint)
                        if callback:
                            callback("endpoint", f"{endpoint.method} {endpoint.path}", endpoint)
                
                elif line.startswith("[AUTH]"):
                    auth_type = line.replace("[AUTH]", "").strip().split("-")[0].strip()
                    self.plan.auth_type = auth_type
                    if callback:
                        callback("auth", f"{auth_type} authentication", None)
                
                elif line.startswith("[MIDDLEWARE]"):
                    mw = self._parse_middleware_line(line)
                    if mw and not any(m.name == mw.name for m in self.plan.middleware):
                        self.plan.middleware.append(mw)
                        if callback:
                            callback("middleware", f"{mw.name}", mw)
                
                elif line.startswith("[WARNING]"):
                    warning = line.replace("[WARNING]", "").strip()
                    if warning not in self.plan.warnings:
                        self.plan.warnings.append(warning)
                        if callback:
                            callback("warning", warning, None)
                            
            except Exception as e:
                logger.debug(f"Failed to parse line: {line} - {e}")
    
    def _parse_model_line(self, line: str) -> Optional[PlannedModel]:
        """Parse [MODEL] line into PlannedModel."""
        try:
            content = line.replace("[MODEL]", "").strip()
            
            # Split name and fields
            if ":" not in content:
                return PlannedModel(name=content.split()[0])
            
            name_part, rest = content.split(":", 1)
            name = name_part.strip()
            
            # Parse fields and relations
            fields = []
            relationships = []
            
            if "|" in rest:
                fields_part, rel_part = rest.split("|", 1)
            else:
                fields_part = rest
                rel_part = ""
            
            # Parse fields
            for field_def in fields_part.split(","):
                field_def = field_def.strip()
                if ":" in field_def:
                    fname, ftype = field_def.split(":", 1)
                    fields.append({"name": fname.strip(), "type": ftype.strip()})
                elif field_def:
                    fields.append({"name": field_def, "type": "string"})
            
            # Parse relations
            if "relations:" in rel_part.lower():
                rel_content = rel_part.lower().split("relations:")[-1]
                relationships = [r.strip() for r in rel_content.split(",") if r.strip()]
            
            return PlannedModel(name=name, fields=fields, relationships=relationships)
            
        except Exception as e:
            logger.debug(f"Model parse error: {e}")
            return None
    
    def _parse_endpoint_line(self, line: str) -> Optional[PlannedEndpoint]:
        """Parse [ENDPOINT] line into PlannedEndpoint."""
        try:
            content = line.replace("[ENDPOINT]", "").strip()
            
            # Extract method and path
            parts = content.split()
            if len(parts) < 2:
                return None
            
            method = parts[0].upper()
            path = parts[1]
            
            # Extract description
            description = ""
            if "-" in content:
                description = content.split("-", 1)[1].strip()
                if "|" in description:
                    description = description.split("|")[0].strip()
            
            # Check auth
            auth_required = "auth:yes" in content.lower()
            
            return PlannedEndpoint(
                method=method,
                path=path,
                description=description,
                auth_required=auth_required,
            )
            
        except Exception as e:
            logger.debug(f"Endpoint parse error: {e}")
            return None
    
    def _parse_middleware_line(self, line: str) -> Optional[PlannedMiddleware]:
        """Parse [MIDDLEWARE] line into PlannedMiddleware."""
        try:
            content = line.replace("[MIDDLEWARE]", "").strip()
            
            if "-" in content:
                name, description = content.split("-", 1)
            else:
                name = content
                description = ""
            
            return PlannedMiddleware(
                name=name.strip(),
                description=description.strip(),
            )
            
        except Exception as e:
            logger.debug(f"Middleware parse error: {e}")
            return None
    
    def _calculate_estimates(self) -> None:
        """Calculate estimated file counts."""
        # Base files (main.py, database.py, etc.)
        base_files = 5
        
        # Per model: model file, route file, service file
        model_files = len(self.plan.models) * 3
        
        # Auth files
        auth_files = 3 if self.plan.auth_type else 0
        
        # Middleware files
        middleware_files = len(self.plan.middleware)
        
        self.plan.estimated_files = base_files + model_files + auth_files + middleware_files
    
    def get_plan_summary(self) -> str:
        """Get a text summary of the plan."""
        lines = [
            f"Models: {len(self.plan.models)}",
            f"Endpoints: {len(self.plan.endpoints)}",
            f"Middleware: {len(self.plan.middleware)}",
            f"Auth: {self.plan.auth_type or 'None'}",
            f"Database: {self.plan.database_type}",
            f"Framework: {self.plan.backend_framework}",
            f"Est. Files: ~{self.plan.estimated_files}",
        ]
        return "\n".join(lines)
