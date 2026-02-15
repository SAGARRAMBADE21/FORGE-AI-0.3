"""Extended CLI with backend generation commands."""

import asyncio
import json
import logging
import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

# Suppress pydantic field shadowing warnings
warnings.filterwarnings("ignore", message=".*Field name.*shadows an attribute.*")

# Load environment variables from .env file
load_dotenv()

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from agent import CodeAgent
from backend_agent import BackendAgent, GenerationMode
from cli.ui import (
    create_gradient_banner,
    print_tips,
    get_user_prompt,
    print_agent_thinking,
    print_agent_response,
    print_tool_call,
    print_tool_inline,
    print_session_summary,
    print_status_bar,
    print_chat_welcome,
    highlight_file_refs,
    print_context_info,
    SessionTracker,
    COLORS,
)
from config.templates_config import BackendFramework, DatabaseType, TemplateConfig
from execution.agentic_loop import AgenticLoop
from fullstack_agent import FullStackAgent
from unified_workflow import generate_synchronized_fullstack

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def show_banner():
    """Display the FORGE banner."""
    create_gradient_banner(console)


app = typer.Typer(
    name="forge",
    help="🚀 FORGE - AI-Powered Full-Stack Code Generation System",
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
)
console = Console()

# Sub-commands
index_app = typer.Typer(
    help="📁 [cyan]Code indexing[/] - Semantic search and navigation",
    rich_markup_mode="rich",
)
backend_app = typer.Typer(
    help="⚙️ [cyan]Backend generation[/] - Generate, review, and debug backend code",
    rich_markup_mode="rich",
)
database_app = typer.Typer(
    help="🗄️ [cyan]Database generation[/] - Generate schemas from frontend analysis",
    rich_markup_mode="rich",
)
app.add_typer(index_app, name="index")
app.add_typer(backend_app, name="backend")
app.add_typer(database_app, name="database")

# Cache for agents to avoid re-initialization
_agent_cache = {}


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def validate_path(path: Path, description: str = "Path") -> bool:
    """Validate path exists and show consistent error message."""
    if not path.exists():
        console.print(f"[red]Error: {description} not found:[/] {path}")
        return False
    return True


def create_progress_callback(console: Console, task_description: str = "Processing..."):
    """Create a reusable progress callback for operations."""
    def callback(stage: str, msg: str):
        console.print(f"[cyan]{stage}:[/] {msg}")
    return callback


# ═══════════════════════════════════════════════════════════════════════════
# INDEX COMMANDS
# ═══════════════════════════════════════════════════════════════════════════


