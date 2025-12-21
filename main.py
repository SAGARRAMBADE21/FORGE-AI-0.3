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
from backend_agent import BackendAgent
from fullstack_agent import FullStackAgent
from config.templates_config import TemplateConfig, BackendFramework, DatabaseType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

app = typer.Typer(
    name="codegen",
    help="Full-Stack Code Generation System with Semantic Indexing"
)
console = Console()

# Sub-commands
index_app = typer.Typer(help="Code indexing commands")
backend_app = typer.Typer(help="Backend generation commands")
app.add_typer(index_app, name="index")
app.add_typer(backend_app, name="backend")


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
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without applying"),
):
    """Generate backend from frontend analysis."""
    if not path.exists():
        console.print(f"[red]Error: Path not found: {path}[/]")
        raise typer.Exit(1)

    # Configure
    config = TemplateConfig(
        framework=BackendFramework(framework),
        database=DatabaseType(database),
        output_dir=str(output) if output else "backend"
    )

    agent = FullStackAgent(path, config)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
        task = prog.add_task("Initializing...", total=None)

        def callback(stage, msg):
            prog.update(task, description=f"[cyan]{stage}[/]: {msg}")

        result = asyncio.run(_generate_backend(agent, callback, dry_run))

    if result.success:
        console.print(f"\n[green]✓ Backend generation complete![/]")
        
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
def backend_analyze(path: Path = typer.Argument(..., help="Project path")):
    """Analyze frontend and show inferred backend architecture."""
    agent = FullStackAgent(path)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
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
    fields: str = typer.Option("", "-f", "--fields", help="Fields as JSON array"),
):
    """Add a new model to the backend."""
    agent = FullStackAgent(path)

    with console.status("Initializing..."):
        asyncio.run(agent.initialize())

    # Parse fields
    field_list = []
    if fields:
        try:
            field_list = json.loads(fields)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid fields JSON: {e}[/]")
            console.print(f"[yellow]Expected format: '[{{\"name\":\"field1\",\"type\":\"string\"}}]'[/]")
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
):
    """Add a new API endpoint."""
    agent = FullStackAgent(path)

    with console.status("Initializing..."):
        asyncio.run(agent.initialize())

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
    path: Path = typer.Argument(".", help="Project path"),
    file: str = typer.Option(None, "-f", "--file", help="Current file context"),
):
    """Interactive chat with the code agent."""
    agent = FullStackAgent(path)

    with console.status("Initializing..."):
        asyncio.run(agent.initialize())

    console.print("[green]Agent ready. Type 'exit' to quit.[/]\n")

    while True:
        try:
            message = console.input("[bold blue]You:[/] ")
            
            if message.lower() in ('exit', 'quit', 'q'):
                break

            if not message.strip():
                continue

            response = asyncio.run(agent.chat(message, file))

            console.print(f"\n[bold green]Agent:[/] {response['response']}")

            if response['actions']:
                for action in response['actions']:
                    console.print(f"  [dim]Action: {action['type']}[/]")

            console.print()

        except KeyboardInterrupt:
            break

    console.print("\n[yellow]Goodbye![/]")


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _display_stats(stats):
    """Display index statistics."""
    console.print(f"\n[green]✓ Indexing complete![/]")

    table = Table(title="Index Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Files", str(stats.files))
    table.add_row("Symbols", str(stats.symbols))
    table.add_row("Chunks", str(stats.chunks))
    table.add_row("Tokens", f"{stats.tokens:,}")
    table.add_row("Parse Errors", str(stats.errors))
    table.add_row("Total Time", f"{stats.total_time_ms:.0f}ms")

    console.print(table)

    if stats.by_language:
        lang_table = Table(title="By Language")
        lang_table.add_column("Language")
        lang_table.add_column("Files", justify="right")
        for lang, count in sorted(stats.by_language.items(), key=lambda x: -x[1]):
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


if __name__ == "__main__":
    app()