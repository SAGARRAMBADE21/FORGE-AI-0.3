# cli/help.py
"""
FORGE Help System - Comprehensive help and documentation.
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()


class ForgeHelp:
    """Comprehensive help system for FORGE."""

    @staticmethod
    def show_quick_start():
        """Show quick start guide."""
        content = """
# 🚀 FORGE Quick Start

## 1. Setup (First time only)
```bash
python main.py setup
```

## 2. Generate Backend
```bash
# Analyze your frontend project
python main.py backend analyze ./my-react-app

# Generate complete backend
python main.py backend generate ./my-react-app -f express -d postgresql
```

## 3. Review Existing Code
```bash
python main.py backend review ./my-backend
```

## 4. Interactive Chat
```bash
python main.py chat ./my-project
```
        """
        console.print(
            Panel(Markdown(content), title="Quick Start", border_style="cyan")
        )

    @staticmethod
    def show_commands():
        """Show all available commands."""
        console.print("\n[bold cyan]FORGE Commands[/]\n")

        table = Table(show_header=True, header_style="cyan")
        table.add_column("Command", width=35)
        table.add_column("Description", width=45)

        # Top-level commands
        table.add_row("[bold]Top-Level Commands[/]", "")
        table.add_row("setup", "Interactive configuration wizard")
        table.add_row("init <path>", "Initialize a new project")
        table.add_row("status <path>", "Show project status")
        table.add_row("chat <path>", "Interactive code chat")
        table.add_row("stats", "Show usage statistics and costs")
        table.add_row("", "")

        # Backend commands
        table.add_row("[bold]Backend Commands[/]", "")
        table.add_row("backend generate <path>", "Generate backend from frontend")
        table.add_row("backend analyze <path>", "Analyze frontend structure")
        table.add_row("backend review <path>", "Review backend code quality")
        table.add_row("backend debug <path>", "Debug backend issues")
        table.add_row("backend add-model <path> <name>", "Add a new data model")
        table.add_row("backend add-endpoint", "Add API endpoint")
        table.add_row("backend sync <path>", "Sync with frontend changes")
        table.add_row("backend rollback <path>", "Rollback last change")
        table.add_row("", "")

        # Index commands
        table.add_row("[bold]Index Commands[/]", "")
        table.add_row("index run <path>", "Index a project")
        table.add_row("index search <path> <query>", "Search code semantically")
        table.add_row("index symbols <path>", "List/search symbols")

        console.print(table)

    @staticmethod
    def show_providers():
        """Show supported LLM providers."""
        console.print("\n[bold cyan]Supported LLM Providers[/]\n")

        table = Table(show_header=True, header_style="cyan")
        table.add_column("Provider", width=15)
        table.add_column("Models", width=35)
        table.add_column("Notes", width=30)

        table.add_row(
            "openrouter",
            "llama-3.3-70b, claude-3.5, gpt-4o",
            "★ Recommended - Many models",
        )
        table.add_row(
            "gemini", "gemini-2.0-flash, gemini-1.5-pro", "Free tier available"
        )
        table.add_row("groq", "llama-3.3-70b, mixtral-8x7b", "Very fast inference")
        table.add_row("openai", "gpt-4o, gpt-4o-mini, gpt-3.5", "Original GPT models")
        table.add_row("anthropic", "claude-3.5-sonnet, claude-3-opus", "Claude models")
        table.add_row(
            "huggingface", "Qwen-2.5-Coder, various OSS", "Open source models"
        )

        console.print(table)
        console.print("\n[dim]Set provider with: --provider <name> or in .env[/]")

    @staticmethod
    def show_frameworks():
        """Show supported frameworks."""
        console.print("\n[bold cyan]Supported Backend Frameworks[/]\n")

        table = Table(show_header=True, header_style="cyan")
        table.add_column("Framework", width=15)
        table.add_column("Language", width=12)
        table.add_column("Use Case", width=35)

        table.add_row("express", "JavaScript", "Node.js REST APIs")
        table.add_row("fastapi", "Python", "High-performance Python APIs")
        table.add_row("nestjs", "TypeScript", "Enterprise TypeScript APIs")
        table.add_row("django", "Python", "Full-featured Python web")
        table.add_row("spring", "Java", "Enterprise Java applications")
        table.add_row("gin", "Go", "High-performance Go APIs")
        table.add_row("actix", "Rust", "Ultra-fast Rust APIs")

        console.print(table)

    @staticmethod
    def show_databases():
        """Show supported databases."""
        console.print("\n[bold cyan]Supported Databases[/]\n")

        table = Table(show_header=True, header_style="cyan")
        table.add_column("Database", width=15)
        table.add_column("Type", width=12)
        table.add_column("Best For", width=35)

        table.add_row("postgresql", "SQL", "★ Default - Full featured")
        table.add_row("mysql", "SQL", "Widely supported")
        table.add_row("sqlite", "SQL", "Development, small apps")
        table.add_row("mongodb", "NoSQL", "Flexible schemas")
        table.add_row("redis", "Key-Value", "Caching, sessions")

        console.print(table)

    @staticmethod
    def show_examples():
        """Show usage examples."""
        content = """
