"""
FORGE CLI UI Components - Gemini CLI-inspired styling.

This module provides rich terminal UI components matching the aesthetic
of Gemini CLI and Claude Code, including gradient banners, styled prompts,
tool call displays, and session tracking.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.table import Table
from rich.text import Text

# ═══════════════════════════════════════════════════════════════════════════
# COLOR PALETTE - Matching Gemini CLI
# ═══════════════════════════════════════════════════════════════════════════

COLORS = {
    # Banner gradient (pink -> purple -> blue)
    "banner_pink": "#FF6B9D",
    "banner_purple": "#A855F7",
    "banner_blue": "#60A5FA",
    # UI elements
    "prompt_gray": "#6B7280",
    "agent_pink": "#EC4899",
    "file_cyan": "#22D3EE",
    "success_green": "#10B981",
    "warning_yellow": "#FACC15",
    "error_red": "#EF4444",
    # Status bar
    "status_magenta": "#D946EF",
    "status_yellow": "#FACC15",
    "status_cyan": "#22D3EE",
}

# Gradient colors for banner (pink -> purple -> blue transition)
GRADIENT_COLORS = [
    "#FF6B9D", "#F065A0", "#E15FA3", "#D259A6", "#C353A9",
    "#B44DAC", "#A547AF", "#9641B2", "#873BB5", "#7835B8",
    "#692FBB", "#5A29BE", "#4B23C1", "#3C1DC4", "#2D17C7",
    "#1E11CA", "#0F0BCD", "#0015D0", "#001FD3", "#0029D6",
    "#0033D9", "#003DDC", "#0047DF", "#0051E2", "#005BE5",
    "#0065E8", "#006FEB", "#0079EE", "#0083F1", "#008DF4",
    "#0097F7", "#60A5FA",
]

# ═══════════════════════════════════════════════════════════════════════════
# ASCII BANNER - Simple Style
# ═══════════════════════════════════════════════════════════════════════════

FORGE_BANNER = """
[bold cyan]   ███████╗ ██████╗ ██████╗  ██████╗ ███████╗
   ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
   █████╗  ██║   ██║██████╔╝██║  ███╗█████╗  
   ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  
   ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
   ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝[/]
"""


def create_gradient_banner(console: Console) -> None:
    """Print the FORGE banner in cyan."""
    console.print(FORGE_BANNER)


# ═══════════════════════════════════════════════════════════════════════════
# TIPS SECTION
# ═══════════════════════════════════════════════════════════════════════════

def print_tips(console: Console) -> None:
    """Print getting started tips like Gemini CLI."""
    console.print("[dim]Tips for getting started:[/]")
    console.print("[dim]1.[/] Ask questions, edit files, or run commands.")
    console.print("[dim]2.[/] Be specific for the best results.")
    console.print(f"[dim]3.[/] [{COLORS['file_cyan']}]/help[/] for more information.")
    console.print()


# ═══════════════════════════════════════════════════════════════════════════
# USER INPUT STYLING
# ═══════════════════════════════════════════════════════════════════════════

def get_user_prompt(current_file: Optional[str] = None) -> str:
    """Get the styled user prompt string (gray '>' like Gemini)."""
    if current_file:
        return f"[dim]({current_file})[/] [{COLORS['prompt_gray']}]>[/] "
    return f"[{COLORS['prompt_gray']}]>[/] "


def print_user_input(console: Console, message: str) -> None:
    """Print user input with gray prompt."""
    console.print(f"[{COLORS['prompt_gray']}]>[/] {message}")


# ═══════════════════════════════════════════════════════════════════════════
# AGENT RESPONSE STYLING
# ═══════════════════════════════════════════════════════════════════════════

def print_agent_thinking(console: Console, plan: str) -> None:
    """Print agent's thinking/plan with pink bullet like Gemini."""
    # Handle multi-line plans
    lines = plan.strip().split('\n')
    for i, line in enumerate(lines):
        if i == 0:
            console.print(f"[{COLORS['agent_pink']}]✦[/] {line}")
        else:
            console.print(f"  {line}")


