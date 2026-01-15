"""Extended CLI with backend generation commands."""

import asyncio
import json
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown
from rich.tree import Tree

from agent import CodeAgent
from backend_agent import BackendAgent, GenerationMode
from fullstack_agent import FullStackAgent
from config.templates_config import TemplateConfig, BackendFramework, DatabaseType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ASCII Art Banner
BANNER = """
[bold cyan]
   ███████╗ ██████╗ ██████╗  ██████╗ ███████╗
   ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
   █████╗  ██║   ██║██████╔╝██║  ███╗█████╗  
   ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  
   ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
   ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
[/]
[dim]   AI-Powered Full-Stack Code Generation System[/]
"""

def show_banner():
    """Display the FORGE banner."""
    console.print(BANNER)
    console.print()

app = typer.Typer(
    name="forge",
    help="🚀 FORGE - AI-Powered Full-Stack Code Generation System",
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False
)
console = Console()

# Sub-commands
index_app = typer.Typer(
    help="📁 [cyan]Code indexing[/] - Semantic search and navigation",
    rich_markup_mode="rich"
)
backend_app = typer.Typer(
    help="⚙️ [cyan]Backend generation[/] - Generate, review, and debug backend code",
    rich_markup_mode="rich"
)
app.add_typer(index_app, name="index")
app.add_typer(backend_app, name="backend")

# Cache for agents to avoid re-initialization
_agent_cache = {}


# ═══════════════════════════════════════════════════════════════════════════
# INDEX COMMANDS
# ═══════════════════════════════════════════════════════════════════════════

@index_app.command("run")
def index_run(
    path: Path = typer.Argument(..., help="Project path to index"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch for changes")
):
    """Index a project with semantic search capabilities."""
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)

    agent = CodeAgent(path)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
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
    console.print(f"[dim]Found {response.total_count} results in {response.search_time_ms:.0f}ms[/]\n")

    for i, result in enumerate(response.results, 1):
        chunk = result.chunk
        title = f"[cyan]{chunk.file}[/] L{chunk.start_line + 1}-{chunk.end_line + 1}"
        if chunk.symbol_name:
            title += f" ([yellow]{chunk.symbol_name}[/])"

        console.print(Panel(
            Syntax(
                chunk.content[:500] + ("..." if len(chunk.content) > 500 else ""),
                chunk.language,
                theme="monokai",
                line_numbers=True,
                start_line=chunk.start_line + 1
            ),
            title=title,
            subtitle=f"Score: {result.score:.3f}"
        ))


