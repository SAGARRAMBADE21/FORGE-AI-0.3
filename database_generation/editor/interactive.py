# Interactive editor
"""
Interactive Editor - Terminal-based schema editing
"""

from typing import Optional, Callable
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

from database_generation.db_types import ForgeSchema, FieldType
from database_generation.editor.schema_editor import SchemaEditor
from database_generation.engine.schema_builder import schema_builder
from database_generation.db_types import DatabaseType, EditorType


class InteractiveEditor:
    """Interactive terminal-based schema editor"""
    
    def __init__(self, schema: ForgeSchema = None):
        self.console = Console()
        self.editor = SchemaEditor(schema)
        self.running = False
    
    def run(self):
        """Start interactive editing session"""
        self.running = True
        
        self.console.print(Panel.fit(
            "[bold cyan]FORGE Interactive Schema Editor[/bold cyan]\n"
            "Type 'help' for commands, 'exit' to quit",
            border_style="cyan"
        ))
        
        while self.running:
            try:
                command = Prompt.ask("\n[bold green]forge-edit[/bold green]")
                self._handle_command(command.strip())
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    def _handle_command(self, command: str):
        """Handle user command"""
        if not command:
            return
        
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        handlers = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "show": self._cmd_show,
            "list": self._cmd_list,
            "create": self._cmd_create,
            "add": self._cmd_add,
            "remove": self._cmd_remove,
            "delete": self._cmd_remove,
            "modify": self._cmd_modify,
            "rename": self._cmd_rename,
            "generate": self._cmd_generate,
            "export": self._cmd_export,
            "undo": self._cmd_undo,
            "redo": self._cmd_redo,
            "clear": self._cmd_clear,
        }
        
        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("Type 'help' for available commands")
    
    def _cmd_help(self, args):
        """Show help"""
        help_table = Table(title="Available Commands", box=None)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description")
        help_table.add_column("Example", style="dim")
        
        commands = [
            ("show", "Show schema or entity", "show | show users"),
            ("list", "List entities or fields", "list | list users"),
            ("create entity <name>", "Create new entity", "create entity users"),
            ("add field <entity> <name> <type>", "Add field", "add field users email string"),
            ("add index <entity> <fields>", "Add index", "add index users email"),
            ("add relationship <from> <to>", "Add relationship", "add relationship users orders"),
            ("remove entity <name>", "Remove entity", "remove entity users"),
            ("remove field <entity> <name>", "Remove field", "remove field users email"),
            ("modify field <entity> <name>", "Modify field", "modify field users email"),
            ("rename entity <old> <new>", "Rename entity", "rename entity user users"),
            ("generate <database>", "Generate SQL", "generate postgresql"),
            ("export <file>", "Export schema", "export schema.json"),
            ("undo", "Undo last change", "undo"),
            ("redo", "Redo last change", "redo"),
            ("clear", "Clear screen", "clear"),
            ("exit", "Exit editor", "exit"),
        ]
        
        for cmd, desc, example in commands:
            help_table.add_row(cmd, desc, example)
        
        self.console.print(help_table)
    
    def _cmd_exit(self, args):
        """Exit editor"""
        if self.editor.schema.entities:
            if not Confirm.ask("Schema has entities. Exit without saving?"):
                return
        self.running = False
        self.console.print("[yellow]Goodbye![/yellow]")
    
    def _cmd_show(self, args):
        """Show schema or specific entity"""
        schema = self.editor.get_schema()
        
        if not args:
            # Show full schema
            self._display_schema_summary()
        else:
            # Show specific entity
            entity_name = args[0]
            entity = next((e for e in schema.entities if e.name == entity_name), None)
            if entity:
                self._display_entity(entity)
            else:
                self.console.print(f"[red]Entity '{entity_name}' not found[/red]")
    
    def _cmd_list(self, args):
        """List entities or fields"""
        schema = self.editor.get_schema()
        
        if not args:
            # List entities
            if not schema.entities:
                self.console.print("[yellow]No entities defined[/yellow]")
                return
            
            table = Table(title="Entities")
            table.add_column("Name", style="cyan")
            table.add_column("Fields")
            table.add_column("Indexes")
            
            for entity in schema.entities:
                table.add_row(
                    entity.name,
                    str(len(entity.fields)),
                    str(len(entity.indexes))
                )
            
            self.console.print(table)
        else:
            # List fields for entity
            entity_name = args[0]
            entity = next((e for e in schema.entities if e.name == entity_name), None)
            if entity:
                self._display_entity_fields(entity)
            else:
                self.console.print(f"[red]Entity '{entity_name}' not found[/red]")
    
    def _cmd_create(self, args):
        """Create entity"""
        if len(args) < 2 or args[0] != "entity":
            self.console.print("[red]Usage: create entity <name>[/red]")
            return
        
        name = args[1].lower()
        
        try:
            self.editor.create_entity(name)
            self.console.print(f"[green]Created entity '{name}'[/green]")
            
            # Ask to add fields
            while Confirm.ask("Add a field?", default=False):
                field_name = Prompt.ask("Field name")
                field_type = Prompt.ask(
                    "Field type",
                    choices=["string", "text", "integer", "decimal", "boolean", 
                            "timestamp", "uuid", "json", "array", "enum"],
                    default="string"
                )
                required = Confirm.ask("Required?", default=False)
                unique = Confirm.ask("Unique?", default=False)
                
                self.editor.get_entity(name).add_field(
                    field_name,
                    field_type,
                    required=required,
                    unique=unique
                )
                self.console.print(f"[green]Added field '{field_name}'[/green]")
                
        except ValueError as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _cmd_add(self, args):
        """Add field, index, or relationship"""
        if not args:
            self.console.print("[red]Usage: add field|index|relationship ...[/red]")
            return
        
        sub_cmd = args[0]
        
        if sub_cmd == "field":
            self._add_field(args[1:])
        elif sub_cmd == "index":
            self._add_index(args[1:])
        elif sub_cmd == "relationship":
            self._add_relationship(args[1:])
        else:
            self.console.print(f"[red]Unknown: add {sub_cmd}[/red]")
    
    def _add_field(self, args):
        """Add field to entity"""
        if len(args) < 3:
            self.console.print("[red]Usage: add field <entity> <name> <type>[/red]")
            return
        
        entity_name, field_name, field_type = args[0], args[1], args[2]
        
        try:
            entity_builder = self.editor.get_entity(entity_name)
            if not entity_builder:
                self.console.print(f"[red]Entity '{entity_name}' not found[/red]")
                return
            
            entity_builder.add_field(field_name, field_type)
            self.console.print(f"[green]Added '{field_name}' to '{entity_name}'[/green]")
        except ValueError as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _add_index(self, args):
        """Add index to entity"""
        if len(args) < 2:
            self.console.print("[red]Usage: add index <entity> <field1> [field2...][/red]")
            return
        
        entity_name = args[0]
        fields = args[1:]
        
        try:
            entity_builder = self.editor.get_entity(entity_name)
            if not entity_builder:
                self.console.print(f"[red]Entity '{entity_name}' not found[/red]")
                return
            
            entity_builder.add_index(fields)
            self.console.print(f"[green]Added index on {fields}[/green]")
        except ValueError as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _add_relationship(self, args):
        """Add relationship"""
        if len(args) < 2:
            self.console.print("[red]Usage: add relationship <from> <to>[/red]")
            return
        
        from_entity, to_entity = args[0], args[1]
        
        try:
            self.editor.add_relationship(from_entity, to_entity)
            self.console.print(f"[green]Added relationship: {from_entity} → {to_entity}[/green]")
        except ValueError as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _cmd_remove(self, args):
        """Remove entity or field"""
        if len(args) < 2:
            self.console.print("[red]Usage: remove entity|field <name>[/red]")
            return
        
        sub_cmd = args[0]
        
        if sub_cmd == "entity":
            name = args[1]
            if Confirm.ask(f"Remove entity '{name}'?"):
                self.editor.remove_entity(name)
                self.console.print(f"[green]Removed entity '{name}'[/green]")
        
        elif sub_cmd == "field":
            if len(args) < 3:
                self.console.print("[red]Usage: remove field <entity> <field>[/red]")
                return
            
            entity_name, field_name = args[1], args[2]
            
            try:
                entity_builder = self.editor.get_entity(entity_name)
                if entity_builder:
                    entity_builder.remove_field(field_name)
                    self.console.print(f"[green]Removed '{field_name}' from '{entity_name}'[/green]")
            except ValueError as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    def _cmd_modify(self, args):
        """Modify field"""
        if len(args) < 3 or args[0] != "field":
            self.console.print("[red]Usage: modify field <entity> <field>[/red]")
            return
        
        entity_name, field_name = args[1], args[2]
        
        entity_builder = self.editor.get_entity(entity_name)
        if not entity_builder:
            self.console.print(f"[red]Entity '{entity_name}' not found[/red]")
            return
        
        # Interactive modification
        self.console.print(f"\nModifying '{entity_name}.{field_name}'")
        
        mods = {}
        if Confirm.ask("Change required?", default=False):
            mods["required"] = Confirm.ask("Required?")
        if Confirm.ask("Change unique?", default=False):
            mods["unique"] = Confirm.ask("Unique?")
        if Confirm.ask("Add comment?", default=False):
            mods["comment"] = Prompt.ask("Comment")
        
        if mods:
            try:
                entity_builder.modify_field(field_name, **mods)
                self.console.print("[green]Field modified[/green]")
            except ValueError as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    def _cmd_rename(self, args):
        """Rename entity"""
        if len(args) < 3 or args[0] != "entity":
            self.console.print("[red]Usage: rename entity <old_name> <new_name>[/red]")
            return
        
        old_name, new_name = args[1], args[2]
        
        try:
            self.editor.rename_entity(old_name, new_name)
            self.console.print(f"[green]Renamed '{old_name}' to '{new_name}'[/green]")
        except ValueError as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _cmd_generate(self, args):
        """Generate SQL"""
        database = args[0] if args else "postgresql"
        
        try:
            db_type = DatabaseType(database)
        except ValueError:
            self.console.print(f"[red]Unknown database: {database}[/red]")
            self.console.print("Options: postgresql, mysql, mongodb")
            return
        
        schema = self.editor.get_schema()
        if not schema.entities:
            self.console.print("[yellow]No entities to generate[/yellow]")
            return
        
        result = schema_builder.build(schema, db_type, EditorType.CLI)
        
        # Display SQL
        syntax = Syntax(result.ddl, "sql" if database != "mongodb" else "javascript",
                       theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title=f"{database.upper()} DDL"))
    
    def _cmd_export(self, args):
        """Export schema to file"""
        filename = args[0] if args else "schema.json"
        
        try:
            import json
            with open(filename, 'w') as f:
                f.write(self.editor.to_json())
            self.console.print(f"[green]Exported to '{filename}'[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _cmd_undo(self, args):
        """Undo last change"""
        if self.editor.undo():
            self.console.print("[green]Undid last change[/green]")
        else:
            self.console.print("[yellow]Nothing to undo[/yellow]")
    
    def _cmd_redo(self, args):
        """Redo last change"""
        if self.editor.redo():
            self.console.print("[green]Redid last change[/green]")
        else:
            self.console.print("[yellow]Nothing to redo[/yellow]")
    
    def _cmd_clear(self, args):
        """Clear screen"""
        self.console.clear()
    
    def _display_schema_summary(self):
        """Display schema summary"""
        schema = self.editor.get_schema()
        
        if not schema.entities:
            self.console.print("[yellow]Schema is empty[/yellow]")
            return
        
        self.console.print(Panel(
            f"[bold]Schema:[/bold] {schema.name}\n"
            f"[bold]App Type:[/bold] {schema.app_type.value}\n"
            f"[bold]Entities:[/bold] {len(schema.entities)}\n"
            f"[bold]Relationships:[/bold] {len(schema.relationships)}",
            title="Schema Summary"
        ))
        
        for entity in schema.entities:
            fields = [f.name for f in entity.fields]
            self.console.print(f"  • [cyan]{entity.name}[/cyan]: {', '.join(fields[:5])}"
                             + (f" (+{len(fields)-5} more)" if len(fields) > 5 else ""))
    
    def _display_entity(self, entity):
        """Display entity details"""
        self.console.print(Panel(
            f"[bold]Entity:[/bold] {entity.name}\n"
            f"[bold]Timestamps:[/bold] {entity.timestamps}\n"
            f"[bold]Soft Delete:[/bold] {entity.soft_delete}",
            title=f"Entity: {entity.name}"
        ))
        
        self._display_entity_fields(entity)
    
    def _display_entity_fields(self, entity):
        """Display entity fields"""
        table = Table(title=f"Fields: {entity.name}")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Required")
        table.add_column("Unique")
        table.add_column("Reference")
        
        for field in entity.fields:
            ref = f"→ {field.reference.entity}" if field.reference else ""
            table.add_row(
                field.name,
                field.type.value,
                "✓" if field.required else "",
                "✓" if field.unique else "",
                ref
            )
        
        self.console.print(table)
        
        if entity.indexes:
            idx_table = Table(title="Indexes")
            idx_table.add_column("Name")
            idx_table.add_column("Fields")
            idx_table.add_column("Unique")
            
            for idx in entity.indexes:
                idx_table.add_row(
                    idx.name or "auto",
                    ", ".join(idx.fields),
                    "✓" if idx.unique else ""
                )
            
            self.console.print(idx_table)