def print_agent_response(console: Console, response: str) -> None:
    """Print agent response with proper styling."""
    console.print(f"\n[{COLORS['agent_pink']}]✦[/] {response}")


# ═══════════════════════════════════════════════════════════════════════════
# TOOL CALL DISPLAY
# ═══════════════════════════════════════════════════════════════════════════

def print_tool_call(console: Console, tool_name: str, description: str, 
                    status: str = "running") -> None:
    """
    Print tool call in a bordered box like Gemini CLI.
    
    Status can be: 'running', 'success', 'error'
    """
    if status == "running":
        prefix = "[dim]--[/]"
    elif status == "success":
        prefix = f"[{COLORS['success_green']}]✓[/]"
    elif status == "error":
        prefix = f"[{COLORS['error_red']}]✗[/]"
    else:
        prefix = "[dim]--[/]"
    
    content = f"{prefix} [{COLORS['file_cyan']}]{tool_name}[/] {description}"
    console.print(Panel(content, border_style="dim", padding=(0, 1)))


def print_tool_inline(console: Console, tool_name: str, description: str,
                      status: str = "running") -> None:
    """Print tool call inline (without box) for simpler display."""
    if status == "running":
        prefix = "[dim]--[/]"
    elif status == "success":
        prefix = f"[{COLORS['success_green']}]✓[/]"
    elif status == "error":
        prefix = f"[{COLORS['error_red']}]✗[/]"
    else:
        prefix = "  "
    
    console.print(f"  {prefix} [{COLORS['file_cyan']}]{tool_name}[/] {description}")


# ═══════════════════════════════════════════════════════════════════════════
# PROGRESS INDICATOR
# ═══════════════════════════════════════════════════════════════════════════

def print_progress_title(console: Console, title: str, elapsed_seconds: int = 0) -> None:
    """Print progress title with timer like Gemini's '!' prefix."""
    time_str = f"{elapsed_seconds}s" if elapsed_seconds > 0 else ""
    esc_hint = "(esc to cancel" + (f", {time_str})" if time_str else ")")
    console.print(f"[{COLORS['warning_yellow']}]![/] {title} [dim]{esc_hint}[/]")


# ═══════════════════════════════════════════════════════════════════════════
# STATUS BAR
# ═══════════════════════════════════════════════════════════════════════════

def create_status_bar(cwd: str, model: str = "gemini-2.5-pro", 
                      context_pct: int = 99, sandbox: str = "full sandbox") -> Table:
    """
    Create a three-column status bar like Gemini CLI.
    
    Left: current directory (magenta)
    Center: sandbox mode (yellow)
    Right: model + context remaining (cyan)
    """
    table = Table.grid(expand=True)
    table.add_column(justify="left", ratio=1)
    table.add_column(justify="center", ratio=1)
    table.add_column(justify="right", ratio=1)
    
    table.add_row(
        f"[{COLORS['status_magenta']}]{cwd}[/]",
        f"[{COLORS['status_yellow']}]{sandbox}[/]",
        f"[{COLORS['status_cyan']}]{model} ({context_pct}% context left)[/]"
    )
    
    return table


def print_status_bar(console: Console, cwd: str, model: str = "gemini-2.5-pro",
                     context_pct: int = 99, sandbox: str = "full sandbox") -> None:
    """Print the status bar."""
    console.print(create_status_bar(cwd, model, context_pct, sandbox))