# Example Usage

## Generate Express + PostgreSQL Backend
```bash
python main.py backend generate ./my-react-app \\
  --framework express \\
  --database postgresql \\
  --output ./backend
```

## Generate FastAPI Backend with Custom Model
```bash
python main.py backend generate ./frontend \\
  --framework fastapi \\
  --database postgresql \\
  --mode multi  # Use 8 specialized agents
```

## Review Code for Security Issues
```bash
python main.py backend review ./backend --verbose
```

## Debug a Specific Error
```bash
python main.py backend debug ./backend \\
  --error "TypeError: Cannot read property 'id' of undefined" \\
  --file "src/controllers/userController.js" \\
  --line 42
```

## Add Custom Model
```bash
python main.py backend add-model ./backend Product \\
  --fields '[{"name":"title","type":"string"},{"name":"price","type":"number"}]'
```

## Search Code Semantically
```bash
python main.py index search ./project "user authentication flow"
```
        """
        console.print(Panel(Markdown(content), title="Examples", border_style="cyan"))

    @staticmethod
    def show_troubleshooting():
        """Show troubleshooting guide."""
        content = """
# 🔧 Troubleshooting

## API Key Issues
- **"API key not found"**: Run `python main.py setup` to configure
- **"Rate limit exceeded"**: Wait a few minutes or switch providers
- **"Invalid API key"**: Check key is correct in .env file

## Generation Issues
- **Slow generation**: Try `--mode single` for faster results
- **Incomplete output**: Increase `--max-tokens` setting
- **Wrong framework**: Ensure frontend is in the path root

## Memory Issues
- **Out of memory**: Enable `FORGE_LIGHTWEIGHT=true` in .env
- **Slow startup**: This is normal on first run (loading models)

## Common Fixes
```bash
# Clear cache if issues persist
python -c "from generation.cache_manager import get_cache; get_cache().clear()"

# Reset cost tracking
python -c "from generation.cost_tracker import get_tracker; get_tracker().clear_history()"
```
        """
        console.print(
            Panel(Markdown(content), title="Troubleshooting", border_style="yellow")
        )

    @staticmethod
    def show_all():
        """Show all help sections."""
        ForgeHelp.show_quick_start()
        ForgeHelp.show_commands()
        ForgeHelp.show_providers()
        ForgeHelp.show_frameworks()
        ForgeHelp.show_databases()
        ForgeHelp.show_examples()
        ForgeHelp.show_troubleshooting()


def show_help(section: str = None):
    """Show help for a specific section or all sections."""
    sections = {
        "start": ForgeHelp.show_quick_start,
        "commands": ForgeHelp.show_commands,
        "providers": ForgeHelp.show_providers,
        "frameworks": ForgeHelp.show_frameworks,
        "databases": ForgeHelp.show_databases,
        "examples": ForgeHelp.show_examples,
        "troubleshoot": ForgeHelp.show_troubleshooting,
    }

    if section and section in sections:
        sections[section]()
    else:
        if section:
            console.print(f"[yellow]Unknown section: {section}[/]")
            console.print(f"[dim]Available: {', '.join(sections.keys())}[/]\n")
        ForgeHelp.show_all()
