"""Agentic loop for autonomous code editing.

This module provides Claude Code-style autonomous editing capabilities
where users can edit generated code through natural language commands.
"""

import asyncio
import logging
import os
import subprocess
import difflib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.prompt import Confirm

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# TYPES
# ═══════════════════════════════════════════════════════════════════════════


class ActionType(str, Enum):
    """Types of actions the agent can perform."""
    EDIT_FILE = "edit_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    READ_FILE = "read_file"
    RUN_COMMAND = "run_command"
    SEARCH_CODE = "search_code"


class ActionStatus(str, Enum):
    """Status of an action."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class FileEdit:
    """A single file edit operation."""
    search: str
    replace: str
    description: str = ""


@dataclass
class Action:
    """An action to be performed by the agent."""
    type: ActionType
    params: dict
    description: str
    status: ActionStatus = ActionStatus.PENDING
    result: Any = None
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResponse:
    """Response from the agentic loop."""
    message: str
    actions: list[Action] = field(default_factory=list)
    thinking: str = ""
    success: bool = True


@dataclass
class CommandResult:
    """Result of running a command."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    success: bool


# ═══════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════


AGENTIC_TOOLS = [
    {
        "name": "edit_file",
        "description": "Edit an existing file by replacing text. Use search/replace pairs.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root"
                },
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "search": {"type": "string", "description": "Text to find"},
                            "replace": {"type": "string", "description": "Text to replace with"}
                        }
                    },
                    "description": "List of search/replace pairs"
                },
                "description": {
                    "type": "string",
                    "description": "What this edit does"
                }
            },
            "required": ["path", "edits"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a new file with the specified content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root"
                },
                "content": {
                    "type": "string",
                    "description": "File contents"
                },
                "description": {
                    "type": "string",
                    "description": "What this file does"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this file should be deleted"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a terminal command. Requires user approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to run"
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory (defaults to project root)"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "search_code",
        "description": "Search the codebase for relevant code.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional file pattern to filter (e.g., '*.ts')"
                }
            },
            "required": ["query"]
        }
    }
]


# ═══════════════════════════════════════════════════════════════════════════
# AGENTIC LOOP
# ═══════════════════════════════════════════════════════════════════════════