@index_app.command("symbols")
def index_symbols(
    path: Path = typer.Argument(..., help="Project path"),
    query: str = typer.Argument("", help="Search query"),
    kind: str = typer.Option(None, "-k", "--kind", help="Filter by kind"),
    limit: int = typer.Option(20, "-n", "--limit", help="Max results")
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
    framework: str = typer.Option("express", "-f", "--framework", help="Backend framework"),
    database: str = typer.Option("postgresql", "-d", "--database", help="Database type"),
    mode: str = typer.Option("hybrid", "-m", "--mode", help="Generation mode: single, multi, hybrid"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without applying"),
):
    """Generate backend from frontend analysis.
    
    Modes:
      single - Fast single-agent mode (1-2 min, good for MVPs)
      multi  - Production multi-agent mode (5-10 min, 8 specialized agents)
      hybrid - Auto-select based on project complexity (default)
    """
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)

    # Parse generation mode
    mode_map = {
        "single": GenerationMode.SINGLE_AGENT,
        "multi": GenerationMode.MULTI_AGENT,
        "hybrid": GenerationMode.HYBRID
    }
    
    if mode.lower() not in mode_map:
        console.print(f"[red]Error: Invalid mode '{mode}'. Use: single, multi, or hybrid[/]")
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
        output_dir=str(output) if output else "backend"
    )

    agent = FullStackAgent(path, config)
    
    # Set generation mode
    agent.backend_agent.set_generation_mode(generation_mode)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
        task = prog.add_task("Initializing...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        result = asyncio.run(_generate_backend(agent, callback, dry_run))

    if result.success:
        console.print(f"\n[green]✓ Backend generation complete![/]")
        
        # Show mode used
        if generation_mode == GenerationMode.HYBRID:
            complexity = agent.backend_agent._assess_project_complexity()
            actual_mode = "multi-agent" if complexity in ["medium", "high"] else "single-agent"
            console.print(f"[dim]Mode used: {actual_mode} (complexity: {complexity})[/]")
        
        # Show collaboration report for multi-agent
        if generation_mode == GenerationMode.MULTI_AGENT or (generation_mode == GenerationMode.HYBRID and complexity in ["medium", "high"]):
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
        console.print(f"\n[red]✗ Generation failed[/]")
        for error in result.errors:
            console.print(f"  [red]• {error}[/]")


@backend_app.command("analyze")
def backend_analyze(
    path: Path = typer.Argument(..., help="Project path"),
    reindex: bool = typer.Option(False, "--reindex", help="Force re-indexing")
):
    """Analyze frontend and show inferred backend architecture."""
    agent = FullStackAgent(path)

    # Check if already indexed
    codegen_dir = path / ".codegen"
    index_exists = (codegen_dir / "vectorstore").exists() if codegen_dir.exists() else False
    
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
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
    fields: str = typer.Option("", "-f", "--fields", help="Fields as JSON array or path to JSON file"),
    reindex: bool = typer.Option(False, "--reindex", help="Force re-indexing")
):
    """Add a new model to the backend."""
    # Use cached agent if available
    cache_key = str(path.resolve())
    if cache_key not in _agent_cache or reindex:
        agent = FullStackAgent(path)
        _agent_cache[cache_key] = agent
    else:
        agent = _agent_cache[cache_key]
    
    status_msg = "Re-indexing..." if reindex else ("Loading cached index..." if cache_key in _agent_cache else "Initializing...")
    with console.status(status_msg):
        asyncio.run(agent.initialize(force_reindex=reindex))

    # Parse fields
    field_list = []
    if fields:
        try:
            # Check if it's a file path
            if fields.endswith('.json') and Path(fields).exists():
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
                if not isinstance(field, dict) or 'name' not in field or 'type' not in field:
                    raise ValueError("Each field must have 'name' and 'type' properties")
        except (json.JSONDecodeError, ValueError) as e:
            console.print(f"[red]Invalid fields JSON: {e}[/]")
            console.print(f"[yellow]Expected format: '[{{\"name\":\"field1\",\"type\":\"string\"}}]'[/]")
            console.print(f"[yellow]Or provide a path to JSON file: -f fields.json[/]")
            console.print(f"[yellow]Example: -f '[{{\"name\":\"id\",\"type\":\"string\"}},{{\"name\":\"title\",\"type\":\"string\"}}]'[/]")
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
    reindex: bool = typer.Option(False, "--reindex", help="Force re-indexing")
):
    """Add a new API endpoint."""
    # Use cached agent if available
    cache_key = str(path.resolve())
    if cache_key not in _agent_cache or reindex:
        agent = FullStackAgent(path)
        _agent_cache[cache_key] = agent
    else:
        agent = _agent_cache[cache_key]
    
    status_msg = "Re-indexing..." if reindex else ("Loading cached index..." if cache_key in _agent_cache else "Initializing...")
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

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
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
    output: str = typer.Option(None, "-o", "--output", help="Output file for review report"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed analysis"),
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

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
        task = prog.add_task("Initializing code review...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        # Import generator and perform review
        from generation.llm_generator import LLMGenerator
        from config.settings import settings
        
        llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
        # Collect backend files
        prog.update(task, description="Scanning backend files...")
        backend_files = []
        code_content = []
        
        for ext in ['.py', '.js', '.ts', '.java', '.go', '.rs']:
            for file in path.rglob(f'*{ext}'):
                if 'node_modules' not in str(file) and '__pycache__' not in str(file):
                    backend_files.append(file)
                    try:
                        content = file.read_text(encoding='utf-8', errors='ignore')
                        if len(content) < 10000:  # Limit file size
                            code_content.append(f"### {file.relative_to(path)}\n```\n{content[:3000]}\n```")
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
        
        review_result = asyncio.run(llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        ))

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
):
    """Debug backend code issues with AI assistance.
    
    Modes:
      - Provide an error message to get fix suggestions
      - Specify a file and line for targeted analysis
      - Run without options for general issue detection
    """
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)

    console.print(f"[cyan]Debugging backend at:[/] {path}\n")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
        task = prog.add_task("Initializing debugger...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        from generation.llm_generator import LLMGenerator
        from config.settings import settings
        
        llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
        # Get relevant code context
        code_context = ""
        
        if file:
            file_path = path / file
            if file_path.exists():
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if line:
                    lines = content.split('\n')
                    start = max(0, line - 15)
                    end = min(len(lines), line + 15)
                    code_context = f"File: {file} (around line {line})\n```\n"
                    for i in range(start, end):
                        marker = ">>> " if i + 1 == line else "    "
                        code_context += f"{marker}{i+1}: {lines[i]}\n"
                    code_context += "```"
                else:
                    code_context = f"File: {file}\n```\n{content[:5000]}\n```"
            else:
                console.print(f"[red]File not found: {file}[/]")
                raise typer.Exit(1)
        else:
            # Collect recent/relevant files
            prog.update(task, description="Scanning for potential issues...")
            for ext in ['.py', '.js', '.ts']:
                for f in list(path.rglob(f'*{ext}'))[:5]:
                    if 'node_modules' not in str(f):
                        try:
                            content = f.read_text(encoding='utf-8', errors='ignore')
                            code_context += f"\n### {f.relative_to(path)}\n```\n{content[:2000]}\n```"
                        except:
                            pass
        
        prog.update(task, description="Analyzing code for issues...")
        
        if error:
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
        
        debug_result = asyncio.run(llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        ))

    # Display results
    console.print("\n" + "═" * 70)
    console.print("[bold cyan]🔍 DEBUG ANALYSIS[/]")
    console.print("═" * 70 + "\n")
    
    if error:
        console.print(f"[red]Error:[/] {error[:100]}...\n" if len(error) > 100 else f"[red]Error:[/] {error}\n")
    
    console.print(Markdown(debug_result))
    
    console.print(f"\n[dim]Debug analysis complete[/]")


# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL COMMANDS
# ═══════════════════════════════════════════════════════════════════════════

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
        "features": {
            "docker": True,
            "testing": True,
            "swagger": True
        }
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
    backend_dir = path / config.get('output_dir', 'backend')
    if backend_dir.exists():
        file_count = sum(1 for _ in backend_dir.rglob('*') if _.is_file())
        console.print(f"\n[bold]Backend:[/] {file_count} files in {backend_dir}")
    else:
        console.print(f"\n[bold]Backend:[/] Not generated yet")

    # Check sessions
    sessions_dir = codegen_dir / "sessions"
    if sessions_dir.exists():
        session_count = len(list(sessions_dir.glob('*.json')))
        console.print(f"\n[bold]Sessions:[/] {session_count}")

    # Check checkpoints
    checkpoints_dir = codegen_dir / "checkpoints"
    if checkpoints_dir.exists():
        checkpoint_count = len(list(checkpoints_dir.glob('*')))
        console.print(f"[bold]Checkpoints:[/] {checkpoint_count}")


@app.command()
def chat(
    path: Path = typer.Argument(None, help="Codebase path to index and chat about"),
    file: str = typer.Option(None, "-f", "--file", help="Current file context"),
):
    """Interactive chat with the code agent - provide a codebase path to index."""
    
    if path is None:
        console.print("[yellow]⚠ No codebase path provided - running in no-index mode[/]")
        console.print("[dim]Usage: python main.py chat <path-to-codebase>[/]\n")
        _display_chat_welcome()
        console.print("\n[dim]No-index mode: Only natural language chat available[/]\n")
        
        # Simple chat loop without agent
        while True:
            try:
                message = _get_user_input(console, file)
                if not message:
                    continue
                
                if message.startswith('/'):
                    if message.lower().strip() in ('/exit', '/quit', '/q'):
                        break
                    elif message.lower().strip() == '/help':
                        console.print("\n[yellow]No-index mode - Limited commands:[/]")
                        console.print("  [cyan]/exit[/] - Exit chat")
                        console.print("\n[dim]Tip: Provide a codebase path to enable full features:[/]")
                        console.print("[dim]  python main.py chat <path-to-your-codebase>[/]")
                    else:
                        console.print("[yellow]Command not available in no-index mode[/]")
                    continue
                
                console.print(f"\n[bold green]🤖 Agent >[/] No-index mode: Provide a codebase path to enable AI features.")
                console.print(f"[dim]Usage: python main.py chat <path-to-your-codebase>[/]")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit[/]")
                try:
                    import time
                    time.sleep(2)
                except KeyboardInterrupt:
                    break
            except EOFError:
                break
        
        console.print("\n[yellow]👋 Goodbye![/]")
        return
    
    # Validate path exists
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Indexing codebase:[/] {path}\n")
    
    agent = FullStackAgent(path)

    with console.status("Initializing and indexing codebase..."):
        asyncio.run(agent.initialize())

    # Display welcome banner
    _display_chat_welcome()

    # Chat history
    history = []
    
    while True:
        try:
            # Get user input with enhanced prompt
            message = _get_user_input(console, file)
            
            if not message:
                continue

            # Handle special commands
            if message.startswith('/'):
                if _handle_special_command(message, console, agent, history, file):
                    continue
                else:
                    break

            # Add to history
            history.append({'role': 'user', 'content': message})

            # Show thinking indicator
            with console.status("[cyan]Thinking..."):
                response = asyncio.run(agent.chat(message, file))

            # Display response
            _display_agent_response(console, response)

            # Add to history
            history.append({'role': 'agent', 'content': response['response']})

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /exit to quit or press Ctrl+C again to force quit[/]")
            try:
                import time
                time.sleep(2)
            except KeyboardInterrupt:
                break
        except EOFError:
            break

    console.print("\n[yellow]👋 Goodbye![/]")


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
            sym.file.split('/')[-1],
            str(sym.range.start.line + 1)
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
                api.method.value,
                api.endpoint,
                "🔒" if api.requires_auth else ""
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
            table.add_row(
                form.component or "-",
                fields,
                form.submit_endpoint or "-"
            )

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
    console.print("  • Specify file context with -f flag or mention files in your message")
    console.print("\n" + "═" * 70 + "\n")