@index_app.command("run")
def index_run(
    path: Path = typer.Argument(..., help="Project path to index"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch for changes"),
):
    """Index a project with semantic search capabilities."""
    # Validate path
    if not validate_path(path, "Project path"):
        raise typer.Exit(1)

    agent = CodeAgent(path)

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as prog:
        task = prog.add_task("Initializing...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        stats = asyncio.run(agent.initialize(callback))

    _display_stats(stats)

    if watch:
        console.print("\n[cyan]Watching for changes... (Ctrl+C to stop)[/]")
        asyncio.run(_watch_loop(agent))


@index_app.command("search")
def index_search(
    path: Path = typer.Argument(..., help="Project path"),
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(5, "-k", "--top-k", help="Number of results"),
):
    """Semantic search over code."""
    agent = CodeAgent(path)

    with console.status("Initializing..."):
        asyncio.run(agent.initialize())

    response = asyncio.run(agent.search(query, top_k=top_k))

    console.print(f"\n[bold]Search:[/] {query}")
    console.print(
        f"[dim]Found {response.total_count} results in {response.search_time_ms:.0f}ms[/]\n"
    )

    for i, result in enumerate(response.results, 1):
        chunk = result.chunk
        title = f"[cyan]{chunk.file}[/] L{chunk.start_line + 1}-{chunk.end_line + 1}"
        if chunk.symbol_name:
            title += f" ([yellow]{chunk.symbol_name}[/])"

        console.print(
            Panel(
                Syntax(
                    chunk.content[:500] + ("..." if len(chunk.content) > 500 else ""),
                    chunk.language,
                    theme="monokai",
                    line_numbers=True,
                    start_line=chunk.start_line + 1,
                ),
                title=title,
                subtitle=f"Score: {result.score:.3f}",
            )
        )


@index_app.command("symbols")
def index_symbols(
    path: Path = typer.Argument(..., help="Project path"),
    query: str = typer.Argument("", help="Search query"),
    kind: str = typer.Option(None, "-k", "--kind", help="Filter by kind"),
    limit: int = typer.Option(20, "-n", "--limit", help="Max results"),
):
    """Search or list symbols."""
    agent = CodeAgent(path)

    with console.status("Initializing..."):
        asyncio.run(agent.initialize())

    if query:
        results = agent.search_symbols(query, limit)
    else:
        results = list(agent.indexer.symbol_table)[:limit]

    _display_symbols(results)


# ═══════════════════════════════════════════════════════════════════════════
# BACKEND COMMANDS
# ═══════════════════════════════════════════════════════════════════════════


@backend_app.command("generate")
def backend_generate(
    path: Path = typer.Argument(..., help="Project path"),
    output: Path = typer.Option(None, "-o", "--output", help="Output directory"),
    framework: str = typer.Option(
        "express", "-f", "--framework", help="Backend framework"
    ),
    database: str = typer.Option(
        "postgresql", "-d", "--database", help="Database type"
    ),
    mode: str = typer.Option(
        "hybrid", "-m", "--mode", help="Generation mode: single, multi, hybrid"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without applying"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Enter edit mode after generation"),
):
    """Generate backend from frontend analysis.

    Modes:
      single - Fast single-agent mode (1-2 min, good for MVPs)
      multi  - Production multi-agent mode (5-10 min, 8 specialized agents)
      hybrid - Auto-select based on project complexity (default)
    """
    # Validate path
    if not validate_path(path, "Frontend path"):
        raise typer.Exit(1)

    # Parse generation mode
    mode_map = {
        "single": GenerationMode.SINGLE_AGENT,
        "multi": GenerationMode.MULTI_AGENT,
        "hybrid": GenerationMode.HYBRID,
    }

    if mode.lower() not in mode_map:
        console.print(
            f"[red]Error: Invalid mode '{mode}'. Use: single, multi, or hybrid[/]"
        )
        raise typer.Exit(1)

    generation_mode = mode_map[mode.lower()]

    console.print(f"[cyan]Generation mode:[/] {mode.upper()}")
    if mode.lower() == "hybrid":
        console.print("[dim]  Will auto-select based on project complexity[/]")
    elif mode.lower() == "single":
        console.print("[dim]  Fast prototyping mode[/]")
    else:
        console.print("[dim]  Production-quality mode with 8 specialized agents[/]")

    # Configure
    config = TemplateConfig(
        framework=BackendFramework(framework),
        database=DatabaseType(database),
        output_dir=str(output) if output else "backend",
    )

    agent = FullStackAgent(path, config)

    # Set generation mode
    agent.backend_agent.set_generation_mode(generation_mode)

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as prog:
        task = prog.add_task("Initializing...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        result = asyncio.run(_generate_backend(agent, callback, dry_run))

    if result.success:
        console.print(f"\n[green]✓ Backend generation complete![/]")

        # Initialize complexity for later use
        complexity = None
        
        # Show mode used
        if generation_mode == GenerationMode.HYBRID:
            complexity = agent.backend_agent._assess_project_complexity()
            actual_mode = (
                "multi-agent" if complexity in ["medium", "high"] else "single-agent"
            )
            console.print(
                f"[dim]Mode used: {actual_mode} (complexity: {complexity})[/]"
            )

        # Show collaboration report for multi-agent
        if generation_mode == GenerationMode.MULTI_AGENT or (
            generation_mode == GenerationMode.HYBRID
            and complexity in ["medium", "high"]
        ):
            report = agent.backend_agent.get_agent_collaboration_report()
            if report != "Multi-agent mode not active":
                console.print(f"\n[cyan]Agent Collaboration:[/]")
                console.print(f"[dim]{report}[/]")

        # Display generated files
        table = Table(title=f"Generated Files ({len(result.files)})")
        table.add_column("Path", style="cyan")
        table.add_column("Type")
        table.add_column("Generator")

        for f in result.files[:20]:
            table.add_row(f.path, f.file_type, f.generator)

        if len(result.files) > 20:
            table.add_row("...", f"+{len(result.files) - 20} more", "")

        console.print(table)

        if result.stats:
            console.print(f"\n[dim]Stats: {result.stats}[/]")

        if dry_run:
            console.print("\n[yellow]Dry run - no files were written[/]")
        else:
            # Write files to disk
            output_dir = output if output else path / "backend"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            console.print(f"\n[cyan]Writing files to:[/] {output_dir}")
            files_written = 0
            
            for file_obj in result.files:
                file_path = output_dir / file_obj.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_obj.content, encoding="utf-8")
                files_written += 1
            
            console.print(f"[green]✓ Wrote {files_written} files to {output_dir}[/]")
            
            # Offer edit mode after successful generation
            enter_edit = edit
            if not edit:
                console.print()
                enter_edit = typer.confirm(
                    "🔧 Would you like to edit the generated code with prompts?",
                    default=False
                )
            
            if enter_edit:
                _enter_post_generation_edit(output_dir, agent, console)
    else:
        console.print(f"\n[red]✗ Generation failed[/]")
        for error in result.errors:
            console.print(f"  [red]• {error}[/]")


@backend_app.command("analyze")
def backend_analyze(
    path: Path = typer.Argument(..., help="Frontend project path"),
    reindex: bool = typer.Option(False, "--reindex", help="Force re-indexing"),
):
    """Analyze frontend and show inferred backend architecture.
    
    This command analyzes your frontend code and shows what backend
    structure would be generated, without creating any files.
    """
    if not validate_path(path, "Frontend path"):
        raise typer.Exit(1)

    agent = FullStackAgent(path)

    # Check if already indexed
    codegen_dir = path / ".codegen"
    index_exists = (
        (codegen_dir / "vectorstore").exists() if codegen_dir.exists() else False
    )

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as prog:
        if index_exists and not reindex:
            task = prog.add_task("Loading existing index...", total=None)
        else:
            task = prog.add_task("Analyzing...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        asyncio.run(agent.initialize(callback))
        analysis = asyncio.run(agent.analyze_frontend(callback))

    console.print(f"\n[green]✓ Analysis complete![/]")

    # Display analysis
    _display_frontend_analysis(analysis)


@backend_app.command("add-model")
def backend_add_model(
    path: Path = typer.Argument(..., help="Project path"),
    name: str = typer.Argument(..., help="Model name"),
    fields: str = typer.Option(
        "", "-f", "--fields", help="Fields as JSON array or path to JSON file"
    ),
    reindex: bool = typer.Option(False, "--reindex", help="Force re-indexing"),
):
    """Add a new model to the backend."""
    # Use cached agent if available
    cache_key = str(path.resolve())
    if cache_key not in _agent_cache or reindex:
        agent = FullStackAgent(path)
        _agent_cache[cache_key] = agent
    else:
        agent = _agent_cache[cache_key]

    status_msg = (
        "Re-indexing..."
        if reindex
        else (
            "Loading cached index..."
            if cache_key in _agent_cache
            else "Initializing..."
        )
    )
    with console.status(status_msg):
        asyncio.run(agent.initialize(force_reindex=reindex))

    # Parse fields
    field_list = []
    if fields:
        try:
            # Check if it's a file path
            if fields.endswith(".json") and Path(fields).exists():
                field_list = json.loads(Path(fields).read_text())
            else:
                # Handle both escaped and unescaped JSON
                import re

                # Replace single quotes with double quotes if present
                fields_cleaned = fields.replace("'", '"')
                field_list = json.loads(fields_cleaned)

            # Validate structure
            if not isinstance(field_list, list):
                raise ValueError("Fields must be a JSON array")
            for field in field_list:
                if (
                    not isinstance(field, dict)
                    or "name" not in field
                    or "type" not in field
                ):
                    raise ValueError(
                        "Each field must have 'name' and 'type' properties"
                    )
        except (json.JSONDecodeError, ValueError) as e:
            console.print(f"[red]Invalid fields JSON: {e}[/]")
            console.print(
                f'[yellow]Expected format: \'[{{"name":"field1","type":"string"}}]\'[/]'
            )
            console.print(f"[yellow]Or provide a path to JSON file: -f fields.json[/]")
            console.print(
                f'[yellow]Example: -f \'[{{"name":"id","type":"string"}},{{"name":"title","type":"string"}}]\'[/]'
            )
            raise typer.Exit(1)

    result = asyncio.run(agent.add_model(name, field_list))

    if result.success:
        console.print(f"[green]✓ Model {name} added[/]")
    else:
        console.print(f"[red]✗ Failed to add model[/]")
        for error in result.errors:
            console.print(f"  [red]• {error}[/]")


@backend_app.command("add-endpoint")
def backend_add_endpoint(
    path: Path = typer.Argument(..., help="Project path"),
    method: str = typer.Argument(..., help="HTTP method"),
    endpoint_path: str = typer.Argument(..., help="Endpoint path"),
    reindex: bool = typer.Option(False, "--reindex", help="Force re-indexing"),
):
    """Add a new API endpoint."""
    # Use cached agent if available
    cache_key = str(path.resolve())
    if cache_key not in _agent_cache or reindex:
        agent = FullStackAgent(path)
        _agent_cache[cache_key] = agent
    else:
        agent = _agent_cache[cache_key]

    status_msg = (
        "Re-indexing..."
        if reindex
        else (
            "Loading cached index..."
            if cache_key in _agent_cache
            else "Initializing..."
        )
    )
    with console.status(status_msg):
        asyncio.run(agent.initialize(force_reindex=reindex))

    result = asyncio.run(agent.add_endpoint(method.upper(), endpoint_path))

    if result.success:
        console.print(f"[green]✓ Endpoint {method.upper()} {endpoint_path} added[/]")
    else:
        console.print(f"[red]✗ Failed to add endpoint[/]")


@backend_app.command("sync")
def backend_sync(path: Path = typer.Argument(..., help="Project path")):
    """Sync backend with frontend changes."""
    agent = FullStackAgent(path)

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as prog:
        task = prog.add_task("Syncing...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        asyncio.run(agent.initialize(callback))
        result = asyncio.run(agent.sync_backend(callback))

    if result.success:
        console.print(f"[green]✓ Sync complete[/]")
    else:
        console.print(f"[red]✗ Sync failed[/]")


@backend_app.command("rollback")
def backend_rollback(path: Path = typer.Argument(..., help="Project path")):
    """Rollback last backend change."""
    agent = FullStackAgent(path)

    with console.status("Initializing..."):
        asyncio.run(agent.initialize())

    success = asyncio.run(agent.rollback())

    if success:
        console.print(f"[green]✓ Rollback successful[/]")
    else:
        console.print(f"[red]✗ Rollback failed[/]")


@backend_app.command("review")
def backend_review(
    path: Path = typer.Argument(..., help="Backend project path to review"),
    output: str = typer.Option(
        None, "-o", "--output", help="Output file for review report"
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Show detailed analysis"
    ),
):
    """Review existing backend code for quality, security, and best practices.

    Analyzes:
      - Code quality and structure
      - Security vulnerabilities (OWASP)
      - Performance issues
      - Best practices adherence
      - Documentation gaps
    """
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)

    console.print(f"[cyan]Reviewing backend code at:[/] {path}\n")

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as prog:
        task = prog.add_task("Initializing code review...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        # Import generator and perform review
        from config.settings import settings
        from generation.llm_generator import LLMGenerator

        llm = LLMGenerator(
            provider=settings.llm.backend_provider, model=settings.llm.backend_model
        )

        # Collect backend files
        prog.update(task, description="Scanning backend files...")
        backend_files = []
        code_content = []

        for ext in [".py", ".js", ".ts", ".java", ".go", ".rs"]:
            for file in path.rglob(f"*{ext}"):
                if "node_modules" not in str(file) and "__pycache__" not in str(file):
                    backend_files.append(file)
                    try:
                        content = file.read_text(encoding="utf-8", errors="ignore")
                        if len(content) < 10000:  # Limit file size
                            code_content.append(
                                f"### {file.relative_to(path)}\n```\n{content[:3000]}\n```"
                            )
                    except:
                        pass

        if not backend_files:
            console.print(f"[yellow]No backend code files found in {path}[/]")
            raise typer.Exit(1)

        prog.update(task, description=f"Analyzing {len(backend_files)} files...")

        # Perform LLM review
        system_prompt = """You are an expert code reviewer specializing in backend development.
Analyze the provided code for:
1. **Security Issues** - SQL injection, XSS, auth flaws, data exposure
2. **Code Quality** - Clean code principles, SOLID, DRY, maintainability
3. **Performance** - Inefficient queries, memory leaks, N+1 problems
4. **Best Practices** - Error handling, logging, testing patterns
5. **Documentation** - Missing comments, unclear function purposes

Provide actionable recommendations with severity levels (Critical/High/Medium/Low)."""

        user_prompt = f"""Review this backend codebase:

Files found: {len(backend_files)}

Code samples:
{chr(10).join(code_content[:5])}

Provide a structured review report with:
1. Executive Summary
2. Critical Issues (if any)
3. Security Analysis
4. Code Quality Score (1-10)
5. Specific Recommendations
6. Files that need attention"""

        prog.update(task, description="Generating review report...")

        review_result = asyncio.run(
            llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        )

    # Display results
    console.print("\n" + "═" * 70)
    console.print("[bold cyan]📋 CODE REVIEW REPORT[/]")
    console.print("═" * 70 + "\n")

    console.print(Markdown(review_result))

    # Save to file if requested
    if output:
        output_path = Path(output)
        output_path.write_text(f"# Code Review Report\n\n{review_result}")
        console.print(f"\n[green]✓ Report saved to {output}[/]")

    console.print(f"\n[dim]Reviewed {len(backend_files)} files[/]")


@backend_app.command("debug")
def backend_debug(
    path: Path = typer.Argument(..., help="Backend project path"),
    error: str = typer.Option(None, "-e", "--error", help="Error message to debug"),
    file: str = typer.Option(None, "-f", "--file", help="Specific file with the issue"),
    line: int = typer.Option(None, "-l", "--line", help="Line number of the issue"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix detected issues"),
):
    """Debug backend code issues with AI assistance.

    Modes:
      - Provide an error message to get fix suggestions
      - Specify a file and line for targeted analysis
      - Run without options for general issue detection
      - Use --fix to automatically apply fixes
    """
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)

    console.print(f"[cyan]Debugging backend at:[/] {path}")
    if fix:
        console.print(f"[yellow]⚡ Auto-fix mode enabled[/]\n")
    else:
        console.print()

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as prog:
        task = prog.add_task("Initializing debugger...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        from config.settings import settings
        from generation.llm_generator import LLMGenerator

        llm = LLMGenerator(
            provider=settings.llm.backend_provider, model=settings.llm.backend_model
        )

        # Get relevant code context
        code_context = ""
        target_file_path = None
        original_content = ""

        if file:
            file_path = path / file
            if file_path.exists():
                original_content = file_path.read_text(
                    encoding="utf-8", errors="ignore"
                )
                target_file_path = file_path
                if line:
                    lines = original_content.split("\n")
                    start = max(0, line - 15)
                    end = min(len(lines), line + 15)
                    code_context = f"File: {file} (around line {line})\n```\n"
                    for i in range(start, end):
                        marker = ">>> " if i + 1 == line else "    "
                        code_context += f"{marker}{i+1}: {lines[i]}\n"
                    code_context += "```"
                else:
                    code_context = f"File: {file}\n```\n{original_content[:5000]}\n```"
            else:
                console.print(f"[red]File not found: {file}[/]")
                raise typer.Exit(1)
        else:
            # Collect recent/relevant files
            prog.update(task, description="Scanning for potential issues...")
            for ext in [".py", ".js", ".ts"]:
                for f in list(path.rglob(f"*{ext}"))[:5]:
                    if "node_modules" not in str(f):
                        try:
                            content = f.read_text(encoding="utf-8", errors="ignore")
                            code_context += f"\n### {f.relative_to(path)}\n```\n{content[:2000]}\n```"
                        except:
                            pass

        prog.update(task, description="Analyzing code for issues...")

        # If fix mode and we have a specific file, use a different prompt
        if fix and target_file_path:
            system_prompt = """You are an expert backend debugger. Analyze the code and provide:
1. A brief list of issues found
2. The COMPLETE FIXED FILE content

IMPORTANT: After your analysis, output the complete fixed file wrapped in:
```fixed
<complete fixed file content here>
```

Fix ALL issues you find:
- Null/undefined handling
- Error handling gaps
- Type validation
- Logic errors
- Security issues"""

            user_prompt = f"""Analyze and FIX this code:

{code_context}

Provide:
1. Brief list of issues found (one line each)
2. The COMPLETE fixed file content in a ```fixed code block"""
        elif error:
            system_prompt = """You are an expert backend debugger. Given an error message and code context,
identify the root cause and provide a clear fix. Be specific about:
1. What caused the error
2. The exact fix needed (with code)
3. How to prevent similar issues"""

            user_prompt = f"""Error message:
```
{error}
```

Code context:
{code_context}

Provide:
1. Root Cause Analysis
2. Step-by-step Fix
3. Code changes needed
4. Prevention tips"""
        else:
            system_prompt = """You are an expert backend debugger. Analyze the code for potential bugs,
runtime errors, and logical issues. Look for:
1. Null/undefined handling
2. Async/await issues
3. Error handling gaps
4. Type mismatches
5. Logic errors"""

            user_prompt = f"""Analyze this code for bugs and issues:

{code_context}

Provide:
1. Detected Issues (severity rated)
2. Potential Runtime Errors
3. Logic Problems
4. Suggested Fixes with code examples"""

        prog.update(task, description="Generating debug analysis...")

        debug_result = asyncio.run(
            llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        )

        # If fix mode, extract and apply the fixed code
        fixed_applied = False
        backup_path = None
        if fix and target_file_path:
            prog.update(task, description="Extracting fixed code...")

            # Try to extract fixed code block
            import re

            fixed_match = re.search(r"```fixed\n(.*?)```", debug_result, re.DOTALL)
            if not fixed_match:
                # Try alternative patterns
                fixed_match = re.search(r"```python\n(.*?)```", debug_result, re.DOTALL)

            if fixed_match:
                fixed_code = fixed_match.group(1).strip()

                # Create backup
                backup_path = target_file_path.with_suffix(
                    target_file_path.suffix + ".backup"
                )
                backup_path.write_text(original_content, encoding="utf-8")

                # Apply fix
                target_file_path.write_text(fixed_code, encoding="utf-8")
                fixed_applied = True
                prog.update(task, description="Fix applied!")

    # Display results
    console.print("\n" + "═" * 70)
    console.print("[bold cyan]🔍 DEBUG ANALYSIS[/]")
    console.print("═" * 70 + "\n")

    if error:
        console.print(
            f"[red]Error:[/] {error[:100]}...\n"
            if len(error) > 100
            else f"[red]Error:[/] {error}\n"
        )

    console.print(Markdown(debug_result))

    if fixed_applied:
        console.print(f"\n[green]✓ Fix applied to {target_file_path}[/]")
        console.print(f"[dim]  Backup saved to {backup_path}[/]")
        console.print(f"\n[yellow]Review the changes and test your code![/]")
    elif fix and not target_file_path:
        console.print(f"\n[yellow]⚠ --fix requires a specific file (-f)[/]")
        console.print(
            f"[dim]  Example: python main.py backend debug ./backend -f app.py --fix[/]"
        )

    console.print(f"\n[dim]Debug analysis complete[/]")


@backend_app.command("fix")
def backend_fix(
    path: Path = typer.Argument(..., help="Backend project path"),
    file: str = typer.Option(
        None, "-f", "--file", help="Specific file to fix (required)"
    ),
):
    """Auto-fix code issues with AI assistance.

    Scans the code for bugs, security issues, and bad patterns,
    then automatically applies fixes.

    Example:
      python main.py backend fix ./backend -f app.py
    """
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)

    if not file:
        console.print(f"[red]Error: --file (-f) is required[/]")
        console.print(
            f"[dim]Example: python main.py backend fix ./backend -f app.py[/]"
        )
        raise typer.Exit(1)

    file_path = path / file
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/]")
        raise typer.Exit(1)

    console.print(f"[cyan]Fixing:[/] {file_path}")
    console.print(f"[yellow]⚡ Auto-fix mode[/]\n")

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as prog:
        task = prog.add_task("Reading file...", total=None)

        from config.settings import settings
        from generation.llm_generator import LLMGenerator

        llm = LLMGenerator(
            provider=settings.llm.backend_provider, model=settings.llm.backend_model
        )

        original_content = file_path.read_text(encoding="utf-8", errors="ignore")

        prog.update(task, description="Analyzing and fixing...")

        system_prompt = """You are an expert code fixer. Analyze the code and:
1. List issues found (briefly)
2. Output the COMPLETE FIXED FILE

Output format:
## Issues Found
- issue 1
- issue 2

```fixed
<complete fixed code>
```

Fix: null handling, error handling, type validation, logic errors, security issues."""

        user_prompt = f"""Fix this code:

```
{original_content}
```

Return the complete fixed file in a ```fixed block."""

        result = asyncio.run(
            llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        )

        prog.update(task, description="Applying fix...")

        # Extract fixed code
        import re

        fixed_match = re.search(r"```fixed\n(.*?)```", result, re.DOTALL)
        if not fixed_match:
            fixed_match = re.search(r"```python\n(.*?)```", result, re.DOTALL)
        if not fixed_match:
            fixed_match = re.search(r"```\n(.*?)```", result, re.DOTALL)

        backup_path = None
        if fixed_match:
            fixed_code = fixed_match.group(1).strip()

            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + ".backup")
            backup_path.write_text(original_content, encoding="utf-8")

            # Apply fix
            file_path.write_text(fixed_code, encoding="utf-8")

            prog.update(task, description="Fix applied!")

    # Show results
    console.print("\n" + "═" * 50)
    console.print(Markdown(result))
    console.print("═" * 50)

    if fixed_match:
        console.print(f"\n[green]✓ Fixed: {file_path}[/]")
        console.print(f"[dim]  Backup: {backup_path}[/]")
    else:
        console.print(f"\n[yellow]⚠ Could not extract fixed code[/]")




# ═══════════════════════════════════════════════════════════════════════════
# EDIT COMMAND - Universal NLP-powered editor
# ═══════════════════════════════════════════════════════════════════════════


@app.command()
def edit_console(
    file: str = typer.Argument(None, help="File to edit (optional)"),
    workspace: Path = typer.Option(".", "-w", "--workspace", help="Workspace directory"),
):
    """
    🔧 Interactive NLP-powered edit console for ALL FORGE outputs
    
    Edit schemas, backend code, APIs, models, and configs using natural language!
    
    Examples:
        forge edit-console schema.sql                    # Load schema and start editing
        forge edit-console                               # Start console first, load later
        
    Natural language commands:
        "rename table users to accounts"
        "change email field to VARCHAR(255)"
        "make password field required"
        "add error handling to createUser function"
    """
    from edit_console import EditConsole
    from config.settings import settings
    from generation.llm_generator import LLMGenerator
    
    console.print()
    
    # Initialize LLM for NLP parsing
    try:
        llm_client = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
    except Exception as e:
        console.print(f"[yellow]Warning: LLM not available ({e})[/]")
        console.print("[dim]Will use pattern-based parsing as fallback[/]")
        llm_client = None
    
    # Create and run console
    edit_console_obj = EditConsole(workspace_path=str(workspace), llm_client=llm_client)
    
    # Load file if provided
    if file:
        try:
            edit_console_obj._handle_load(file)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load {file}: {e}[/]")
            console.print(f"[dim]You can load it manually with: load {file}[/]")
    
    # Run interactive console
    edit_console_obj.run()


# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL COMMANDS
# ═══════════════════════════════════════════════════════════════════════════


@app.command()
def setup():
    """🔧 Interactive configuration wizard for FORGE setup."""
    show_banner()
    from cli.wizard import run_wizard

    run_wizard()


@app.command()
def stats():
    """📊 Show usage statistics, costs, and cache info."""
    show_banner()

    # Cost tracking stats
    try:
        from generation.cost_tracker import get_tracker

        tracker = get_tracker()

        console.print("[bold cyan]💰 Cost Tracking[/]\n")
        summary = tracker.get_summary()

        cost_table = Table(show_header=False, box=None)
        cost_table.add_column("Metric", style="dim", width=25)
        cost_table.add_column("Value", style="cyan")

        cost_table.add_row("Session Cost", summary["session_cost_usd"])
        cost_table.add_row("Today's Cost", summary["today_cost_usd"])
        cost_table.add_row("Lifetime Cost", summary["lifetime_cost_usd"])
        cost_table.add_row("Total Requests", str(summary["total_requests"]))
        cost_table.add_row("Cached Requests", str(summary["cached_requests"]))
        cost_table.add_row("Cache Hit Rate", summary["cache_hit_rate"])
        cost_table.add_row("Total Input Tokens", f"{summary['total_input_tokens']:,}")
        cost_table.add_row("Total Output Tokens", f"{summary['total_output_tokens']:,}")

        console.print(cost_table)

        # Usage by model
        usage = tracker.get_usage_by_model()
        if usage:
            console.print("\n[bold]Usage by Model:[/]")
            for model, stats in list(usage.items())[:5]:
                console.print(
                    f"  [cyan]{model}[/]: {stats['requests']} requests, ${stats['cost_usd']:.4f}"
                )
    except Exception as e:
        console.print(f"[dim]Cost tracking not available: {e}[/]")

    # Cache stats
    try:
        from generation.cache_manager import get_cache

        cache = get_cache()

        console.print("\n[bold cyan]📦 Response Cache[/]\n")
        cache_stats = cache.stats()

        cache_table = Table(show_header=False, box=None)
        cache_table.add_column("Metric", style="dim", width=25)
        cache_table.add_column("Value", style="cyan")

        cache_table.add_row("Cache Hits", str(cache_stats["hits"]))
        cache_table.add_row("Cache Misses", str(cache_stats["misses"]))
        cache_table.add_row("Hit Rate", cache_stats["hit_rate"])
        cache_table.add_row("Memory Entries", str(cache_stats["memory_entries"]))
        cache_table.add_row("Disk Size", f"{cache_stats['disk_size_mb']} MB")
        cache_table.add_row("Enabled", "Yes" if cache_stats["enabled"] else "No")

        console.print(cache_table)
    except Exception as e:
        console.print(f"[dim]Cache stats not available: {e}[/]")

    # Optimization stats
    try:
        from generation.prompt_optimizer import get_optimizer

        optimizer = get_optimizer()
        opt_stats = optimizer.get_stats()

        if opt_stats["prompts_optimized"] > 0:
            console.print("\n[bold cyan]⚡ Prompt Optimization[/]\n")
            console.print(f"  Prompts Optimized: {opt_stats['prompts_optimized']}")
            console.print(f"  Characters Saved: {opt_stats['total_chars_saved']:,}")
            console.print(
                f"  Average Reduction: {opt_stats['average_reduction_percent']:.1f}%"
            )
    except Exception:
        pass

    console.print()


@app.command("help")
def show_help(
    section: str = typer.Argument(
        None,
        help="Help section: start, commands, providers, frameworks, examples, troubleshoot",
    )
):
    """📚 Show detailed help and documentation."""
    show_banner()
    from cli.help import show_help as display_help

    display_help(section)


@app.command()
def init(
    path: Path = typer.Argument(".", help="Project path"),
    framework: str = typer.Option("express", "-f", "--framework"),
):
    """Initialize a new project with code generation support."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    # Create .codegen directory
    codegen_dir = path / ".codegen"
    codegen_dir.mkdir(exist_ok=True)

    # Create config file
    config = {
        "framework": framework,
        "database": "postgresql",
        "output_dir": "backend",
        "features": {"docker": True, "testing": True, "swagger": True},
    }

    (codegen_dir / "config.json").write_text(json.dumps(config, indent=2))

    console.print(f"[green]✓ Initialized codegen in {path}[/]")
    console.print(f"  Config: {codegen_dir / 'config.json'}")


@app.command()
def status(path: Path = typer.Argument(".", help="Project path")):
    """Show project status."""
    path = Path(path)
    codegen_dir = path / ".codegen"

    if not codegen_dir.exists():
        console.print("[yellow]Project not initialized. Run 'codegen init' first.[/]")
        return

    # Load config
    config = {}
    config_file = codegen_dir / "config.json"
    if config_file.exists():
        config = json.loads(config_file.read_text())
        console.print(f"\n[bold]Configuration:[/]")
        console.print(f"  Framework: {config.get('framework')}")
        console.print(f"  Database: {config.get('database')}")
        console.print(f"  Output: {config.get('output_dir')}")

    # Check for generated backend
    backend_dir = path / config.get("output_dir", "backend")
    if backend_dir.exists():
        file_count = sum(1 for _ in backend_dir.rglob("*") if _.is_file())
        console.print(f"\n[bold]Backend:[/] {file_count} files in {backend_dir}")
    else:
        console.print(f"\n[bold]Backend:[/] Not generated yet")

    # Check sessions
    sessions_dir = codegen_dir / "sessions"
    if sessions_dir.exists():
        session_count = len(list(sessions_dir.glob("*.json")))
        console.print(f"\n[bold]Sessions:[/] {session_count}")

    # Check checkpoints
    checkpoints_dir = codegen_dir / "checkpoints"
    if checkpoints_dir.exists():
        checkpoint_count = len(list(checkpoints_dir.glob("*")))
        console.print(f"[bold]Checkpoints:[/] {checkpoint_count}")


# ═══════════════════════════════════════════════════════════════════════════
# AGENTIC EDIT MODE
# ═══════════════════════════════════════════════════════════════════════════


@app.command()
def edit(
    path: Path = typer.Argument(..., help="Backend project path to edit"),
):
    """
    🔧 Agentic edit mode - edit code with natural language.
    
    Enter an interactive loop where you can:
    - Edit files: "Add rate limiting to API endpoints"
    - Run commands: "Run npm install express-rate-limit"
    - Create files: "Create a health check endpoint"
    - Search code: "Find authentication logic"
    - Undo changes: "undo"
    
    All changes require your approval before execution.
    """
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)
    
    # Display welcome
    console.print(f"\n[bold cyan]🔧 FORGE Agentic Edit Mode[/]")
    console.print(f"[dim]Project: {path}[/]\n")
    
    console.print("[dim]Commands:[/]")
    console.print("  • Type natural language requests to edit code")
    console.print("  • [cyan]undo[/] - Undo last change")
    console.print("  • [cyan]history[/] - Show action history")
    console.print("  • [cyan]/exit[/] - Exit edit mode")
    console.print()
    
    # Create session tracker
    session = SessionTracker()
    
    # Initialize agent for context (optional)
    agent = None
    try:
        agent = FullStackAgent(path)
        with console.status("[dim]Indexing project...[/]"):
            asyncio.run(agent.initialize())
        console.print(f"[green]✓[/] Project indexed\n")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not initialize agent: {e}[/]")
        console.print("[dim]Continuing without semantic search...[/]\n")
    
    # Create agentic loop
    loop = AgenticLoop(
        project_path=path,
        console=console,
        agent=agent,
    )
    
    # Main loop
    while True:
        try:
            # Get user input
            request = console.input(f"[{COLORS['prompt_gray']}]>[/] ").strip()
            
            if not request:
                continue
            
            # Handle exit
            if request.lower() in ("/exit", "/quit", "/q", "exit", "quit"):
                break
            
            # Process request
            with console.status("[dim]Thinking...[/]"):
                response = asyncio.run(loop.process(request))
            
            # Display response
            if response.message:
                print_agent_response(console, response.message)
            
            # Track for session summary
            for action in response.actions:
                success = action.status.value == "executed"
                session.record_tool_call(success=success)
            
        except KeyboardInterrupt:
            console.print("\n[dim]Use /exit to quit[/]")
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            logger.exception("Edit mode error")
    
    # Show session summary
    print_session_summary(console, session)


@app.command()
def chat(
    path: Path = typer.Argument(None, help="Codebase path to index and chat about"),
    file: str = typer.Option(None, "-f", "--file", help="Current file context"),
    task_mode: bool = typer.Option(True, "--task/--no-task", help="Enable task execution"),
):
    """
    🔮 Interactive task chat - execute backend tasks via natural language.
    
    SLASH COMMANDS:
        /generate <path>      Generate backend from frontend
        /add endpoint <spec>  Add new API endpoint  
        /add model <name>     Add new data model
        /add auth [type]      Add authentication
        /search <query>       Search codebase
        /help                 Show all commands
    
    Examples:
        forge chat ./my-project
        forge chat ./backend --no-task
    """
    from cli.ui import print_chat_commands, print_task_callback, print_task_result
    from orchestration.task_chat import TaskChat
    
    # Create session tracker for Gemini-style exit summary
    session = SessionTracker()

    if path is None:
        print_chat_welcome(console)
        console.print("[dim]No codebase path provided - running in no-index mode[/]")
        console.print("[dim]Usage: python main.py chat <path-to-codebase>[/]\n")

        # Simple chat loop without agent
        while True:
            try:
                message = _get_user_input(console, file)
                if not message:
                    continue

                if message.startswith("/"):
                    if message.lower().strip() in ("/exit", "/quit", "/q"):
                        break
                    elif message.lower().strip() == "/help":
                        print_chat_commands(console)
                    else:
                        console.print(
                            "[dim]Command not available in no-index mode[/]"
                        )
                    continue

                print_agent_thinking(
                    console,
                    "No-index mode: Provide a codebase path to enable AI features."
                )

            except KeyboardInterrupt:
                console.print("\n[dim]Use /exit to quit[/]")
                try:
                    import time
                    time.sleep(2)
                except KeyboardInterrupt:
                    break
            except EOFError:
                break

        print_session_summary(console, session)
        return

    # Validate path exists
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)

    # Display welcome banner
    print_chat_welcome(console, str(path))
    
    console.print(f"[dim]Indexing codebase:[/] {path}\n")

    agent = FullStackAgent(path)

    with console.status("[dim]Initializing and indexing codebase...[/]"):
        asyncio.run(agent.initialize())
        session.record_tool_call(success=True)

    console.print(f"[{COLORS['success_green']}]✓[/] Codebase indexed successfully")
    
    # Initialize TaskChat if task mode enabled
    task_chat = None
    if task_mode:
        task_chat = TaskChat(path, agent=agent)
        console.print(f"[{COLORS['success_green']}]✓[/] Task mode enabled - use /help for commands\n")
    else:
        console.print("[dim]Task mode disabled - Q&A only\n[/]")

    # Chat history
    history = []
    
    # Task callback for progress
    callback = print_task_callback(console)

    while True:
        try:
            # Get user input with Gemini-style prompt
            message = _get_user_input(console, file)

            if not message:
                continue

            # Handle slash commands and tasks
            if message.startswith("/"):
                if message.lower().strip() in ("/exit", "/quit", "/q"):
                    break
                elif message.lower().strip() == "/help":
                    print_chat_commands(console)
                    continue
                elif task_mode and task_chat:
                    # Route to TaskChat
                    with console.status(f"[{COLORS['warning_yellow']}]![/] Processing..."):
                        response = asyncio.run(task_chat.process(message, callback))
                        session.record_tool_call(success=response.task_result.success if response.task_result else True)
                    
                    if response.is_task and response.task_result:
                        result = response.task_result
                        if result.data.get("needs_approval"):
                            console.print()
                            console.print(response.message)
                            approval = console.input(f"\n[{COLORS['prompt_gray']}]>[/] Execute? ([cyan]y[/]/[red]n[/]): ").strip().lower()
                            if approval != "y":
                                console.print("[yellow]Cancelled[/]")
                        else:
                            print_task_result(console, result.success, result.message if result.success else "Task failed")
                    else:
                        print_agent_response(console, response.message)
                    continue
                else:
                    if _handle_special_command(message, console, agent, history, file, session):
                        continue
                    else:
                        break
            
            # Check for task-like natural language
            if task_mode and task_chat:
                is_task_like = any(kw in message.lower() for kw in ["add", "create", "generate", "remove", "update", "fix"])
                if is_task_like:
                    with console.status(f"[{COLORS['warning_yellow']}]![/] Processing..."):
                        response = asyncio.run(task_chat.process(message, callback))
                    if response.is_task:
                        console.print()
                        console.print(response.message)
                        if response.task_result and response.task_result.data.get("needs_approval"):
                            approval = console.input(f"\n[{COLORS['prompt_gray']}]>[/] Execute? ([cyan]y[/]/[red]n[/]): ").strip().lower()
                            if approval != "y":
                                console.print("[yellow]Cancelled[/]")
                        continue

            # Add to history
            history.append({"role": "user", "content": message})

            # Show thinking indicator with Gemini style
            print_agent_thinking(
                console,
                f"I'll analyze your request and search the codebase for relevant information."
            )
            
            with console.status(f"[{COLORS['warning_yellow']}]![/] Searching codebase..."):
                response = asyncio.run(agent.chat(message, file))
                session.record_tool_call(success=True)
                session.record_tokens(
                    input_tokens=len(message.split()) * 2,
                    output_tokens=len(response.get("response", "").split()) * 2,
                    model="gemini-2.5-pro"
                )

            # Display response with Gemini style
            _display_agent_response(console, response)

            # Add to history
            history.append({"role": "agent", "content": response["response"]})

        except KeyboardInterrupt:
            console.print(
                "\n[dim]Use /exit to quit or press Ctrl+C again to force quit[/]"
            )
            try:
                import time
                time.sleep(2)
            except KeyboardInterrupt:
                break
        except EOFError:
            break

    # Print Gemini-style session summary on exit
    print_session_summary(console, session)


@app.command()
def fullstack(
    frontend_path: Path = typer.Argument(..., help="Path to frontend project"),
    output_dir: Path = typer.Option(
        None, "-o", "--output", help="Output directory (defaults to frontend path)"
    ),
    db_type: str = typer.Option(
        "mysql",
        "-d",
        "--database",
        help="Database type (postgresql, mysql, mongodb, sqlite)",
    ),
    backend_framework: str = typer.Option(
        "fastapi",
        "-b",
        "--backend",
        help="Backend framework (fastapi, django, express, flask)",
    ),
    plan_only: bool = typer.Option(
        False, "--plan", "-p", help="Show plan and exit without generating"
    ),
    auto_approve: bool = typer.Option(
        False, "--yes", "-y", help="Auto-approve plan without prompting"
    ),
):
    """
    Generate synchronized fullstack application with real-time planning.
    
    PROCESS:
    1. 🔮 Real-time Planning → LLM analyzes frontend and builds plan
    2. ✓ User Approval → Review and modify plan before generation
    3. ⚡ Generate → Database + Backend with synchronized models
    
    FLAGS:
        --plan, -p    Show plan only (no generation)
        --yes, -y     Auto-approve plan
    
    Examples:
        # Interactive planning (recommended)
        forge fullstack ./frontend-app
        
        # Preview plan without generating
        forge fullstack ./frontend-app --plan
        
        # Auto-approve for CI/automation
        forge fullstack ./frontend-app --yes
    """
    from cli.ui import LivePlanDisplay, print_plan_summary, print_plan_prompt, print_generation_start
    from orchestration.realtime_planner import RealtimePlanner
    
    # Validate frontend path
    if not validate_path(frontend_path, "Frontend path"):
        raise typer.Exit(1)
    
    # Set default output directory to frontend path if not specified
    if output_dir is None:
        output_dir = frontend_path

    # Validate database and backend framework
    valid_databases = ["postgresql", "mysql", "mongodb", "sqlite"]
    valid_backends = ["fastapi", "django", "express", "flask"]
    
    if db_type.lower() not in valid_databases:
        console.print(f"[red]Error: Invalid database type:[/] {db_type}")
        console.print(f"[dim]Valid options: {', '.join(valid_databases)}[/]")
        raise typer.Exit(1)
    
    if backend_framework.lower() not in valid_backends:
        console.print(f"[red]Error: Invalid backend framework:[/] {backend_framework}")
        console.print(f"[dim]Valid options: {', '.join(valid_backends)}[/]")
        raise typer.Exit(1)

    # Create output directory
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        console.print(f"[red]Error: Failed to create output directory:[/] {e}")
        raise typer.Exit(1)

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 0: REAL-TIME PLANNING
    # ═══════════════════════════════════════════════════════════════════════
    
    config = {
        "database": db_type,
        "framework": backend_framework,
        "output_dir": str(output_dir),
    }
    
    planner = RealtimePlanner(frontend_path, config)
    display = LivePlanDisplay(console)
    
    try:
        # Start planning display
        display.start()
        
        # Create plan with streaming updates
        plan = asyncio.run(planner.create_plan_streaming(display.update))
        
        display.stop()
        
        # Show plan summary
        print_plan_summary(console, plan)
        
        # If plan-only mode, exit here
        if plan_only:
            console.print("\n[dim]Plan-only mode: exiting without generation[/]")
            raise typer.Exit(0)
        
        # Interactive approval loop (unless auto-approve)
        if not auto_approve:
            while True:
                response = print_plan_prompt(console)
                
                if response.lower() == "y":
                    break
                elif response.lower() == "n":
                    console.print("[yellow]Generation cancelled[/]")
                    raise typer.Exit(0)
                else:
                    # User typed a modification request
                    console.print()
                    asyncio.run(planner.add_component(response, display.update))
                    print_plan_summary(console, planner.plan)
        
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1-3: EXECUTE GENERATION
        # ═══════════════════════════════════════════════════════════════════
        
        print_generation_start(console)
        
        # Progress callback for UI updates
        def progress_callback(phase: str, description: str):
            console.print(f"[cyan]{phase}:[/] {description}")

        # Run the synchronized workflow
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating fullstack application...", total=None)

            result = asyncio.run(
                generate_synchronized_fullstack(
                    frontend_path=str(frontend_path),
                    output_dir=str(output_dir),
                    db_type=db_type,
                    backend_framework=backend_framework,
                    plan=planner.plan,  # Pass the approved plan
                    callback=progress_callback,
                )
            )

            progress.update(task, completed=True)

        # Display results
        if result["success"]:
            logger.info(f"Fullstack generation completed: {result['backend'].get('files_created', 0)} backend files, {len(result['database'].get('files', {}))} database files")
            console.print()
            console.print("[bold green]✓ Generation Complete![/]\n")

            # Models summary
            models_count = len(result["models"])
            relations_count = len(result["relations"])
            console.print(
                Panel(
                    f"[white]Models Discovered:[/] {models_count}\n"
                    f"[white]Relationships:[/] {relations_count}\n"
                    f"[white]Database Files:[/] {len(result['database'].get('files', {}))}\n"
                    f"[white]Backend Files:[/] {result['backend'].get('files_created', 0)}\n\n"
                    f"[bold {'green' if result['synchronized'] else 'yellow'}]"
                    f"{'✓ Synchronized!' if result['synchronized'] else '⚠ Verification Failed'}[/]",
                    title="[bold cyan]Generation Summary[/]",
                    border_style="green",
                )
            )

            # Show output structure
            console.print("\n[bold]Generated Files:[/]")
            tree = Tree(f"📁 {output_dir}")
            
            db_tree = tree.add("📁 database")
            for file_type, file_path in result["database"].get("files", {}).items():
                if file_path:
                    db_tree.add(f"📄 {Path(file_path).name}")

            backend_tree = tree.add("📁 backend")
            files_created = result['backend'].get('files_created', 0)
            if files_created > 0:
                backend_tree.add(f"📄 {files_created} files (app/core/, app/models/, app/schemas/, etc.)")
            else:
                backend_tree.add("[dim]No files created[/]")

            console.print(tree)
            console.print()

            # Next steps
            console.print(
                Panel(
                    "[bold]Next Steps:[/]\n\n"
                    f"1. Review schema: [cyan]{output_dir}/database/schema.sql[/]\n"
                    f"2. Run migrations: [cyan]cd {output_dir}/database && psql < schema.sql[/]\n"
                    f"3. Start backend: [cyan]cd {output_dir}/backend && python main.py[/]\n"
                    f"4. Seed data: [cyan]{output_dir}/database/seeds/[/]",
                    title="[bold green]✓ Ready to Deploy[/]",
                    border_style="green",
                )
            )

        else:
            error_msg = result.get('error', 'Unknown error')
            console.print(f"\n[red]✗ Generation failed:[/] {error_msg}")
            logger.error(f"Fullstack generation failed: {error_msg}")
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]! Generation cancelled by user[/]")
        logger.info("Fullstack generation cancelled")
        raise typer.Exit(130)
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Fullstack generation failed")
        console.print(f"\n[red]Error: Unexpected error:[/] {e}")
        console.print("\n[dim]Run with DEBUG=1 for detailed logs[/]")
        raise typer.Exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def _display_stats(stats):
    """Display index statistics."""
    console.print(f"\n[green]✓ Indexing complete![/]")

    table = Table(title="Index Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Files", str(stats.total_files))
    table.add_row("Symbols", str(stats.total_symbols))
    table.add_row("Chunks", str(stats.total_chunks))
    table.add_row("Total Time", f"{stats.index_time_ms:.0f}ms")

    console.print(table)

    if stats.languages:
        lang_table = Table(title="By Language")
        lang_table.add_column("Language")
        lang_table.add_column("Files", justify="right")
        for lang, count in sorted(stats.languages.items(), key=lambda x: -x[1]):
            lang_table.add_row(lang, str(count))
        console.print(lang_table)


def _display_symbols(symbols):
    """Display symbol table."""
    table = Table(title=f"Symbols ({len(symbols)})")
    table.add_column("Name", style="cyan")
    table.add_column("Kind")
    table.add_column("File")
    table.add_column("Line", justify="right")

    for sym in symbols:
        table.add_row(
            sym.name,
            sym.kind.value,
            sym.file.split("/")[-1],
            str(sym.range.start.line + 1),
        )

    console.print(table)


def _display_frontend_analysis(analysis):
    """Display frontend analysis results."""
    console.print(f"\nFramework: [cyan]{analysis.framework.value}[/]")
    console.print(f"Language: [cyan]{analysis.language.value}[/]")

    # API calls
    if analysis.api_calls:
        table = Table(title=f"API Calls ({len(analysis.api_calls)})")
        table.add_column("Method", style="cyan", width=8)
        table.add_column("Endpoint", style="green")
        table.add_column("Auth")

        for api in analysis.api_calls[:15]:
            table.add_row(
                api.method.value, api.endpoint, "🔒" if api.requires_auth else ""
            )

        console.print(table)

    # Data models
    if analysis.data_models:
        table = Table(title=f"Data Models ({len(analysis.data_models)})")
        table.add_column("Name", style="cyan")
        table.add_column("Fields")

        for model in analysis.data_models[:10]:
            fields = ", ".join(f.name for f in model.fields[:5])
            if len(model.fields) > 5:
                fields += f" (+{len(model.fields) - 5})"
            table.add_row(model.name, fields)

        console.print(table)

    # Forms
    if analysis.forms:
        table = Table(title=f"Forms ({len(analysis.forms)})")
        table.add_column("Component", style="cyan")
        table.add_column("Fields")
        table.add_column("Submit")

        for form in analysis.forms[:10]:
            fields = ", ".join(f.name for f in form.fields[:4])
            table.add_row(form.component or "-", fields, form.submit_endpoint or "-")

        console.print(table)

    # Auth
    if analysis.auth:
        console.print(f"\n[bold]Auth:[/] {analysis.auth.type.value}")


async def _generate_backend(agent, callback, dry_run: bool):
    """Generate backend with progress."""
    await agent.initialize(callback)

    if dry_run:
        callback("dry_run", "Generating preview...")
        # In dry run, we'd generate but not apply

    return await agent.generate_backend(callback)


def _enter_post_generation_edit(backend_path: Path, agent, console: Console):
    """Enter edit mode for generated backend code.
    
    Provides Claude Code-style editing capabilities for modifying
    the generated backend with natural language prompts.
    """
    console.print(f"\n[bold cyan]🔧 FORGE Edit Mode[/]")
    console.print(f"[dim]Editing: {backend_path}[/]\n")
    
    console.print("[dim]Commands:[/]")
    console.print("  • Type natural language requests to edit code")
    console.print("  • [cyan]undo[/] - Undo last change")
    console.print("  • [cyan]history[/] - Show action history")
    console.print("  • [cyan]/exit[/] - Exit edit mode")
    console.print()
    
    # Create session tracker
    session = SessionTracker()
    
    # Initialize LLM generator for edit mode
    from generation.llm_generator import LLMGenerator
    llm_gen = LLMGenerator()
    
    # Create agentic loop with the agent for context
    loop = AgenticLoop(
        project_path=backend_path,
        console=console,
        agent=agent,
        llm_generator=llm_gen,
    )
    
    # Main edit loop
    while True:
        try:
            # Get user input
            request = console.input(f"[{COLORS['prompt_gray']}]>[/] ").strip()
            
            if not request:
                continue
            
            # Handle exit
            if request.lower() in ("/exit", "/quit", "/q", "exit", "quit"):
                break
            
            # Process request
            with console.status("[dim]Thinking...[/]"):
                response = asyncio.run(loop.process(request))
            
            # Display response
            if response.message:
                print_agent_response(console, response.message)
            
            # Track for session summary
            for action in response.actions:
                success = action.status.value == "executed"
                session.record_tool_call(success=success)
            
        except KeyboardInterrupt:
            console.print("\n[dim]Use /exit to quit[/]")
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            logging.exception("Edit mode error")
    
    # Show session summary
    print_session_summary(console, session)



async def _watch_loop(agent):
    """Watch for file changes."""
    await agent.start_watching()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        agent.stop_watching()
        console.print("\n[yellow]Stopped watching[/]")


def _display_chat_welcome():
    """Display welcome banner for chat mode."""
    console.print("\n" + "═" * 70)
    console.print("[bold cyan]🤖 FORGE Code Agent - Interactive Mode[/]")
    console.print("═" * 70)
    console.print("\n[dim]Commands:[/]")
    console.print("  [cyan]/help[/]     - Show available commands")
    console.print("  [cyan]/search[/]   - Search codebase")
    console.print("  [cyan]/analyze[/]  - Analyze current file")
    console.print("  [cyan]/generate[/] - Generate code")
    console.print("  [cyan]/clear[/]    - Clear conversation history")
    console.print("  [cyan]/exit[/]     - Exit chat mode")
    console.print("\n[dim]Tips:[/]")
    console.print("  • Press Enter twice to submit multi-line input")
    console.print("  • Use Ctrl+C to interrupt")
    console.print(
        "  • Specify file context with -f flag or mention files in your message"
    )
    console.print("\n" + "═" * 70 + "\n")


def _get_user_input(console, current_file=None) -> str:
    """Get user input with Gemini-style gray '>' prompt."""
    # Use Gemini-style prompt
    prompt = get_user_prompt(current_file)

    # Single line input by default
    try:
        first_line = console.input(f"\n{prompt}")

        if not first_line.strip():
            return ""

        # Check if user wants multi-line (ends with backslash or triple quotes)
        if first_line.strip().endswith("\\") or first_line.strip().startswith("```"):
            lines = [first_line.rstrip("\\")]
            console.print("[dim](Multi-line mode - press Enter twice to submit)[/]")

            empty_count = 0
            while empty_count < 2:
                line = console.input(f"[{COLORS['prompt_gray']}]...[/] ")
                if not line.strip():
                    empty_count += 1
                else:
                    empty_count = 0
                    lines.append(line)

                if line.strip() == "```":
                    break

            return "\n".join(lines).strip()

        return first_line

    except (EOFError, KeyboardInterrupt):
        raise


def _handle_special_command(
    command: str, console, agent, history, current_file, session=None
) -> bool:
    """Handle special commands. Returns True to continue, False to exit."""
    cmd = command.lower().strip()

    if cmd in ("/exit", "/quit", "/q"):
        return False

    elif cmd == "/help":
        console.print("\n[bold]Available Commands:[/]")
        console.print("  [cyan]/help[/]              - Show this help message")
        console.print("  [cyan]/search <query>[/]    - Search codebase semantically")
        console.print("  [cyan]/analyze[/]           - Analyze current file or project")
        console.print("  [cyan]/generate <desc>[/]   - Generate code from description")
        console.print("  [cyan]/symbols <query>[/]   - Search for symbols")
        console.print("  [cyan]/clear[/]             - Clear conversation history")
        console.print("  [cyan]/history[/]           - Show conversation history")
        console.print("  [cyan]/context[/]           - Show current file context")
        console.print("  [cyan]/exit[/]              - Exit chat mode")
        console.print("\n[bold]Natural Language:[/]")
        console.print("  Just type your question or request naturally!")
        console.print("  Examples:")
        console.print('    • "Find all API endpoints"')
        console.print('    • "Generate a user authentication backend"')
        console.print('    • "Explain how the indexer works"')
        console.print('    • "Add a new endpoint for user profile"')

    elif cmd == "/clear":
        history.clear()
        console.print("[green]✓ Conversation history cleared[/]")

    elif cmd == "/history":
        if not history:
            console.print("[dim]No conversation history yet[/]")
        else:
            console.print("\n[bold]Conversation History:[/]")
            for i, entry in enumerate(history, 1):
                role_color = "blue" if entry["role"] == "user" else "green"
                role_name = "You" if entry["role"] == "user" else "Agent"
                console.print(
                    f"\n[{role_color}]{i}. {role_name}:[/] {entry['content'][:100]}..."
                )

    elif cmd == "/context":
        if current_file:
            console.print(f"[cyan]Current file context:[/] {current_file}")
        else:
            console.print(
                "[dim]No file context set. Use -f flag when starting chat.[/]"
            )

    elif cmd == "/search" or cmd.startswith("/search "):
        query = cmd[7:].strip() if len(cmd) > 7 else ""
        if query:
            with console.status("Searching..."):
                results = asyncio.run(agent.search(query, top_k=5))
            console.print(f"\n[green]Found {results.total_count} results[/]")
            for i, result in enumerate(results.results[:5], 1):
                console.print(
                    f"\n{i}. [cyan]{result.chunk.file}[/] L{result.chunk.start_line}-{result.chunk.end_line}"
                )
                console.print(f"   [dim]{result.chunk.content[:150]}...[/]")
        else:
            console.print("[yellow]Usage: /search <query>[/]")

    elif cmd == "/symbols" or cmd.startswith("/symbols "):
        query = cmd[8:].strip() if len(cmd) > 8 else ""
        if query:
            results = agent.search_symbols(query, max_results=10)
            console.print(f"\n[green]Found {len(results)} symbols[/]")
            for sym in results:
                console.print(f"  [cyan]{sym.name}[/] ({sym.kind.value}) - {sym.file}")
        else:
            console.print("[yellow]Usage: /symbols <query>[/]")

    elif cmd == "/analyze":
        with console.status("Analyzing..."):
            analysis = asyncio.run(agent.analyze_frontend())
        _display_frontend_analysis(analysis)

    elif cmd == "/generate" or cmd.startswith("/generate "):
        description = cmd[9:].strip() if len(cmd) > 9 else ""
        if description:
            console.print(f"[cyan]Generating code for:[/] {description}")
            console.print(
                "[dim]This will analyze your frontend and generate matching backend...[/]"
            )
            # This would trigger the generation flow
            console.print("[yellow]Feature coming soon![/]")
        else:
            console.print("[yellow]Usage: /generate <description>[/]")

    else:
        console.print(f"[yellow]Unknown command: {cmd}[/]")
        console.print("[dim]Type /help for available commands[/]")

    return True


def _display_agent_response(console, response: dict):
    """Display agent response with Gemini-style formatting."""
    # Use pink bullet like Gemini CLI
    response_text = response.get('response', '')
    response_text = highlight_file_refs(response_text)
    print_agent_response(console, response_text)

    # Display actions if any with tool-style display
    if response.get("actions"):
        console.print()
        for action in response["actions"]:
            action_type = action.get("type", "unknown")
            print_tool_inline(console, action_type, "", status="success")

    # Display context used if available
    if response.get("context_used"):
        context = response["context_used"]
        if len(context) > 200:
            print_context_info(console, f"Using context: {context[:200]}...")
        else:
            print_context_info(console, f"Using context: {context}")


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE GENERATION COMMANDS  
# ═══════════════════════════════════════════════════════════════════════════


@database_app.command("generate")
def database_generate(
    frontend_path: Path = typer.Argument(..., help="Frontend project path to analyze"),
    output_dir: Path = typer.Option(
        None,
        "-o",
        "--output",
        help="Output directory for database schemas (default: <frontend_path>/database)",
    ),
    db_type: str = typer.Option(
        "postgresql",
        "-d",
        "--database",
        help="Database type: postgresql, mysql, mongodb, sqlite, mariadb",
    ),
    records: int = typer.Option(
        10, "-r", "--records", help="Number of seed data records per model"
    ),
):
    """Generate complete database from frontend analysis.
    
    Workflow:
      1. Analyze frontend components and forms
      2. Infer data models and relationships  
      3. Generate database schema (SQL/NoSQL)
      4. Create migrations
      5. Generate seed data
      
    Example:
      forge database generate ./frontend -d postgresql -o ./db_output
    """
    if not frontend_path.exists():
        console.print(f"[red]Error: Frontend path not found: {frontend_path}[/]")
        raise typer.Exit(1)

    # Set default output directory to frontend_path/database if not specified
    if output_dir is None:
        output_dir = frontend_path / "database"

    console.print("\n[bold cyan]🗄️  FORGE Database Generator[/]\n")
    console.print(f"[cyan]Frontend:[/] {frontend_path}")
    console.print(f"[cyan]Database:[/] {db_type.upper()}")
    console.print(f"[cyan]Output:[/] {output_dir}\n")

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as prog:
        task = prog.add_task("Initializing...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        # Import and initialize
        from config.settings import settings
        from database_generation.orchestrator import DatabaseOrchestrator

        orchestrator = DatabaseOrchestrator(frontend_path, output_dir, settings)

        # Generate database
        result = asyncio.run(
            orchestrator.generate_database(
                db_type=db_type,
                skip_frontend=False,
                records_per_model=records,
                callback=callback,
            )
        )

        prog.update(task, description="[green]✓ Generation complete![/]")

    # Display results
    if result["success"]:
        console.print("\n[green]✅ Database generated successfully![/]\n")

        summary = Table(show_header=False, box=None, padding=(0, 2))
        summary.add_column("Item", style="cyan bold")
        summary.add_column("Value", style="white")

        summary.add_row("📁 Output Directory", str(output_dir))
        summary.add_row("🗄️  Database Type", db_type.upper())
        summary.add_row("📊 Models Generated", str(len(result["models"])))
        summary.add_row("🔗 Relationships", str(len(result["relations"])))

        if "schema" in result["files"]:
            schema_files = result["files"]["schema"]
            if isinstance(schema_files, dict):
                summary.add_row("📝 Schema Files", ", ".join(schema_files.keys()))
            else:
                summary.add_row("📝 Schema File", schema_files.name)

        if "migration" in result["files"]:
            summary.add_row("🔄 Migration", result["files"]["migration"].name)

        if "seeds" in result["files"]:
            summary.add_row(
                "🌱 Seed Files", f"{len(result['files']['seeds'])} models"
            )

        console.print(Panel(summary, title="[bold]Generation Summary[/]", border_style="green"))

        # Show next steps
        console.print("\n[bold yellow]Next Steps:[/]")
        console.print(f"  1. Review schema: {output_dir}/schema.sql")
        console.print(f"  2. Create database:")
        console.print(f'     [dim]forge database create "{output_dir}/schema.sql" -c "postgresql://user:pass@localhost" -n mydb[/]')
        console.print(f"  3. Load seed data:")
        console.print(f'     [dim]forge database seed "{output_dir}/seeds" -c "postgresql://user:pass@localhost" -n mydb[/]')

    else:
        console.print("[red]❌ Generation failed![/]")
        for error in result["errors"]:
            console.print(f"  [red]• {error}[/]")
        raise typer.Exit(1)


@database_app.command("create")
def database_create(
    schema_path: Path = typer.Argument(..., help="Path to schema.sql file"),
    connection_string: str = typer.Option(
        ..., "-c", "--connection", help='Database connection string (e.g., "postgresql://user:pass@localhost")'
    ),
    db_name: str = typer.Option(..., "-n", "--name", help="Database name to create"),
):
    """Create actual database from generated schema.
    
    Example:
      forge database create schema.sql -c "postgresql://user:pass@localhost" -n myapp_db
    """
    if not schema_path.exists():
        console.print(f"[red]Error: Schema file not found: {schema_path}[/]")
        raise typer.Exit(1)

    console.print(f"\n[cyan]Creating database:[/] {db_name}")
    console.print(f"[cyan]Using schema:[/] {schema_path}\n")

    with console.status("[cyan]Creating database...[/]"):
        from database_generation.database_manager import DatabaseManager

        db_manager = DatabaseManager(connection_string)

        # Create database
        asyncio.run(db_manager.create_database(db_name))

        # Execute schema
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        asyncio.run(db_manager.connect(db_name))
        asyncio.run(db_manager.execute_sql(schema_sql))
        asyncio.run(db_manager.close())

    console.print(f"\n[green]✅ Database '{db_name}' created successfully![/]")


@database_app.command("seed")
def database_seed(
    seed_path: Path = typer.Argument(..., help="Path to seed data directory"),
    connection_string: str = typer.Option(
        ..., "-c", "--connection", help='Database connection string (e.g., "postgresql://user:pass@localhost")'
    ),
    db_name: str = typer.Option(..., "-n", "--name", help="Database name"),
):
    """Load seed data into database.
    
    Example:
      forge database seed ./seeds -c "postgresql://user:pass@localhost" -n myapp_db
    """
    if not seed_path.exists():
        console.print(f"[red]Error: Seed data path not found: {seed_path}[/]")
        raise typer.Exit(1)

    console.print(f"\n[cyan]Loading seed data into:[/] {db_name}\n")

    with console.status("[cyan]Loading seed data...[/]"):
        from database_generation.database_manager import DatabaseManager

        db_manager = DatabaseManager(connection_string)
        asyncio.run(db_manager.connect(db_name))

        # Execute all seed files
        for seed_file in sorted(seed_path.glob("*.sql")):
            console.print(f"  [dim]Loading: {seed_file.name}[/]")
            with open(seed_file, "r", encoding="utf-8") as f:
                seed_sql = f.read()
            asyncio.run(db_manager.execute_sql(seed_sql))

        asyncio.run(db_manager.close())

    console.print(f"\n[green]✅ Seed data loaded successfully![/]")


@database_app.command("chat")
def database_chat(
    frontend_path: Path = typer.Argument(..., help="Path to frontend project"),
    db_type: DatabaseType = typer.Option(DatabaseType.POSTGRESQL, "-t", "--type", help="Database type"),
):
    """Interactive chat mode for database schema design.
    
    Chat with AI agents to design optimal database schemas. Get expert advice
    from LeadArchitect, DataModeler, DBAExpert, and SQLWriter agents.
    
    Example:
      forge database chat ./frontend -t postgresql
    """
    if not frontend_path.exists():
        console.print(f"[red]Error: Frontend path not found: {frontend_path}[/]")
        raise typer.Exit(1)
    
    console.print("\n[bold cyan]🤖 Database Design Chat Mode[/]\n")
    console.print("[dim]Chat with AI agents to design your database schema[/]\n")
    
    from database_generation.chat import ChatAssistant, ChatSession
    import uuid
    
    # Create assistant and session with proper API
    assistant = ChatAssistant(use_ai=True)
    session = assistant.create_session()
    session.target_database = db_type.value
    
    console.print("[yellow]Type 'help' for commands, 'exit' to quit[/]\n")
    
    while True:
        try:
            user_input = typer.prompt("\n💬 You", default="")
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("\n[cyan]Goodbye! 👋[/]")
                break
            
            if not user_input.strip():
                continue
                
            response = assistant.chat(user_input, session)
            console.print(f"\n[bold green]🤖 Assistant:[/] {response.get('message', 'No response')}\n")
            
        except KeyboardInterrupt:
            console.print("\n\n[cyan]Goodbye! 👋[/]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/]")


@database_app.command("edit")
def database_edit(
    schema_path: Path = typer.Argument(..., help="Path to schema JSON file"),
    interactive: bool = typer.Option(True, "-i", "--interactive", help="Interactive editing mode"),
):
    """Edit database schema interactively.
    
    Visual schema editor with validation, suggestions, and real-time feedback.
    
    Example:
      forge database edit ./schema.json -i
    """
    if not schema_path.exists():
        console.print(f"[red]Error: Schema file not found: {schema_path}[/]")
        raise typer.Exit(1)
    
    console.print("\n[bold cyan]📝 Schema Editor[/]\n")
    
    from database_generation.editor import SchemaEditor, InteractiveEditor
    from database_generation.db_types import ForgeSchema
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_data = json.load(f)
    
    # Convert dict to ForgeSchema if needed
    if isinstance(schema_data, dict):
        schema = ForgeSchema(**schema_data)
    else:
        schema = schema_data
    
    editor = SchemaEditor(schema)
    
    if interactive:
        interactive_editor = InteractiveEditor(schema)
        interactive_editor.run()
    else:
        # Show schema summary
        console.print(f"[dim]Schema: {len(schema.entities)} entities[/]")
        for entity in schema.entities[:5]:
            console.print(f"  - {entity.name}: {len(entity.fields)} fields")
    
    # Save changes
    save = typer.confirm("\n💾 Save changes?")
    if save:
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema.model_dump(), f, indent=2, default=str)
        console.print(f"\n[green]✅ Schema saved to {schema_path}[/]")


@database_app.command("optimize")
def database_optimize(
    schema_path: Path = typer.Argument(..., help="Path to schema JSON file"),
    db_type: DatabaseType = typer.Option(DatabaseType.POSTGRESQL, "-t", "--type", help="Database type"),
    output: Path = typer.Option(None, "-o", "--output", help="Output path for optimized schema"),
):
    """AI-powered schema optimization.
    
    Use AI to analyze and optimize database schema for performance,
    normalization, indexing, and best practices.
    
    Example:
      forge database optimize ./schema.json -t postgresql -o ./schema_optimized.json
    """
    if not schema_path.exists():
        console.print(f"[red]Error: Schema file not found: {schema_path}[/]")
        raise typer.Exit(1)
    
    console.print("\n[bold cyan]🚀 AI Schema Optimization[/]\n")
    
    from database_generation.engine import AIEngine, SchemaBuilder
    from database_generation.db_types import DatabaseType as DBType
    
    with console.status("[cyan]Loading schema...[/]"):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
    
    # Convert to ForgeSchema
    if isinstance(schema_data, dict):
        from database_generation.db_types import ForgeSchema
        schema = ForgeSchema(**schema_data)
    else:
        schema = schema_data
    
    with console.status("[cyan]Analyzing schema with AI...[/]"):
        # Build schema for target database
        builder = SchemaBuilder()
        db_enum = DBType(db_type.value.lower())
        result = builder.build(schema, db_enum)
        
        console.print(f"\n[green]✅ Schema built for {db_type.value}[/]")
        console.print(f"[dim]Entities: {result.entities_count}, Indexes: {result.indexes_count}[/]")
        
        if result.warnings:
            console.print("\n[yellow]⚠️  Warnings:[/]")
            for warning in result.warnings:
                console.print(f"  - {warning}")
        
        # Show DDL preview
        if result.ddl:
            console.print("\n[bold cyan]Generated DDL (preview):[/]")
            console.print(result.ddl[:500] + "..." if len(result.ddl) > 500 else result.ddl)
    
    # Save schema
    output_path = output or schema_path.parent / f"{schema_path.stem}_generated.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema.model_dump(), f, indent=2, default=str)
    
    console.print(f"\n[green]✅ Schema saved to {output_path}[/]")


@database_app.command("mcp")
def database_mcp(
    action: str = typer.Argument(..., help="Action: start, stop, status"),
    db_type: str = typer.Option("postgresql", "-t", "--type", help="Database type: postgresql, mysql, mongodb"),
    port: int = typer.Option(5000, "-p", "--port", help="MCP server port"),
):
    """Manage Model Context Protocol (MCP) servers.
    
    Start MCP servers for database integration with AI agents and external tools.
    
    Examples:
      forge database mcp start -t postgresql -p 5000
      forge database mcp status
      forge database mcp stop
    """
    from database_generation.mcp import MCPHub
    
    hub = MCPHub()
    
    if action == "start":
        console.print(f"\n[cyan]Starting MCP server for {db_type}...[/]\n")
        asyncio.run(hub.start_server(db_type, port))
        console.print(f"\n[green]✅ MCP server running on port {port}[/]")
        
    elif action == "stop":
        console.print(f"\n[cyan]Stopping MCP servers...[/]\n")
        asyncio.run(hub.stop_all())
        console.print(f"\n[green]✅ All MCP servers stopped[/]")
        
    elif action == "status":
        status = asyncio.run(hub.get_status())
        console.print("\n[bold cyan]MCP Server Status:[/]\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Database")
        table.add_column("Status")
        table.add_column("Port")
        
        for db, info in status.items():
            table.add_row(
                db,
                "[green]Running[/]" if info["running"] else "[dim]Stopped[/]",
                str(info.get("port", "-"))
            )
        
        console.print(table)
    else:
        console.print(f"[red]Unknown action: {action}[/]")
        console.print("[yellow]Available actions: start, stop, status[/]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🚀 FORGE - AI-Powered Full-Stack Code Generation System"""
    if ctx.invoked_subcommand is None:
        show_banner()

        # Show available commands in a nice panel
        commands_table = Table(show_header=False, box=None, padding=(0, 2))
        commands_table.add_column("Command", style="cyan bold", width=35)
        commands_table.add_column("Description")

        # Setup & Config
        commands_table.add_row("[bold yellow]Setup & Config[/]", "")
        commands_table.add_row("setup", "Interactive configuration wizard")
        commands_table.add_row("stats", "Show usage statistics & costs")
        commands_table.add_row("help [section]", "Detailed help & documentation")
        commands_table.add_row("init [path]", "Initialize new project")
        commands_table.add_row("status [path]", "Show project status")
        commands_table.add_row("", "")

        # Database Generation  
        commands_table.add_row("[bold yellow]Database Generation[/]", "")
        commands_table.add_row(
            "database generate <path>", "Generate schema from frontend"
        )
        commands_table.add_row(
            "database create <schema>", "Create database from schema"
        )
        commands_table.add_row("database seed <path>", "Load seed data")
        commands_table.add_row("database chat <path>", "Interactive schema design")
        commands_table.add_row("database edit <schema>", "Visual schema editor")
        commands_table.add_row("database optimize <schema>", "AI-powered optimization")
        commands_table.add_row("database mcp <action>", "Manage MCP servers")
        commands_table.add_row("", "")

        # Backend Generation
        commands_table.add_row("[bold yellow]Backend Generation[/]", "")
        commands_table.add_row(
            "backend analyze <path>", "Analyze frontend architecture"
        )
        commands_table.add_row(
            "backend generate <path>", "Generate backend from frontend"
        )
        commands_table.add_row(
            "backend review <path>", "Review code quality & security"
        )
        commands_table.add_row("backend debug <path>", "Debug code with AI assistance")
        commands_table.add_row(
            "backend fix <path> -f <file>", "Auto-fix detected issues"
        )
        commands_table.add_row("backend add-model <path> <name>", "Add new data model")
        commands_table.add_row("backend add-endpoint <path>", "Add API endpoint")
        commands_table.add_row("backend sync <path>", "Sync with frontend changes")
        commands_table.add_row("backend rollback <path>", "Rollback last change")
        commands_table.add_row("", "")

        # Code Indexing
        commands_table.add_row("[bold yellow]Code Indexing[/]", "")
        commands_table.add_row("index run <path>", "Index project for semantic search")
        commands_table.add_row(
            "index search <path> <query>", "Search code semantically"
        )
        commands_table.add_row("index symbols <path>", "List symbols in project")
        commands_table.add_row("", "")

        # Interactive
        commands_table.add_row("[bold yellow]Interactive[/]", "")
        commands_table.add_row("chat <path>", "Chat with codebase")
        commands_table.add_row("edit <path>", "Agentic edit mode - edit with natural language")
        commands_table.add_row("", "")

        # Fullstack (NEW)
        commands_table.add_row("[bold yellow]Synchronized Fullstack[/]", "")
        commands_table.add_row(
            "fullstack <frontend> [options]",
            "Generate synchronized database + backend from frontend"
        )

        console.print(
            Panel(
                commands_table,
                title="[bold]All Commands (32 Total)[/]",
                border_style="cyan",
                padding=(1, 2),
            )
        )


if __name__ == "__main__":
    app()