class AgenticLoop:
    """
    Autonomous code editing loop.
    
    Provides Claude Code-style capabilities for editing generated backend
    code through natural language commands.
    """
    
    def __init__(
        self,
        project_path: Path,
        console: Console,
        llm_generator=None,
        agent=None,
    ):
        self.project_path = Path(project_path).resolve()
        self.console = console
        self.llm_generator = llm_generator
        self.agent = agent
        
        # History
        self.conversation_history: list[dict] = []
        self.action_history: list[Action] = []
        self.undo_stack: list[dict] = []  # For rollback
        
        # Settings
        self.require_approval = True
        self.show_diffs = True
        self.max_history = 50
    
    async def process(self, user_request: str) -> AgentResponse:
        """
        Process a user request and execute actions.
        
        Args:
            user_request: Natural language request from user
            
        Returns:
            AgentResponse with message and executed actions
        """
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_request
        })
        
        # Check for special commands
        if user_request.strip().lower() in ["/undo", "undo"]:
            return await self._handle_undo()
        
        if user_request.strip().lower() in ["/history", "history"]:
            return self._handle_history()
        
        # Build context
        context = await self._build_context(user_request)
        
        # Get agent response with tool calls
        try:
            response = await self._get_llm_response(user_request, context)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return AgentResponse(
                message=f"Error getting AI response: {e}",
                success=False
            )
        
        # Parse and execute actions
        actions = self._parse_actions(response)
        executed_actions = []
        
        for action in actions:
            # Show action to user
            self._display_action(action)
            
            # Get approval if required
            if self.require_approval and action.type != ActionType.READ_FILE:
                approved = self._get_approval(action)
                if not approved:
                    action.status = ActionStatus.REJECTED
                    executed_actions.append(action)
                    continue
                action.status = ActionStatus.APPROVED
            
            # Execute action
            try:
                result = await self._execute_action(action)
                action.result = result
                action.status = ActionStatus.EXECUTED
            except Exception as e:
                action.error = str(e)
                action.status = ActionStatus.FAILED
                logger.error(f"Action failed: {e}")
            
            executed_actions.append(action)
            self.action_history.append(action)
        
        # Build response message
        message = self._build_response_message(response, executed_actions)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
        
        return AgentResponse(
            message=message,
            actions=executed_actions,
            thinking=response.get("thinking", ""),
            success=all(a.status == ActionStatus.EXECUTED for a in executed_actions)
        )
    
    async def _build_context(self, request: str) -> str:
        """Build context for the LLM request."""
        context_parts = []
        
        # Project info
        context_parts.append(f"Project: {self.project_path}")
        
        # List key files
        key_files = self._get_key_files()
        if key_files:
            context_parts.append(f"Key files: {', '.join(key_files[:10])}")
        
        # Search for relevant code if agent available
        if self.agent:
            try:
                results = await self.agent.search(request, top_k=5)
                if results.results:
                    context_parts.append("\nRelevant code:")
                    for r in results.results[:3]:
                        context_parts.append(f"- {r.chunk.file}:{r.chunk.start_line}")
                        context_parts.append(f"  {r.chunk.content[:200]}...")
            except Exception as e:
                logger.debug(f"Search failed: {e}")
        
        return "\n".join(context_parts)
    
    def _get_key_files(self) -> list[str]:
        """Get list of key project files."""
        key_patterns = [
            "package.json", "tsconfig.json", "prisma/schema.prisma",
            "src/app.ts", "src/index.ts", "src/main.ts",
            "requirements.txt", "pyproject.toml",
        ]
        
        found = []
        for pattern in key_patterns:
            path = self.project_path / pattern
            if path.exists():
                found.append(pattern)
        
        return found
    
    async def _get_llm_response(self, request: str, context: str) -> dict:
        """Get response from LLM with tool calls."""
        
        system_prompt = f"""You are an AI coding assistant helping edit a backend project.

Project path: {self.project_path}

You can use these tools:
- edit_file: Modify existing files (search and replace)
- create_file: Create new files
- delete_file: Remove files
- read_file: View file contents
- run_command: Run terminal commands (npm, pip, etc.)
- search_code: Search the codebase

When editing files, use precise search strings that will match exactly.
Always explain what you're doing before taking actions.

Context:
{context}
"""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add recent conversation history
        for msg in self.conversation_history[-10:]:
            messages.append(msg)
        
        # Call LLM with tools
        if self.llm_generator:
            response = await self.llm_generator.generate_with_tools(
                messages=messages,
                tools=AGENTIC_TOOLS,
                max_tokens=4096
            )
            return response
        else:
            # Fallback: return empty response if no LLM
            return {
                "content": "LLM not configured. Please set up an LLM provider.",
                "tool_calls": []
            }
    
    def _parse_actions(self, response: dict) -> list[Action]:
        """Parse tool calls from LLM response into actions."""
        actions = []
        
        tool_calls = response.get("tool_calls", [])
        for call in tool_calls:
            action_type = ActionType(call.get("name", "read_file"))
            params = call.get("arguments", {})
            description = params.get("description", call.get("name", ""))
            
            actions.append(Action(
                type=action_type,
                params=params,
                description=description
            ))
        
        return actions
    
    def _display_action(self, action: Action):
        """Display an action to the user."""
        icons = {
            ActionType.EDIT_FILE: "📝",
            ActionType.CREATE_FILE: "📄",
            ActionType.DELETE_FILE: "🗑️",
            ActionType.READ_FILE: "👁️",
            ActionType.RUN_COMMAND: "🔧",
            ActionType.SEARCH_CODE: "🔍",
        }
        
        icon = icons.get(action.type, "•")
        
        if action.type == ActionType.EDIT_FILE:
            path = action.params.get("path", "unknown")
            self.console.print(f"\n{icon} [cyan]Edit:[/] {path}")
            
            if self.show_diffs:
                self._show_edit_diff(action)
                
        elif action.type == ActionType.CREATE_FILE:
            path = action.params.get("path", "unknown")
            self.console.print(f"\n{icon} [green]Create:[/] {path}")
            
            # Show preview
            content = action.params.get("content", "")
            if content and len(content) < 500:
                self.console.print(Panel(
                    Syntax(content, self._get_language(path), line_numbers=True),
                    title="New file contents",
                    border_style="green"
                ))
                
        elif action.type == ActionType.DELETE_FILE:
            path = action.params.get("path", "unknown")
            reason = action.params.get("reason", "")
            self.console.print(f"\n{icon} [red]Delete:[/] {path}")
            if reason:
                self.console.print(f"   Reason: {reason}")
                
        elif action.type == ActionType.RUN_COMMAND:
            cmd = action.params.get("command", "")
            self.console.print(f"\n{icon} [yellow]Run:[/] {cmd}")
            
        elif action.type == ActionType.SEARCH_CODE:
            query = action.params.get("query", "")
            self.console.print(f"\n{icon} [blue]Search:[/] {query}")
    
    def _show_edit_diff(self, action: Action):
        """Show diff preview for file edit."""
        path = self.project_path / action.params.get("path", "")
        
        if not path.exists():
            self.console.print("[dim]  (file does not exist)[/]")
            return
        
        try:
            original = path.read_text()
            modified = original
            
            for edit in action.params.get("edits", []):
                search = edit.get("search", "")
                replace = edit.get("replace", "")
                modified = modified.replace(search, replace)
            
            # Generate diff
            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile=f"a/{path.name}",
                tofile=f"b/{path.name}",
                lineterm=""
            )
            
            diff_text = "".join(diff)
            if diff_text:
                self.console.print(Panel(
                    Syntax(diff_text, "diff"),
                    title="Changes",
                    border_style="cyan"
                ))
        except Exception as e:
            self.console.print(f"[dim]  (could not show diff: {e})[/]")
    
    def _get_language(self, path: str) -> str:
        """Get syntax highlighting language for a file."""
        ext_map = {
            ".ts": "typescript",
            ".tsx": "tsx",
            ".js": "javascript",
            ".jsx": "jsx",
            ".py": "python",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".prisma": "prisma",
            ".sql": "sql",
        }
        ext = Path(path).suffix.lower()
        return ext_map.get(ext, "text")
    
    def _get_approval(self, action: Action) -> bool:
        """Get user approval for an action."""
        if action.type == ActionType.RUN_COMMAND:
            prompt = f"Run this command?"
        elif action.type == ActionType.DELETE_FILE:
            prompt = f"Delete this file?"
        else:
            prompt = f"Apply this change?"
        
        return Confirm.ask(prompt, default=True)
    
    async def _execute_action(self, action: Action) -> Any:
        """Execute an action and return result."""
        
        if action.type == ActionType.EDIT_FILE:
            return await self._exec_edit_file(action.params)
        
        elif action.type == ActionType.CREATE_FILE:
            return await self._exec_create_file(action.params)
        
        elif action.type == ActionType.DELETE_FILE:
            return await self._exec_delete_file(action.params)
        
        elif action.type == ActionType.READ_FILE:
            return await self._exec_read_file(action.params)
        
        elif action.type == ActionType.RUN_COMMAND:
            return await self._exec_run_command(action.params)
        
        elif action.type == ActionType.SEARCH_CODE:
            return await self._exec_search_code(action.params)
        
        else:
            raise ValueError(f"Unknown action type: {action.type}")
    
    async def _exec_edit_file(self, params: dict) -> dict:
        """Execute file edit."""
        path = self.project_path / params.get("path", "")
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Save for undo
        original_content = path.read_text()
        self.undo_stack.append({
            "type": "edit",
            "path": str(path),
            "original": original_content
        })
        
        # Apply edits
        content = original_content
        edits_applied = 0
        
        for edit in params.get("edits", []):
            search = edit.get("search", "")
            replace = edit.get("replace", "")
            
            if search in content:
                content = content.replace(search, replace, 1)
                edits_applied += 1
        
        # Write file
        path.write_text(content)
        
        self.console.print(f"  [green]✓[/] Applied {edits_applied} edit(s)")
        
        return {"edits_applied": edits_applied, "path": str(path)}
    
    async def _exec_create_file(self, params: dict) -> dict:
        """Execute file creation."""
        path = self.project_path / params.get("path", "")
        content = params.get("content", "")
        
        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save for undo
        self.undo_stack.append({
            "type": "create",
            "path": str(path)
        })
        
        # Write file
        path.write_text(content)
        
        self.console.print(f"  [green]✓[/] Created {path.name}")
        
        return {"path": str(path), "size": len(content)}
    
    async def _exec_delete_file(self, params: dict) -> dict:
        """Execute file deletion."""
        path = self.project_path / params.get("path", "")
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Save for undo
        self.undo_stack.append({
            "type": "delete",
            "path": str(path),
            "content": path.read_text()
        })
        
        # Delete file
        path.unlink()
        
        self.console.print(f"  [green]✓[/] Deleted {path.name}")
        
        return {"path": str(path)}
    
    async def _exec_read_file(self, params: dict) -> dict:
        """Execute file read."""
        path = self.project_path / params.get("path", "")
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        content = path.read_text()
        
        # Display to user
        self.console.print(Panel(
            Syntax(content, self._get_language(str(path)), line_numbers=True),
            title=str(path.name),
            border_style="blue"
        ))
        
        return {"path": str(path), "content": content, "size": len(content)}
    
    async def _exec_run_command(self, params: dict) -> CommandResult:
        """Execute terminal command."""
        command = params.get("command", "")
        cwd = params.get("cwd", str(self.project_path))
        
        self.console.print(f"  [dim]Running: {command}[/]")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            cmd_result = CommandResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0
            )
            
            # Display output
            if result.stdout:
                self.console.print(Panel(
                    result.stdout[:2000],
                    title="Output",
                    border_style="green" if cmd_result.success else "red"
                ))
            
            if result.stderr and not cmd_result.success:
                self.console.print(Panel(
                    result.stderr[:1000],
                    title="Error",
                    border_style="red"
                ))
            
            status = "[green]✓[/]" if cmd_result.success else "[red]✗[/]"
            self.console.print(f"  {status} Exit code: {result.returncode}")
            
            return cmd_result
            
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="Command timed out after 5 minutes",
                success=False
            )
    
    async def _exec_search_code(self, params: dict) -> dict:
        """Execute code search."""
        query = params.get("query", "")
        
        if self.agent:
            results = await self.agent.search(query, top_k=10)
            
            # Display results
            table = Table(title=f"Search: {query}")
            table.add_column("File", style="cyan")
            table.add_column("Lines", style="dim")
            table.add_column("Preview", style="white")
            
            for r in results.results[:5]:
                table.add_row(
                    r.chunk.file,
                    f"{r.chunk.start_line}-{r.chunk.end_line}",
                    r.chunk.content[:50] + "..."
                )
            
            self.console.print(table)
            
            return {
                "query": query,
                "count": len(results.results),
                "results": [
                    {"file": r.chunk.file, "score": r.score}
                    for r in results.results[:10]
                ]
            }
        else:
            # Fallback: grep search
            self.console.print("[dim]Agent not available, using basic search[/]")
            return {"query": query, "count": 0, "results": []}
    
    async def _handle_undo(self) -> AgentResponse:
        """Handle undo command."""
        if not self.undo_stack:
            return AgentResponse(
                message="Nothing to undo.",
                success=False
            )
        
        last_action = self.undo_stack.pop()
        
        if last_action["type"] == "edit":
            # Restore original file
            Path(last_action["path"]).write_text(last_action["original"])
            self.console.print(f"[green]✓[/] Restored {last_action['path']}")
            
        elif last_action["type"] == "create":
            # Delete created file
            Path(last_action["path"]).unlink()
            self.console.print(f"[green]✓[/] Removed {last_action['path']}")
            
        elif last_action["type"] == "delete":
            # Restore deleted file
            Path(last_action["path"]).write_text(last_action["content"])
            self.console.print(f"[green]✓[/] Restored {last_action['path']}")
        
        return AgentResponse(
            message="Undo successful.",
            success=True
        )
    
    def _handle_history(self) -> AgentResponse:
        """Handle history command."""
        if not self.action_history:
            return AgentResponse(
                message="No action history.",
                success=True
            )
        
        table = Table(title="Action History")
        table.add_column("#", style="dim")
        table.add_column("Type", style="cyan")
        table.add_column("Target", style="white")
        table.add_column("Status", style="green")
        
        for i, action in enumerate(self.action_history[-10:], 1):
            target = action.params.get("path", action.params.get("command", ""))[:30]
            status_colors = {
                ActionStatus.EXECUTED: "green",
                ActionStatus.FAILED: "red",
                ActionStatus.REJECTED: "yellow",
            }
            color = status_colors.get(action.status, "dim")
            table.add_row(
                str(i),
                action.type.value,
                target,
                f"[{color}]{action.status.value}[/]"
            )
        
        self.console.print(table)
        
        return AgentResponse(
            message=f"Showing last {len(self.action_history[-10:])} actions.",
            success=True
        )
    
    def _build_response_message(self, response: dict, actions: list[Action]) -> str:
        """Build response message from LLM response and executed actions."""
        message = response.get("content", "")
        
        if not message and actions:
            executed = [a for a in actions if a.status == ActionStatus.EXECUTED]
            rejected = [a for a in actions if a.status == ActionStatus.REJECTED]
            failed = [a for a in actions if a.status == ActionStatus.FAILED]
            
            parts = []
            if executed:
                parts.append(f"Completed {len(executed)} action(s)")
            if rejected:
                parts.append(f"{len(rejected)} rejected")
            if failed:
                parts.append(f"{len(failed)} failed")
            
            message = ". ".join(parts) + "."
        
        return message