def _get_user_input(console, current_file=None) -> str:
    """Get user input with enhanced prompt."""
    context_indicator = f"[dim]({current_file})[/] " if current_file else ""
    
    # Single line input by default
    try:
        first_line = console.input(f"\n{context_indicator}[bold blue]You >[/] ")
        
        if not first_line.strip():
            return ""
        
        # Check if user wants multi-line (ends with backslash or triple quotes)
        if first_line.strip().endswith('\\') or first_line.strip().startswith('```'):
            lines = [first_line.rstrip('\\')]
            console.print("[dim](Multi-line mode - press Enter twice to submit)[/]")
            
            empty_count = 0
            while empty_count < 2:
                line = console.input("[blue]...[/] ")
                if not line.strip():
                    empty_count += 1
                else:
                    empty_count = 0
                    lines.append(line)
                
                if line.strip() == '```':
                    break
            
            return '\n'.join(lines).strip()
        
        return first_line
        
    except (EOFError, KeyboardInterrupt):
        raise


def _handle_special_command(command: str, console, agent, history, current_file) -> bool:
    """Handle special commands. Returns True to continue, False to exit."""
    cmd = command.lower().strip()
    
    if cmd in ('/exit', '/quit', '/q'):
        return False
    
    elif cmd == '/help':
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
        console.print("    • \"Find all API endpoints\"")
        console.print("    • \"Generate a user authentication backend\"")
        console.print("    • \"Explain how the indexer works\"")
        console.print("    • \"Add a new endpoint for user profile\"")
    
    elif cmd == '/clear':
        history.clear()
        console.print("[green]✓ Conversation history cleared[/]")
    
    elif cmd == '/history':
        if not history:
            console.print("[dim]No conversation history yet[/]")
        else:
            console.print("\n[bold]Conversation History:[/]")
            for i, entry in enumerate(history, 1):
                role_color = "blue" if entry['role'] == 'user' else "green"
                role_name = "You" if entry['role'] == 'user' else "Agent"
                console.print(f"\n[{role_color}]{i}. {role_name}:[/] {entry['content'][:100]}...")
    
    elif cmd == '/context':
        if current_file:
            console.print(f"[cyan]Current file context:[/] {current_file}")
        else:
            console.print("[dim]No file context set. Use -f flag when starting chat.[/]")
    
    elif cmd == '/search' or cmd.startswith('/search '):
        query = cmd[7:].strip() if len(cmd) > 7 else ""
        if query:
            with console.status("Searching..."):
                results = asyncio.run(agent.search(query, top_k=5))
            console.print(f"\n[green]Found {results.total_count} results[/]")
            for i, result in enumerate(results.results[:5], 1):
                console.print(f"\n{i}. [cyan]{result.chunk.file}[/] L{result.chunk.start_line}-{result.chunk.end_line}")
                console.print(f"   [dim]{result.chunk.content[:150]}...[/]")
        else:
            console.print("[yellow]Usage: /search <query>[/]")
    
    elif cmd == '/symbols' or cmd.startswith('/symbols '):
        query = cmd[8:].strip() if len(cmd) > 8 else ""
        if query:
            results = agent.search_symbols(query, max_results=10)
            console.print(f"\n[green]Found {len(results)} symbols[/]")
            for sym in results:
                console.print(f"  [cyan]{sym.name}[/] ({sym.kind.value}) - {sym.file}")
        else:
            console.print("[yellow]Usage: /symbols <query>[/]")
    
    elif cmd == '/analyze':
        with console.status("Analyzing..."):
            analysis = asyncio.run(agent.analyze_frontend())
        _display_frontend_analysis(analysis)
    
    elif cmd == '/generate' or cmd.startswith('/generate '):
        description = cmd[9:].strip() if len(cmd) > 9 else ""
        if description:
            console.print(f"[cyan]Generating code for:[/] {description}")
            console.print("[dim]This will analyze your frontend and generate matching backend...[/]")
            # This would trigger the generation flow
            console.print("[yellow]Feature coming soon![/]")
        else:
            console.print("[yellow]Usage: /generate <description>[/]")
    
    else:
        console.print(f"[yellow]Unknown command: {cmd}[/]")
        console.print("[dim]Type /help for available commands[/]")
    
    return True


