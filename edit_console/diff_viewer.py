"""
Diff viewer for showing changes before applying
"""

import difflib
from typing import List, Tuple
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel


class DiffViewer:
    """Shows diffs with syntax highlighting"""
    
    def __init__(self):
        self.console = Console()
    
    def show_diff(self, old_content: str, new_content: str, 
                  filename: str = "", context_lines: int = 3):
        """Show a unified diff with syntax highlighting"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"original/{filename}",
            tofile=f"modified/{filename}",
            lineterm='',
            n=context_lines
        )
        
        diff_text = ''.join(diff)
        
        if not diff_text:
            self.console.print("[yellow]No changes to preview[/yellow]")
            return
        
        # Display with syntax highlighting
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
        panel = Panel(syntax, title=f"[bold]Changes Preview: {filename}[/bold]", 
                     border_style="blue")
        self.console.print(panel)
    
    def show_inline_diff(self, old_content: str, new_content: str, 
                        start_line: int = 1):
        """Show inline diff with line numbers"""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        changes = self._get_line_changes(old_lines, new_lines)
        
        for line_num, change_type, content in changes:
            if change_type == "removed":
                self.console.print(f"[red]- {line_num + start_line}: {content}[/red]")
            elif change_type == "added":
                self.console.print(f"[green]+ {line_num + start_line}: {content}[/green]")
            else:
                self.console.print(f"  {line_num + start_line}: {content}")
    
    def _get_line_changes(self, old_lines: List[str], new_lines: List[str]) -> List[Tuple[int, str, str]]:
        """Get line-by-line changes"""
        changes = []
        
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'delete':
                for i in range(i1, i2):
                    changes.append((i, "removed", old_lines[i]))
            elif tag == 'insert':
                for j in range(j1, j2):
                    changes.append((j, "added", new_lines[j]))
            elif tag == 'replace':
                for i in range(i1, i2):
                    changes.append((i, "removed", old_lines[i]))
                for j in range(j1, j2):
                    changes.append((j, "added", new_lines[j]))
            elif tag == 'equal':
                for i in range(i1, i2):
                    changes.append((i, "unchanged", old_lines[i]))
        
        return changes
    
    def get_diff_text(self, old_content: str, new_content: str) -> str:
        """Get diff as plain text"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm=''
        )
        
        return ''.join(diff)
