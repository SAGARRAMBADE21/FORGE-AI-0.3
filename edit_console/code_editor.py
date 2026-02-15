"""
Code Editor - handles JavaScript/TypeScript/Python code modifications
"""

import re
from typing import Optional
from .models import EditIntent, EditResult, ActionType, TargetType


class CodeEditor:
    """Handles code file modifications"""
    
    def apply_edit(self, intent: EditIntent, content: str, language: str = "javascript") -> EditResult:
        """
        Apply edit intent to code file
        
        Args:
            intent: Parsed edit intent
            content: Current code content
            language: Programming language (javascript, typescript, python)
            
        Returns:
            EditResult with modified content and diff
        """
        try:
            if intent.action == ActionType.RENAME:
                return self._rename_identifier(intent, content)
            elif intent.action == ActionType.MODIFY:
                return self._modify_code(intent, content)
            elif intent.action == ActionType.ADD:
                return self._add_code(intent, content, language)
            elif intent.action == ActionType.REMOVE:
                return self._remove_code(intent, content)
            else:
                return EditResult(
                    success=False,
                    original_content=content,
                    modified_content=content,
                    diff="",
                    message=f"Unsupported action: {intent.action}",
                    errors=[f"Cannot {intent.action} in code files"]
                )
        except Exception as e:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Edit failed: {str(e)}",
                errors=[str(e)]
            )
    
    def _rename_identifier(self, intent: EditIntent, content: str) -> EditResult:
        """Rename function, class, variable, etc"""
        old_name = intent.changes.old_value or intent.target_location.name
        new_name = intent.changes.new_value
        
        if not old_name or not new_name:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message="Missing old or new name",
                errors=["Both old and new names required"]
            )
        
        # Simple word boundary replacement
        # TODO: Use proper AST parsing for more accuracy
        pattern = re.compile(rf'\b{re.escape(old_name)}\b')
        modified = pattern.sub(new_name, content)
        
        count = len(pattern.findall(content))
        
        return EditResult(
            success=True,
            original_content=content,
            modified_content=modified,
            diff=self._generate_diff(content, modified),
            message=f"Renamed '{old_name}' to '{new_name}' ({count} occurrences)"
        )
    
    def _modify_code(self, intent: EditIntent, content: str) -> EditResult:
        """Modify code (change value, add error handling, etc)"""
        # This is complex and depends on what specifically to modify
        # For now, handle simple value replacements
        
        if intent.changes.old_value and intent.changes.new_value:
            modified = content.replace(
                intent.changes.old_value,
                intent.changes.new_value
            )
            
            return EditResult(
                success=True,
                original_content=content,
                modified_content=modified,
                diff=self._generate_diff(content, modified),
                message=f"Replaced '{intent.changes.old_value}' with '{intent.changes.new_value}'"
            )
        
        return EditResult(
            success=False,
            original_content=content,
            modified_content=content,
            diff="",
            message="Code modification requires more specific parameters",
            errors=["Specify what to change and to what value"]
        )
    
    def _add_code(self, intent: EditIntent, content: str, language: str) -> EditResult:
        """Add code (function, class, etc)"""
        # Adding code requires knowing where to add it
        # This is complex without proper AST parsing
        return EditResult(
            success=False,
            original_content=content,
            modified_content=content,
            diff="",
            message="Adding code not yet fully supported",
            errors=["Code addition requires AST parsing integration"]
        )
    
    def _remove_code(self, intent: EditIntent, content: str) -> EditResult:
        """Remove code (function, class, lines, etc)"""
        if intent.target_location.line_start is not None:
            # Remove specific lines
            lines = content.splitlines(keepends=True)
            start = intent.target_location.line_start - 1
            end = intent.target_location.line_end or start + 1
            
            if start < 0 or end > len(lines):
                return EditResult(
                    success=False,
                    original_content=content,
                    modified_content=content,
                    diff="",
                    message=f"Invalid line range: {start+1}-{end}",
                    errors=["Line numbers out of range"]
                )
            
            modified_lines = lines[:start] + lines[end:]
            modified = ''.join(modified_lines)
            
            return EditResult(
                success=True,
                original_content=content,
                modified_content=modified,
                diff=self._generate_diff(content, modified),
                message=f"Removed lines {start+1}-{end}"
            )
        
        return EditResult(
            success=False,
            original_content=content,
            modified_content=content,
            diff="",
            message="Code removal requires line numbers or identifier",
            errors=["Specify what to remove"]
        )
    
    def _generate_diff(self, old: str, new: str) -> str:
        """Generate unified diff"""
        import difflib
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, lineterm='')
        return ''.join(diff)
