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
    path: Path = typer.Argument(".", help="Project path"),
    file: str = typer.Option(None, "-f", "--file", help="Current file context"),
    no_index: bool = typer.Option(False, "--no-index", help="Skip codebase indexing"),
):
    """Interactive chat with the code agent (Cursor-like interface)."""
    
    if no_index:
        console.print("[yellow]⚠ Running in no-index mode - codebase features disabled[/]")
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
                        console.print("\n[dim]Tip: Run without --no-index to enable full features[/]")
                    else:
                        console.print("[yellow]Command not available in no-index mode[/]")
                    continue
                
                console.print(f"\n[bold green]🤖 Agent >[/] No-index mode: Please run without --no-index flag to enable AI features.")
                
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
    
    agent = FullStackAgent(path)

    with console.status("Initializing..."):
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
    
    elif cmd.startswith('/search '):
        query = cmd[8:].strip()
        if query:
            with console.status("Searching..."):
                results = asyncio.run(agent.search(query, top_k=5))
            console.print(f"\n[green]Found {results.total_count} results[/]")
            for i, result in enumerate(results.results[:5], 1):
                console.print(f"\n{i}. [cyan]{result.chunk.file}[/] L{result.chunk.start_line}-{result.chunk.end_line}")
                console.print(f"   [dim]{result.chunk.content[:150]}...[/]")
        else:
            console.print("[yellow]Usage: /search <query>[/]")
    
    elif cmd.startswith('/symbols '):
        query = cmd[9:].strip()
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
    
    elif cmd.startswith('/generate '):
        description = cmd[10:].strip()
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


if __name__ == "__main__":
    app()