# ═══════════════════════════════════════════════════════════════════════════
# SESSION TRACKING
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SessionTracker:
    """
    Track session metrics for displaying summary on exit.
    Similar to Gemini CLI's interaction summary.
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_time: datetime = field(default_factory=datetime.now)
    
    # Tool call tracking
    tool_calls_success: int = 0
    tool_calls_failed: int = 0
    
    # Token tracking
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    
    # Model usage
    model_requests: dict = field(default_factory=dict)
    
    def record_tool_call(self, success: bool = True) -> None:
        """Record a tool call result."""
        if success:
            self.tool_calls_success += 1
        else:
            self.tool_calls_failed += 1
    
    def record_tokens(self, input_tokens: int, output_tokens: int, 
                      cached: int = 0, model: str = "unknown") -> None:
        """Record token usage."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cached_tokens += cached
        
        if model not in self.model_requests:
            self.model_requests[model] = {"requests": 0, "input": 0, "output": 0}
        self.model_requests[model]["requests"] += 1
        self.model_requests[model]["input"] += input_tokens
        self.model_requests[model]["output"] += output_tokens
    
    @property
    def total_tool_calls(self) -> int:
        return self.tool_calls_success + self.tool_calls_failed
    
    @property
    def success_rate(self) -> float:
        if self.total_tool_calls == 0:
            return 100.0
        return (self.tool_calls_success / self.total_tool_calls) * 100
    
    @property
    def elapsed_time(self) -> str:
        """Get elapsed time as formatted string."""
        delta = datetime.now() - self.start_time
        total_seconds = int(delta.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


def print_session_summary(console: Console, tracker: SessionTracker) -> None:
    """
    Print session summary panel on exit like Gemini CLI.
    
    Shows:
    - Session ID
    - Tool calls with success/failure count
    - Success rate
    - Wall time
    - Token usage by model
    """
    console.print()
    
    # Build summary content
    lines = []
    lines.append("")
    lines.append(f"[bold]Agent powering down. Goodbye![/]")
    lines.append("")
    lines.append("[bold]Interaction Summary[/]")
    lines.append(f"[dim]Session ID:[/]               {tracker.session_id}")
    
    # Tool calls
    tool_str = f"{tracker.total_tool_calls}"
    if tracker.total_tool_calls > 0:
        tool_str += f" ( [{COLORS['success_green']}]✓ {tracker.tool_calls_success}[/]"
        if tracker.tool_calls_failed > 0:
            tool_str += f" [{COLORS['error_red']}]✗ {tracker.tool_calls_failed}[/]"
        tool_str += " )"
    lines.append(f"[dim]Tool Calls:[/]               {tool_str}")
    lines.append(f"[dim]Success Rate:[/]             {tracker.success_rate:.1f}%")
    lines.append("")
    
    # Performance
    lines.append("[bold]Performance[/]")
    lines.append(f"[dim]Wall Time:[/]                {tracker.elapsed_time}")
    lines.append("")
    
    # Model usage table
    if tracker.model_requests:
        lines.append("[bold]Model Usage[/]               [dim]Reqs   Input Tokens   Output Tokens[/]")
        lines.append("[dim]" + "─" * 60 + "[/]")
        for model, stats in tracker.model_requests.items():
            model_display = model[:20].ljust(20)
            lines.append(
                f"[dim]{model_display}[/]   {stats['requests']:>4}   "
                f"{stats['input']:>12,}   {stats['output']:>12,}"
            )
        lines.append("")
        
        # Cache savings
        if tracker.cached_tokens > 0:
            total_input = tracker.input_tokens + tracker.cached_tokens
            cache_pct = (tracker.cached_tokens / total_input) * 100 if total_input > 0 else 0
            lines.append(
                f"[dim]Savings Highlight:[/] {tracker.cached_tokens:,} ({cache_pct:.1f}%) "
                "of input tokens were served from cache."
            )
            lines.append("")
    
    content = "\n".join(lines)
    console.print(Panel(content, border_style="dim", padding=(0, 2)))


# ═══════════════════════════════════════════════════════════════════════════
# CHAT WELCOME SCREEN
# ═══════════════════════════════════════════════════════════════════════════

def print_chat_welcome(console: Console, cwd: str = ".", model: str = "gemini-2.5-pro") -> None:
    """Print the welcome screen for chat mode."""
    create_gradient_banner(console)
    print_tips(console)


# ═══════════════════════════════════════════════════════════════════════════
# FILE REFERENCE HIGHLIGHTING
# ═══════════════════════════════════════════════════════════════════════════

def highlight_file_refs(text: str) -> str:
    """
    Highlight file references in text with cyan color.
    Detects patterns like: file.py, path/to/file.js, README.md
    """
    import re
    
    # Pattern for file paths
    file_pattern = r'([a-zA-Z0-9_\-./]+\.(py|js|ts|tsx|jsx|md|json|yaml|yml|css|html|go|rs|java))'
    
    def replacer(match):
        filepath = match.group(1)
        return f"[{COLORS['file_cyan']}]{filepath}[/]"
    
    return re.sub(file_pattern, replacer, text)


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT INFO DISPLAY
# ═══════════════════════════════════════════════════════════════════════════

def print_context_info(console: Console, info: str) -> None:
    """Print context information in dim style."""
    console.print(f"[dim]{info}[/]")


# ═══════════════════════════════════════════════════════════════════════════
# REAL-TIME PLAN DISPLAY
# ═══════════════════════════════════════════════════════════════════════════


class LivePlanDisplay:
    """
    Display plan as it streams from LLM - real-time discovery visualization.
    
    Usage:
        display = LivePlanDisplay(console)
        display.start()
        display.update("model", "User (email, name, password)", model_obj)
        display.update("endpoint", "GET /users", endpoint_obj)
        display.stop()
    """
    
    # Icons for each component type
    ICONS = {
        "status": "✦",
        "model": "📦",
        "endpoint": "🔌",
        "auth": "🔐",
        "middleware": "⚙️",
        "warning": "⚠️",
    }
    
    def __init__(self, console: Console):
        self.console = console
        self.discoveries = []
        
    def start(self) -> None:
        """Start the live display with header."""
        self.console.print()
        self.console.print(Panel.fit(
            "[bold cyan]🔮 REALTIME FULLSTACK PLANNING[/]",
            border_style="cyan",
        ))
        self.console.print()
    
    def update(self, component_type: str, message: str, data=None) -> None:
        """
        Display a discovered component.
        
        Args:
            component_type: "status", "model", "endpoint", "auth", "middleware", "warning"
            message: Description of the component
            data: Optional component data object
        """
        icon = self.ICONS.get(component_type, "•")
        
        if component_type == "status":
            self.console.print(f"[{COLORS['agent_pink']}]{icon}[/] [dim]{message}[/]")
        elif component_type == "model":
            self.console.print(f"[{COLORS['success_green']}]{icon}[/] Discovered: [bold]{message}[/]")
            self.discoveries.append(("model", message))
        elif component_type == "endpoint":
            self.console.print(f"[{COLORS['file_cyan']}]{icon}[/] Adding: [cyan]{message}[/]")
            self.discoveries.append(("endpoint", message))
        elif component_type == "auth":
            self.console.print(f"[{COLORS['warning_yellow']}]{icon}[/] Detected: [yellow]{message}[/]")
            self.discoveries.append(("auth", message))
        elif component_type == "middleware":
            self.console.print(f"[dim]{icon}[/] Adding: {message}")
            self.discoveries.append(("middleware", message))
        elif component_type == "warning":
            self.console.print(f"[{COLORS['warning_yellow']}]{icon}[/] [yellow]{message}[/]")
    
    def stop(self) -> None:
        """End the live display."""
        self.console.print()


def print_plan_summary(console: Console, plan) -> None:
    """
    Print the final plan summary in a styled panel.
    
    Args:
        console: Rich console
        plan: FullstackPlan object
    """
    # Build summary content
    models_str = ", ".join(m.name for m in plan.models) if plan.models else "None"
    
    content = (
        f"[bold]Models:[/]     {len(plan.models)} ({models_str})\n"
        f"[bold]Endpoints:[/]  {len(plan.endpoints)}\n"
        f"[bold]Middleware:[/] {len(plan.middleware)}\n"
        f"[bold]Auth:[/]       {plan.auth_type or 'None'}\n"
        f"[bold]Database:[/]   {plan.database_type}\n"
        f"[bold]Framework:[/]  {plan.backend_framework}\n"
        f"[bold]Est. Files:[/] ~{plan.estimated_files}"
    )
    
    console.print(Panel(
        content,
        title="[bold cyan]PLAN SUMMARY[/]",
        border_style="cyan",
    ))
    
    # Show warnings if any
    if plan.warnings:
        console.print()
        for warning in plan.warnings:
            console.print(f"[{COLORS['warning_yellow']}]⚠️[/] [yellow]{warning}[/]")


def print_plan_prompt(console: Console) -> str:
    """
    Show interactive prompt for plan approval/modification.
    
    Returns:
        User input: "y" to proceed, "n" to cancel, or modification request
    """
    console.print()
    response = console.input(
        f"[{COLORS['prompt_gray']}]>[/] Proceed, or type to add/modify ([cyan]y[/]/[red]n[/]): "
    ).strip()
    return response if response else "y"


def print_generation_start(console: Console) -> None:
    """Print message when generation starts."""
    console.print()
    console.print(f"[{COLORS['agent_pink']}]✦[/] [bold]Generating backend...[/]")
    console.print()


# ═══════════════════════════════════════════════════════════════════════════
# TASK CHAT DISPLAY
# ═══════════════════════════════════════════════════════════════════════════


def print_task_start(console: Console, task_type: str, description: str = "") -> None:
    """Print task start indicator."""
    console.print()
    console.print(f"[{COLORS['agent_pink']}]✦[/] [bold]{task_type}[/] {description}")


def print_task_step(console: Console, message: str, icon: str = "•") -> None:
    """Print a task progress step."""
    console.print(f"  [{COLORS['file_cyan']}]{icon}[/] {message}")


def print_task_result(console: Console, success: bool, message: str) -> None:
    """Print task result."""
    console.print()
    if success:
        console.print(f"[{COLORS['success_green']}]✓[/] [bold]{message}[/]")
    else:
        console.print(f"[{COLORS['error_red']}]✗[/] [bold]{message}[/]")


def print_task_approval_prompt(console: Console) -> str:
    """Show approval prompt for task execution."""
    console.print()
    response = console.input(
        f"[{COLORS['prompt_gray']}]>[/] Execute this task? ([cyan]y[/]/[red]n[/]): "
    ).strip()
    return response.lower() if response else "y"


def print_chat_commands(console: Console) -> None:
    """Print available chat commands."""
    console.print()
    console.print(Panel(
        "[bold]Available Commands:[/]\n\n"
        f"  [{COLORS['file_cyan']}]/generate[/] <path>     Generate backend from frontend\n"
        f"  [{COLORS['file_cyan']}]/add endpoint[/] <spec> Add new API endpoint\n"
        f"  [{COLORS['file_cyan']}]/add model[/] <name>    Add new data model\n"
        f"  [{COLORS['file_cyan']}]/add auth[/] [type]     Add authentication\n"
        f"  [{COLORS['file_cyan']}]/search[/] <query>      Search codebase\n"
        f"  [{COLORS['file_cyan']}]/help[/]                Show this help\n"
        f"  [{COLORS['file_cyan']}]/exit[/]                Exit chat\n\n"
        "[dim]Or use natural language:[/]\n"
        '  "add rate limiting to all endpoints"\n'
        '  "generate backend from ./frontend"',
        title="[bold cyan]Task Chat[/]",
        border_style="cyan",
    ))


def print_task_callback(console: Console):
    """Create a callback function for task progress."""
    def callback(msg_type: str, message: str, data=None):
        if msg_type == "status":
            console.print(f"[{COLORS['agent_pink']}]✦[/] [dim]{message}[/]")
        elif msg_type == "step":
            console.print(f"  [{COLORS['file_cyan']}]•[/] {message}")
        elif msg_type == "result":
            console.print(f"[{COLORS['success_green']}]✓[/] {message}")
        elif msg_type == "error":
            console.print(f"[{COLORS['error_red']}]✗[/] {message}")
        elif msg_type == "model":
            console.print(f"[{COLORS['success_green']}]📦[/] Discovered: [bold]{message}[/]")
        elif msg_type == "endpoint":
            console.print(f"[{COLORS['file_cyan']}]🔌[/] Adding: [cyan]{message}[/]")
        elif msg_type == "auth":
            console.print(f"[{COLORS['warning_yellow']}]🔐[/] Detected: [yellow]{message}[/]")
        elif msg_type == "middleware":
            console.print(f"[dim]⚙️[/] Adding: {message}")
        elif msg_type == "warning":
            console.print(f"[{COLORS['warning_yellow']}]⚠️[/] [yellow]{message}[/]")
    return callback


