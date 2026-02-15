"""
Task Chat - Antigravity-style task execution via chat.

Enables users to execute backend development tasks through
natural language and slash commands in an interactive chat.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from generation.llm_generator import LLMGenerator

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════


class TaskType(str, Enum):
    """Types of tasks that can be executed."""
    GENERATE = "generate"
    ADD_ENDPOINT = "add_endpoint"
    ADD_MODEL = "add_model"
    ADD_AUTH = "add_auth"
    SEARCH = "search"
    EDIT = "edit"
    CHAT = "chat"  # General chat, not a task


@dataclass
class TaskResult:
    """Result of a task execution."""
    success: bool
    message: str
    files_created: int = 0
    files_modified: int = 0
    data: dict = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Response from the chat system."""
    message: str
    is_task: bool = False
    task_type: Optional[TaskType] = None
    task_result: Optional[TaskResult] = None


# ═══════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════════

INTENT_ROUTER_PROMPT = """You are a task router for a backend development assistant.
Analyze the user's message and determine what they want to do.

Classify the intent into one of:
- GENERATE: Generate full backend from frontend (keywords: generate, create backend, fullstack)
- ADD_ENDPOINT: Add a new API endpoint (keywords: add endpoint, create route, new api)
- ADD_MODEL: Add a new data model (keywords: add model, new entity, create table)
- ADD_AUTH: Add authentication (keywords: add auth, authentication, login, jwt)
- SEARCH: Search the codebase (keywords: find, search, where is, locate)
- EDIT: Modify existing code (keywords: change, update, modify, fix, edit)
- CHAT: General question or conversation

Respond with ONLY the intent name (GENERATE, ADD_ENDPOINT, ADD_MODEL, ADD_AUTH, SEARCH, EDIT, or CHAT).
Include any extracted parameters after a | separator.

Examples:
User: "generate backend from ./frontend"
Response: GENERATE|path=./frontend

User: "add a POST endpoint for /products/import"
Response: ADD_ENDPOINT|method=POST,path=/products/import

User: "what does the auth middleware do?"
Response: CHAT

User: "add rate limiting to the API"
Response: EDIT|request=add rate limiting to the API
"""


# ═══════════════════════════════════════════════════════════════════════════
# TASK CHAT
# ═══════════════════════════════════════════════════════════════════════════


