"""
File manager for edit console
Handles loading, saving, and tracking files
"""

import os
from pathlib import Path
from typing import Optional, Dict
from .models import FileContext, FileType


class FileManager:
    """Manages files in the edit console"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path)
        self.loaded_files: Dict[str, FileContext] = {}
        self.backup_dir = self.workspace_path / ".forge_backup"
        self.backup_dir.mkdir(exist_ok=True)
    
    def detect_file_type(self, filename: str) -> FileType:
        """Detect file type from extension"""
        ext = Path(filename).suffix.lower()
        
        type_map = {
            ".sql": FileType.SQL,
            ".js": FileType.JAVASCRIPT,
            ".ts": FileType.TYPESCRIPT,
            ".py": FileType.PYTHON,
            ".json": FileType.JSON,
            ".yaml": FileType.YAML,
            ".yml": FileType.YAML,
        }
        
        return type_map.get(ext, FileType.UNKNOWN)
    
    def load_file(self, filepath: str) -> FileContext:
        """Load a file for editing"""
        full_path = self.workspace_path / filepath
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_type = self.detect_file_type(filepath)
        summary = self._generate_summary(content, file_type)
        
        context = FileContext(
            filename=filepath,
            file_type=file_type,
            content=content,
            summary=summary,
            line_count=len(content.splitlines())
        )
        
        self.loaded_files[filepath] = context
        return context
    
    def save_file(self, filepath: str, content: str, create_backup: bool = True):
        """Save file with optional backup"""
        full_path = self.workspace_path / filepath
        
        # Create backup if file exists
        if create_backup and full_path.exists():
            self._create_backup(filepath)
        
        # Save file
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_backup(self, filepath: str):
        """Create backup of file"""
        full_path = self.workspace_path / filepath
        backup_path = self.backup_dir / filepath
        
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
    
    def _generate_summary(self, content: str, file_type: FileType) -> str:
        """Generate a brief summary of file content"""
        lines = content.splitlines()
        line_count = len(lines)
        
        if file_type == FileType.SQL:
            # Count tables
            table_count = content.upper().count("CREATE TABLE")
            return f"{table_count} tables, {line_count} lines"
        
        elif file_type in [FileType.JAVASCRIPT, FileType.TYPESCRIPT]:
            # Count functions
            func_count = content.count("function ") + content.count("const ") + content.count("let ")
            return f"~{func_count} definitions, {line_count} lines"
        
        elif file_type == FileType.PYTHON:
            # Count functions and classes
            func_count = content.count("def ")
            class_count = content.count("class ")
            return f"{class_count} classes, {func_count} functions, {line_count} lines"
        
        else:
            return f"{line_count} lines"
    
    def get_loaded_file(self, filepath: str) -> Optional[FileContext]:
        """Get a loaded file context"""
        return self.loaded_files.get(filepath)
    
    def reload_file(self, filepath: str) -> FileContext:
        """Reload a file from disk"""
        if filepath in self.loaded_files:
            del self.loaded_files[filepath]
        return self.load_file(filepath)
