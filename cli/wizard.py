# cli/wizard.py
"""
Configuration Wizard - Interactive setup for FORGE.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class ConfigWizard:
    """
    Interactive configuration wizard for FORGE setup.

    Guides users through:
    - API key configuration
    - Provider selection
    - Default settings
    - Feature toggles
    """

    PROVIDERS = {
        "openrouter": {
            "name": "OpenRouter",
            "key_env": "OPENROUTER_API_KEY",
            "url": "https://openrouter.ai/keys",
            "description": "Access to many models via single API",
            "recommended": True,
        },
        "gemini": {
            "name": "Google Gemini",
            "key_env": "GEMINI_API_KEY",
            "url": "https://aistudio.google.com/apikey",
            "description": "Free tier available, great for testing",
        },
        "groq": {
            "name": "Groq",
            "key_env": "GROQ_API_KEY",
            "url": "https://console.groq.com/keys",
            "description": "Very fast inference, free tier",
        },
        "openai": {
            "name": "OpenAI",
            "key_env": "OPENAI_API_KEY",
            "url": "https://platform.openai.com/api-keys",
            "description": "GPT-4, GPT-3.5-turbo",
        },
        "anthropic": {
            "name": "Anthropic",
            "key_env": "ANTHROPIC_API_KEY",
            "url": "https://console.anthropic.com/",
            "description": "Claude models",
        },
        "huggingface": {
            "name": "HuggingFace",
            "key_env": "HUGGINGFACE_API_KEY",
            "url": "https://huggingface.co/settings/tokens",
            "description": "Open source models",
        },
    }

    def __init__(self, project_path: Path = None):
        self.project_path = project_path or Path.cwd()
        self.env_path = self.project_path / ".env"
        self.config = {}

    def run(self):
        """Run the interactive configuration wizard."""
        self._show_welcome()

        # Step 1: Check existing configuration
        existing = self._load_existing_config()
        if existing:
            if not Confirm.ask(
                "Existing configuration found. Overwrite?", default=False
            ):
                console.print("[yellow]Keeping existing configuration.[/]")
                return

        # Step 2: Provider selection
        self._configure_provider()

        # Step 3: API key configuration
        self._configure_api_keys()

        # Step 4: Optimization settings
        self._configure_optimizations()

        # Step 5: Test connection
        if Confirm.ask("Test API connection?", default=True):
            self._test_connection()

        # Step 6: Save configuration
        self._save_config()

        self._show_completion()

    def _show_welcome(self):
        """Show welcome message."""
        console.print()
        console.print(
            Panel.fit(
                "[bold cyan]🔧 FORGE Configuration Wizard[/]\n\n"
                "This wizard will help you set up FORGE for code generation.\n"
                "You'll configure:\n"
                "  • LLM provider and API keys\n"
                "  • Default generation settings\n"
                "  • Performance optimizations",
                border_style="cyan",
            )
        )
        console.print()

    def _load_existing_config(self) -> Dict[str, str]:
        """Load existing .env configuration."""
        if not self.env_path.exists():
            return {}

        config = {}
        for line in self.env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip("\"'")
        return config

    def _configure_provider(self):
        """Select default LLM provider."""
        console.print("\n[bold]Step 1: Select your primary LLM provider[/]\n")

        table = Table(show_header=True, header_style="cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("Provider", width=15)
        table.add_column("Description", width=40)
        table.add_column("", width=12)

        providers = list(self.PROVIDERS.items())
        for i, (key, info) in enumerate(providers, 1):
            recommended = "[green]★ Recommended[/]" if info.get("recommended") else ""
            table.add_row(str(i), info["name"], info["description"], recommended)

        console.print(table)

        choice = Prompt.ask(
            "\nSelect provider",
            choices=[str(i) for i in range(1, len(providers) + 1)],
            default="1",
        )

        provider_key = providers[int(choice) - 1][0]
        self.config["provider"] = provider_key
        console.print(f"\n[green]✓ Selected: {self.PROVIDERS[provider_key]['name']}[/]")

    def _configure_api_keys(self):
        """Configure API keys."""
        console.print("\n[bold]Step 2: Configure API Keys[/]\n")

        provider = self.config.get("provider", "openrouter")
        provider_info = self.PROVIDERS[provider]

        console.print(f"Get your {provider_info['name']} API key at:")
        console.print(f"  [cyan]{provider_info['url']}[/]\n")

        api_key = Prompt.ask(
            f"Enter your {provider_info['name']} API key", password=True
        )

        self.config["api_keys"] = {provider_info["key_env"]: api_key}

        # Ask about additional providers
        if Confirm.ask("\nConfigure additional providers?", default=False):
            for key, info in self.PROVIDERS.items():
                if key != provider:
                    if Confirm.ask(f"  Configure {info['name']}?", default=False):
                        console.print(f"    Get key at: [cyan]{info['url']}[/]")
                        key_value = Prompt.ask(f"    Enter API key", password=True)
                        if key_value:
                            self.config["api_keys"][info["key_env"]] = key_value

        console.print("\n[green]✓ API keys configured[/]")

    def _configure_optimizations(self):
        """Configure optimization settings."""
        console.print("\n[bold]Step 3: Configure Optimizations[/]\n")

        self.config["optimizations"] = {}

        # Caching
        enable_cache = Confirm.ask(
            "Enable response caching? (Reduces API costs)", default=True
        )
        self.config["optimizations"]["FORGE_ENABLE_CACHE"] = str(enable_cache).lower()

        # Cost tracking
        enable_cost = Confirm.ask(
            "Enable cost tracking? (Monitor API spending)", default=True
        )
        self.config["optimizations"]["FORGE_ENABLE_COST_TRACKING"] = str(
            enable_cost
        ).lower()

        if enable_cost:
            limit = Prompt.ask("  Session spending limit in USD", default="10.0")
            self.config["optimizations"]["FORGE_SESSION_LIMIT_USD"] = limit

        # Lightweight mode
        lightweight = Confirm.ask(
            "Enable lightweight mode? (Skip heavy ML models, use API embeddings)",
            default=False,
        )
        self.config["optimizations"]["FORGE_LIGHTWEIGHT"] = str(lightweight).lower()

        console.print("\n[green]✓ Optimizations configured[/]")

    def _test_connection(self):
        """Test API connection."""
        console.print("\n[bold]Testing API connection...[/]")

        try:
            provider = self.config.get("provider", "openrouter")
            api_key_env = self.PROVIDERS[provider]["key_env"]
            api_key = self.config.get("api_keys", {}).get(api_key_env, "")

            if not api_key:
                console.print("[yellow]⚠ No API key found, skipping test[/]")
                return

            # Set env temporarily for test
            os.environ[api_key_env] = api_key

            # Try to create generator and make simple call
            from generation.llm_generator import LLMGenerator

            llm = LLMGenerator(provider=provider)
            console.print("[dim]Making test request...[/]")

            import asyncio

            response = asyncio.run(
                llm.generate(
                    system_prompt="You are a helpful assistant.",
                    user_prompt="Say 'FORGE is ready!' in exactly those words.",
                    skip_cache=True,
                )
            )

            if "FORGE" in response or "ready" in response.lower():
                console.print("[green]✓ Connection successful![/]")
            else:
                console.print(f"[green]✓ Got response: {response[:50]}...[/]")

        except Exception as e:
            console.print(f"[red]✗ Connection failed: {e}[/]")
            console.print(
                "[yellow]You can still save the configuration and test later.[/]"
            )

    def _save_config(self):
        """Save configuration to .env file."""
        console.print("\n[bold]Saving configuration...[/]")

        lines = []

        # Header
        lines.append("# FORGE Configuration")
        lines.append("# Generated by FORGE Configuration Wizard")
        lines.append("")

        # API Keys
        lines.append("# API Keys")
        for key, value in self.config.get("api_keys", {}).items():
            lines.append(f"{key}={value}")
        lines.append("")

        # Optimizations
        lines.append("# Optimization Settings")
        for key, value in self.config.get("optimizations", {}).items():
            lines.append(f"{key}={value}")

        # Write to file
        self.env_path.write_text("\n".join(lines))
        console.print(f"[green]✓ Configuration saved to {self.env_path}[/]")

    def _show_completion(self):
        """Show completion message."""
        console.print()
        console.print(
            Panel.fit(
                "[bold green]✓ FORGE is configured![/]\n\n"
                "You can now use FORGE commands:\n"
                "  [cyan]python main.py backend generate <path>[/]  - Generate backend\n"
                "  [cyan]python main.py backend review <path>[/]    - Review code\n"
                "  [cyan]python main.py chat <path>[/]              - Chat about code\n\n"
                "Run [cyan]python main.py --help[/] for all commands.",
                border_style="green",
            )
        )
        console.print()


def run_wizard(project_path: Path = None):
    """Run the configuration wizard."""
    wizard = ConfigWizard(project_path)
    wizard.run()