class TaskChat:
    """
    Antigravity-style task execution via chat.
    
    Features:
    - Slash command shortcuts (/generate, /add endpoint, etc.)
    - Natural language intent routing
    - Task planning with user approval
    - Progress callbacks for live updates
    """
    
    # Available slash commands
    COMMANDS = {
        "/generate": ("Generate backend from frontend", TaskType.GENERATE),
        "/add endpoint": ("Add new API endpoint", TaskType.ADD_ENDPOINT),
        "/add model": ("Add new data model", TaskType.ADD_MODEL),
        "/add auth": ("Add authentication", TaskType.ADD_AUTH),
        "/search": ("Search codebase", TaskType.SEARCH),
        "/edit": ("Edit code", TaskType.EDIT),
        "/help": ("Show available commands", None),
    }
    
    def __init__(
        self,
        project_path: Path,
        llm: Optional[LLMGenerator] = None,
        agent=None,  # FullStackAgent for operations
    ):
        self.project_path = Path(project_path)
        self.llm = llm or LLMGenerator()
        self.agent = agent
        self.history = []
        
    async def process(
        self,
        message: str,
        callback: Callable[[str, str, Any], None] = None,
    ) -> ChatResponse:
        """
        Process user message and route to appropriate handler.
        
        Args:
            message: User's input message
            callback: Progress callback - callback(type, message, data)
                      type: "status", "step", "result", "error"
        """
        message = message.strip()
        
        # Handle slash commands first
        if message.startswith("/"):
            return await self._handle_slash_command(message, callback)
        
        # Route natural language to intent
        intent, params = await self._route_intent(message)
        
        if intent == TaskType.CHAT:
            # General chat - pass to agent or respond directly
            return await self._handle_chat(message, callback)
        else:
            # Task execution
            return await self._execute_task(intent, params, message, callback)
    
    async def _handle_slash_command(
        self,
        message: str,
        callback: Callable = None,
    ) -> ChatResponse:
        """Handle slash commands."""
        lower_msg = message.lower()
        
        # Help command
        if lower_msg == "/help":
            return self._generate_help_response()
        
        # Match commands
        for cmd, (description, task_type) in self.COMMANDS.items():
            if lower_msg.startswith(cmd):
                if task_type is None:
                    continue
                    
                # Extract args after command
                args = message[len(cmd):].strip()
                params = {"args": args, "raw": message}
                
                return await self._execute_task(task_type, params, message, callback)
        
        # Unknown command
        return ChatResponse(
            message=f"Unknown command: {message.split()[0]}\nUse /help to see available commands.",
            is_task=False,
        )
    
    async def _route_intent(self, message: str) -> tuple[TaskType, dict]:
        """Use LLM to route natural language to intent."""
        try:
            response = await self.llm.generate(
                system_prompt=INTENT_ROUTER_PROMPT,
                user_prompt=message,
            )
            
            # Parse response
            parts = response.strip().split("|")
            intent_str = parts[0].strip().upper()
            
            # Parse parameters
            params = {"raw": message}
            if len(parts) > 1:
                param_str = parts[1]
                for pair in param_str.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        params[key.strip()] = value.strip()
            
            # Map to TaskType
            intent_map = {
                "GENERATE": TaskType.GENERATE,
                "ADD_ENDPOINT": TaskType.ADD_ENDPOINT,
                "ADD_MODEL": TaskType.ADD_MODEL,
                "ADD_AUTH": TaskType.ADD_AUTH,
                "SEARCH": TaskType.SEARCH,
                "EDIT": TaskType.EDIT,
                "CHAT": TaskType.CHAT,
            }
            
            intent = intent_map.get(intent_str, TaskType.CHAT)
            return intent, params
            
        except Exception as e:
            logger.warning(f"Intent routing failed: {e}")
            return TaskType.CHAT, {"raw": message}
    
    async def _execute_task(
        self,
        task_type: TaskType,
        params: dict,
        original_message: str,
        callback: Callable = None,
    ) -> ChatResponse:
        """Execute a task based on type."""
        
        if callback:
            callback("status", f"Starting {task_type.value} task...", None)
        
        try:
            if task_type == TaskType.GENERATE:
                result = await self._task_generate(params, callback)
            elif task_type == TaskType.ADD_ENDPOINT:
                result = await self._task_add_endpoint(params, callback)
            elif task_type == TaskType.ADD_MODEL:
                result = await self._task_add_model(params, callback)
            elif task_type == TaskType.ADD_AUTH:
                result = await self._task_add_auth(params, callback)
            elif task_type == TaskType.SEARCH:
                result = await self._task_search(params, callback)
            elif task_type == TaskType.EDIT:
                result = await self._task_edit(params, callback)
            else:
                result = TaskResult(
                    success=False,
                    message=f"Unknown task type: {task_type}",
                )
            
            return ChatResponse(
                message=result.message,
                is_task=True,
                task_type=task_type,
                task_result=result,
            )
            
        except Exception as e:
            logger.exception(f"Task execution failed: {e}")
            if callback:
                callback("error", str(e), None)
            return ChatResponse(
                message=f"Task failed: {str(e)}",
                is_task=True,
                task_type=task_type,
                task_result=TaskResult(success=False, message=str(e)),
            )
    
    async def _handle_chat(
        self,
        message: str,
        callback: Callable = None,
    ) -> ChatResponse:
        """Handle general chat/questions."""
        if self.agent:
            try:
                response = await self.agent.chat(message)
                return ChatResponse(
                    message=response.get("response", "I couldn't process that request."),
                    is_task=False,
                )
            except Exception as e:
                logger.warning(f"Agent chat failed: {e}")
        
        # Fallback response
        return ChatResponse(
            message="I can help with backend development tasks. Try /help to see available commands.",
            is_task=False,
        )
    
    def _generate_help_response(self) -> ChatResponse:
        """Generate help message."""
        lines = ["**Available Commands:**\n"]
        for cmd, (description, _) in self.COMMANDS.items():
            lines.append(f"  `{cmd}` - {description}")
        lines.append("\n**Or use natural language:**")
        lines.append('  "generate backend from ./frontend"')
        lines.append('  "add endpoint POST /products/import"')
        lines.append('  "add rate limiting to all endpoints"')
        
        return ChatResponse(message="\n".join(lines), is_task=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # TASK IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _task_generate(self, params: dict, callback: Callable = None) -> TaskResult:
        """Generate backend from frontend."""
        from orchestration.realtime_planner import RealtimePlanner
        
        frontend_path = params.get("args") or params.get("path", ".")
        frontend_path = Path(frontend_path)
        
        if not frontend_path.exists():
            return TaskResult(
                success=False,
                message=f"Frontend path not found: {frontend_path}",
            )
        
        if callback:
            callback("status", "Analyzing frontend...", None)
        
        # Use realtime planner
        config = {"database": "postgresql", "framework": "fastapi"}
        planner = RealtimePlanner(frontend_path, config, self.llm)
        
        # Create plan with streaming
        plan = await planner.create_plan_streaming(callback)
        
        return TaskResult(
            success=True,
            message=f"Plan created: {len(plan.models)} models, {len(plan.endpoints)} endpoints",
            data={"plan": plan.to_dict(), "needs_approval": True},
        )
    
    async def _task_add_endpoint(self, params: dict, callback: Callable = None) -> TaskResult:
        """Add new API endpoint."""
        args = params.get("args", "")
        method = params.get("method", "GET")
        path = params.get("path", "")
        
        # Parse from args if not in params
        if args and not path:
            parts = args.split()
            if len(parts) >= 2:
                method = parts[0].upper()
                path = parts[1]
            elif len(parts) == 1:
                path = parts[0]
        
        if not path:
            return TaskResult(
                success=False,
                message="Please specify endpoint path. Example: /add endpoint POST /products",
            )
        
        if callback:
            callback("step", f"Planning endpoint: {method} {path}", None)
        
        # Generate endpoint plan using LLM
        prompt = f"""Plan a new API endpoint:
Method: {method}
Path: {path}

Output the plan as:
[MODEL] ModelName if new model needed
[ENDPOINT] {method} {path} - description
[SERVICE] service function needed
"""
        
        try:
            response = await self.llm.generate(
                system_prompt="You are a backend developer. Plan the implementation.",
                user_prompt=prompt,
            )
            
            if callback:
                callback("result", f"✓ Planned: {method} {path}", None)
            
            return TaskResult(
                success=True,
                message=f"Endpoint planned: {method} {path}\n\n{response}",
                data={"method": method, "path": path, "plan": response, "needs_approval": True},
            )
            
        except Exception as e:
            return TaskResult(success=False, message=f"Planning failed: {e}")
    
    async def _task_add_model(self, params: dict, callback: Callable = None) -> TaskResult:
        """Add new data model."""
        args = params.get("args", "")
        model_name = args.split()[0] if args else None
        
        if not model_name:
            return TaskResult(
                success=False,
                message="Please specify model name. Example: /add model Product",
            )
        
        if callback:
            callback("step", f"Planning model: {model_name}", None)
        
        # Generate model plan using LLM
        prompt = f"""Plan a new data model:
Name: {model_name}
Context: {args}

Output:
[MODEL] {model_name}: field1:type, field2:type, ...
[ENDPOINT] CRUD endpoints for {model_name}
"""
        
        try:
            response = await self.llm.generate(
                system_prompt="You are a backend developer. Plan the model with sensible fields.",
                user_prompt=prompt,
            )
            
            if callback:
                callback("result", f"✓ Planned: {model_name} model", None)
            
            return TaskResult(
                success=True,
                message=f"Model planned: {model_name}\n\n{response}",
                data={"model_name": model_name, "plan": response, "needs_approval": True},
            )
            
        except Exception as e:
            return TaskResult(success=False, message=f"Planning failed: {e}")
    
    async def _task_add_auth(self, params: dict, callback: Callable = None) -> TaskResult:
        """Add authentication."""
        args = params.get("args", "jwt")
        auth_type = "JWT" if "jwt" in args.lower() else args.upper()
        
        if callback:
            callback("step", f"Planning {auth_type} authentication", None)
        
        plan_lines = [
            f"[AUTH] {auth_type} authentication",
            "[MODEL] User: email:string, password_hash:string, role:string",
            "[ENDPOINT] POST /auth/register - Register new user",
            "[ENDPOINT] POST /auth/login - Login and get tokens",
            "[ENDPOINT] POST /auth/refresh - Refresh access token",
            "[MIDDLEWARE] auth_required - Verify JWT tokens",
        ]
        
        if callback:
            for line in plan_lines:
                callback("step", line, None)
        
        return TaskResult(
            success=True,
            message=f"{auth_type} Authentication Plan:\n" + "\n".join(plan_lines),
            data={"auth_type": auth_type, "plan": plan_lines, "needs_approval": True},
        )
    
    async def _task_search(self, params: dict, callback: Callable = None) -> TaskResult:
        """Search the codebase."""
        query = params.get("args", params.get("raw", ""))
        
        if not query:
            return TaskResult(
                success=False,
                message="Please provide search query. Example: /search authentication",
            )
        
        if self.agent:
            if callback:
                callback("status", f"Searching: {query}", None)
            
            try:
                results = await self.agent.search(query, top_k=5)
                
                if results.results:
                    lines = [f"Found {len(results.results)} results:\n"]
                    for r in results.results:
                        lines.append(f"• **{r.file}** (score: {r.score:.2f})")
                        if r.snippet:
                            lines.append(f"  ```\n  {r.snippet[:100]}...\n  ```")
                    
                    return TaskResult(
                        success=True,
                        message="\n".join(lines),
                        data={"results": [r.__dict__ for r in results.results]},
                    )
                else:
                    return TaskResult(
                        success=True,
                        message=f"No results found for: {query}",
                    )
                    
            except Exception as e:
                return TaskResult(success=False, message=f"Search failed: {e}")
        
        return TaskResult(
            success=False,
            message="Search not available - agent not initialized",
        )
    
    async def _task_edit(self, params: dict, callback: Callable = None) -> TaskResult:
        """Edit code based on request."""
        request = params.get("args") or params.get("request") or params.get("raw", "")
        
        if not request:
            return TaskResult(
                success=False,
                message="Please describe what you want to edit.",
            )
        
        if callback:
            callback("status", f"Planning edit: {request[:50]}...", None)
        
        # Generate edit plan using LLM
        prompt = f"""Plan code modifications for this request:
{request}

Output:
[FILE] path/to/file.py - what changes needed
[CHANGE] description of each specific change
"""
        
        try:
            response = await self.llm.generate(
                system_prompt="You are a code editor. Plan specific file changes.",
                user_prompt=prompt,
            )
            
            if callback:
                callback("result", "Edit plan created", None)
            
            return TaskResult(
                success=True,
                message=f"Edit Plan:\n\n{response}",
                data={"request": request, "plan": response, "needs_approval": True},
            )
            
        except Exception as e:
            return TaskResult(success=False, message=f"Planning failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


def create_task_chat(project_path: Path, agent=None) -> TaskChat:
    """Create a TaskChat instance."""
    return TaskChat(project_path, agent=agent)
