"""
Main Edit Console - Interactive NLP-powered editing interface
"""

from typing import Optional, Dict
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from .models import FileContext, FileType, EditIntent, EditResult
from .file_manager import FileManager
from .nlp_interpreter import NLPInterpreter
from .schema_editor import SchemaEditor
from .code_editor import CodeEditor
from .diff_viewer import DiffViewer


class EditConsole:
    """Interactive edit console with NLP command support"""
    
    def __init__(self, workspace_path: str = ".", llm_client=None):
        """
        Initialize edit console
        
        Args:
            workspace_path: Path to workspace directory
            llm_client: Optional LLM client for NLP parsing
        """
        self.workspace_path = workspace_path
        self.console = Console()
        self.file_mgr = FileManager(workspace_path)
        self.nlp = NLPInterpreter(llm_client)
        self.schema_editor = SchemaEditor()
        self.code_editor = CodeEditor()
        self.diff_viewer = DiffViewer()
        
        self.current_file: Optional[FileContext] = None
        self.pending_changes: Dict[str, str] = {}  # filepath -> modified content
        self.history = []
    
    def run(self):
        """Main interactive loop"""
        self._show_welcome()
        
        while True:
            try:
                command = Prompt.ask("\n[bold cyan]>[/bold cyan]").strip()
                
                if not command:
                    continue
                
                # Check for built-in commands
                if command.lower() in ['exit', 'quit', 'q']:
                    if self._confirm_exit():
                        break
                elif command.lower() == 'help':
                    self._show_help()
                elif command.lower().startswith('load '):
                    self._handle_load(command[5:].strip())
                elif command.lower() == 'save':
                    self._handle_save()
                elif command.lower().startswith('save as '):
                    self._handle_save_as(command[8:].strip())
                elif command.lower() == 'reload':
                    self._handle_reload()
                elif command.lower() == 'diff':
                    self._handle_show_diff()
                elif command.lower() == 'show':
                    self._handle_show_content()
                elif command.lower() == 'undo':
                    self._handle_undo()
                elif command.lower() == 'reset':
                    self._handle_reset()
                elif command.lower() == 'list':
                    self._handle_list_files()
                else:
                    # NLP command - process edit
                    self._process_edit_command(command)
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    def _show_welcome(self):
        """Show welcome message"""
        welcome = Panel.fit(
            "[bold]FORGE Universal Edit Console[/bold]\n\n"
            "Edit any FORGE-generated file using natural language!\n"
            "Type [cyan]'help'[/cyan] for commands or start editing with [cyan]'load <file>'[/cyan]",
            border_style="green"
        )
        self.console.print(welcome)
    
    def _show_help(self):
        """Show help information"""
        help_table = Table(title="Available Commands", show_header=True)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description")
        
        commands = [
            ("load <file>", "Load a file for editing"),
            ("save", "Save current file"),
            ("save as <file>", "Save to new file"),
            ("reload", "Reload file from disk"),
            ("diff", "Show pending changes"),
            ("show", "Show current file content"),
            ("list", "List loaded files"),
            ("undo", "Undo last change"),
            ("reset", "Discard all pending changes"),
            ("help", "Show this help"),
            ("exit/quit", "Exit console"),
        ]
        
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
        
        self.console.print(help_table)
        
        # NLP examples
        self.console.print("\n[bold]Natural Language Edit Examples:[/bold]")
        examples = [
            "rename table users to accounts",
            "change email field type to VARCHAR(255)",
            "make password field required",
            "remove the old_field column",
        ]
        for ex in examples:
            self.console.print(f"  [dim]>[/dim] {ex}")
    
    def _handle_load(self, filepath: str):
        """Load a file for editing"""
        try:
            context = self.file_mgr.load_file(filepath)
            self.current_file = context
            
            self.console.print(
                f"[green]✓[/green] Loaded: [bold]{context.filename}[/bold] "
                f"({context.summary})"
            )
        except FileNotFoundError as e:
            self.console.print(f"[red]✗[/red] {e}")
        except Exception as e:
            self.console.print(f"[red]✗[/red] Failed to load file: {e}")
    
    def _handle_save(self):
        """Save current file"""
        if not self.current_file:
            self.console.print("[yellow]No file loaded[/yellow]")
            return
        
        if self.current_file.filename not in self.pending_changes:
            self.console.print("[yellow]No pending changes to save[/yellow]")
            return
        
        try:
            modified_content = self.pending_changes[self.current_file.filename]
            self.file_mgr.save_file(self.current_file.filename, modified_content)
            
            # Update current context
            self.current_file.content = modified_content
            del self.pending_changes[self.current_file.filename]
            
            self.console.print(f"[green]✓[/green] Saved: {self.current_file.filename}")
        except Exception as e:
            self.console.print(f"[red]✗[/red] Save failed: {e}")
    
    def _handle_save_as(self, new_filepath: str):
        """Save to new file"""
        if not self.current_file:
            self.console.print("[yellow]No file loaded[/yellow]")
            return
        
        try:
            content = self.pending_changes.get(
                self.current_file.filename,
                self.current_file.content
            )
            self.file_mgr.save_file(new_filepath, content, create_backup=False)
            self.console.print(f"[green]✓[/green] Saved as: {new_filepath}")
        except Exception as e:
            self.console.print(f"[red]✗[/red] Save failed: {e}")
    
    def _handle_reload(self):
        """Reload current file from disk"""
        if not self.current_file:
            self.console.print("[yellow]No file loaded[/yellow]")
            return
        
        if self.current_file.filename in self.pending_changes:
            if not Confirm.ask("Discard pending changes?"):
                return
            del self.pending_changes[self.current_file.filename]
        
        try:
            context = self.file_mgr.reload_file(self.current_file.filename)
            self.current_file = context
            self.console.print(f"[green]✓[/green] Reloaded: {context.filename}")
        except Exception as e:
            self.console.print(f"[red]✗[/red] Reload failed: {e}")
    
    def _handle_show_diff(self):
        """Show pending changes"""
        if not self.current_file:
            self.console.print("[yellow]No file loaded[/yellow]")
            return
        
        if self.current_file.filename not in self.pending_changes:
            self.console.print("[yellow]No pending changes[/yellow]")
            return
        
        self.diff_viewer.show_diff(
            self.current_file.content,
            self.pending_changes[self.current_file.filename],
            self.current_file.filename
        )
    
    def _handle_show_content(self):
        """Show current file content"""
        if not self.current_file:
            self.console.print("[yellow]No file loaded[/yellow]")
            return
        
        content = self.pending_changes.get(
            self.current_file.filename,
            self.current_file.content
        )
        
        from rich.syntax import Syntax
        
        # Map file types to syntax highlighting
        syntax_map = {
            FileType.SQL: "sql",
            FileType.JAVASCRIPT: "javascript",
            FileType.TYPESCRIPT: "typescript",
            FileType.PYTHON: "python",
            FileType.JSON: "json",
            FileType.YAML: "yaml",
        }
        
        lexer = syntax_map.get(self.current_file.file_type, "text")
        syntax = Syntax(content, lexer, theme="monokai", line_numbers=True)
        
        self.console.print(Panel(syntax, title=self.current_file.filename))
    
    def _handle_undo(self):
        """Undo last change"""
        if not self.history:
            self.console.print("[yellow]Nothing to undo[/yellow]")
            return
        
        last_state = self.history.pop()
        if self.current_file and self.current_file.filename in self.pending_changes:
            self.pending_changes[self.current_file.filename] = last_state
            self.console.print("[green]✓[/green] Undone")
        else:
            self.console.print("[yellow]Cannot undo - no pending changes[/yellow]")
    
    def _handle_reset(self):
        """Reset all pending changes"""
        if not self.current_file:
            self.console.print("[yellow]No file loaded[/yellow]")
            return
        
        if self.current_file.filename not in self.pending_changes:
            self.console.print("[yellow]No pending changes[/yellow]")
            return
        
        if Confirm.ask("Discard all pending changes?"):
            del self.pending_changes[self.current_file.filename]
            self.history.clear()
            self.console.print("[green]✓[/green] Reset to original")
    
    def _handle_list_files(self):
        """List all loaded files"""
        if not self.file_mgr.loaded_files:
            self.console.print("[yellow]No files loaded[/yellow]")
            return
        
        table = Table(title="Loaded Files")
        table.add_column("File", style="cyan")
        table.add_column("Type")
        table.add_column("Summary")
        table.add_column("Modified", style="yellow")
        
        for filepath, context in self.file_mgr.loaded_files.items():
            is_modified = "Yes" if filepath in self.pending_changes else "No"
            table.add_row(
                filepath,
                context.file_type.value,
                context.summary,
                is_modified
            )
        
        self.console.print(table)
    
    def _process_edit_command(self, command: str):
        """Process NLP edit command"""
        if not self.current_file:
            self.console.print("[yellow]Load a file first with 'load <file>'[/yellow]")
            return
        
        # Parse command
        self.console.print(f"[dim]Parsing command...[/dim]")
        intent = self.nlp.parse_command(command, self.current_file)
        
        # Show parsed intent
        self.console.print(
            f"[dim]Understood:[/dim] {intent.action.value} {intent.target_type.value}"
        )
        
        # Apply edit
        current_content = self.pending_changes.get(
            self.current_file.filename,
            self.current_file.content
        )
        
        result = self._apply_edit(intent, current_content)
        
        if result.success:
            # Show diff
            self.diff_viewer.show_diff(
                current_content,
                result.modified_content,
                self.current_file.filename
            )
            
            # Ask to apply
            if Confirm.ask("\nApply this change?", default=True):
                # Save to history
                self.history.append(current_content)
                
                # Update pending changes
                self.pending_changes[self.current_file.filename] = result.modified_content
                
                self.console.print(f"[green]✓[/green] {result.message}")
            else:
                self.console.print("[yellow]Change discarded[/yellow]")
        else:
            self.console.print(f"[red]✗[/red] {result.message}")
            if result.errors:
                for error in result.errors:
                    self.console.print(f"  [red]-[/red] {error}")
    
    def _apply_edit(self, intent: EditIntent, content: str) -> EditResult:
        """Apply edit based on file type"""
        if self.current_file.file_type == FileType.SQL:
            return self.schema_editor.apply_edit(intent, content)
        elif self.current_file.file_type in [FileType.JAVASCRIPT, FileType.TYPESCRIPT]:
            return self.code_editor.apply_edit(intent, content, "javascript")
        elif self.current_file.file_type == FileType.PYTHON:
            return self.code_editor.apply_edit(intent, content, "python")
        else:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Editing {self.current_file.file_type.value} files not yet supported",
                errors=[f"No editor for {self.current_file.file_type.value}"]
            )
    
    def _confirm_exit(self) -> bool:
        """Confirm exit if there are unsaved changes"""
        if self.pending_changes:
            self.console.print("[yellow]You have unsaved changes![/yellow]")
            for filepath in self.pending_changes.keys():
                self.console.print(f"  - {filepath}")
            return Confirm.ask("\nExit anyway?", default=False)
        return True