def _display_agent_response(console, response: dict):
    """Display agent response with rich formatting."""
    console.print(f"\n[bold green]🤖 Agent >[/] {response['response']}")
    
    # Display actions if any
    if response.get('actions'):
        console.print("\n[dim]Actions:[/]")
        for action in response['actions']:
            action_type = action.get('type', 'unknown')
            console.print(f"  [cyan]→[/] {action_type}")
    
    # Display context used if available
    if response.get('context_used'):
        context = response['context_used']
        if len(context) > 200:
            console.print(f"\n[dim]Context: {context[:200]}...[/]")
        else:
            console.print(f"\n[dim]Context: {context}[/]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🚀 FORGE - AI-Powered Full-Stack Code Generation System"""
    if ctx.invoked_subcommand is None:
        show_banner()
        
        # Show available commands in a nice panel
        commands_table = Table(show_header=False, box=None, padding=(0, 2))
        commands_table.add_column("Command", style="cyan bold")
        commands_table.add_column("Description")
        
        commands_table.add_row("index run <path>", "Index a project for semantic search")
        commands_table.add_row("index search <path> <query>", "Search code semantically")
        commands_table.add_row("index symbols <path>", "List symbols in project")
        commands_table.add_row("", "")
        commands_table.add_row("backend generate <path>", "Generate backend from frontend")
        commands_table.add_row("backend analyze <path>", "Analyze frontend architecture")
        commands_table.add_row("backend review <path>", "Review code quality & security")
        commands_table.add_row("backend debug <path>", "Debug code with AI assistance")
        commands_table.add_row("", "")
        commands_table.add_row("chat <path>", "Interactive chat with codebase")
        commands_table.add_row("init [path]", "Initialize new project")
        commands_table.add_row("status [path]", "Show project status")
        
        console.print(Panel(
            commands_table,
            title="[bold]📋 Available Commands[/]",
            border_style="cyan",
            padding=(1, 2)
        ))
        
        console.print("\n[dim]Run [cyan]python main.py <command> --help[/] for more info on a command.[/]")
        console.print("[dim]Example: [cyan]python main.py backend generate ./my-frontend[/][/]\n")


if __name__ == "__main__":
    app()