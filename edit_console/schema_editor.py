"""
SQL Schema Editor - handles SQL schema modifications
"""

import re
from typing import List, Optional, Tuple
from .models import EditIntent, EditResult, ActionType, TargetType


class SchemaEditor:
    """Handles SQL schema file modifications"""
    
    def apply_edit(self, intent: EditIntent, content: str) -> EditResult:
        """
        Apply edit intent to SQL schema
        
        Args:
            intent: Parsed edit intent
            content: Current SQL content
            
        Returns:
            EditResult with modified content and diff
        """
        try:
            if intent.target_type == TargetType.TABLE:
                return self._edit_table(intent, content)
            elif intent.target_type in [TargetType.FIELD, TargetType.COLUMN]:
                return self._edit_field(intent, content)
            else:
                return EditResult(
                    success=False,
                    original_content=content,
                    modified_content=content,
                    diff="",
                    message=f"Unsupported target type for SQL: {intent.target_type}",
                    errors=[f"Cannot edit {intent.target_type} in SQL schema"]
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
    
    def _edit_table(self, intent: EditIntent, content: str) -> EditResult:
        """Edit table (rename, add, remove)"""
        if intent.action == ActionType.RENAME:
            return self._rename_table(intent, content)
        elif intent.action == ActionType.ADD:
            return self._add_table(intent, content)
        elif intent.action == ActionType.REMOVE:
            return self._remove_table(intent, content)
        else:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Unsupported action for table: {intent.action}",
                errors=[f"Cannot {intent.action} table"]
            )
    
    def _edit_field(self, intent: EditIntent, content: str) -> EditResult:
        """Edit field (add, remove, modify type, modify constraint)"""
        if intent.action == ActionType.MODIFY:
            # Check what property to modify
            if intent.changes.additional_params.get('property') == 'type':
                return self._change_field_type(intent, content)
            elif intent.changes.additional_params.get('property') == 'constraint':
                return self._change_field_constraint(intent, content)
            else:
                return self._modify_field_generic(intent, content)
        elif intent.action == ActionType.ADD:
            return self._add_field(intent, content)
        elif intent.action == ActionType.REMOVE:
            return self._remove_field(intent, content)
        else:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Unsupported action for field: {intent.action}",
                errors=[f"Cannot {intent.action} field"]
            )
    
    def _rename_table(self, intent: EditIntent, content: str) -> EditResult:
        """Rename a table"""
        old_name = intent.changes.old_value or intent.target_location.name
        new_name = intent.changes.new_value
        
        if not old_name or not new_name:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message="Missing table names for rename",
                errors=["Old or new table name not specified"]
            )
        
        # Find CREATE TABLE statement
        pattern = re.compile(
            rf'CREATE\s+TABLE\s+{re.escape(old_name)}\s*\(',
            re.IGNORECASE
        )
        
        if not pattern.search(content):
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Table '{old_name}' not found in schema",
                errors=[f"No CREATE TABLE statement found for '{old_name}'"]
            )
        
        # Replace table name
        modified = pattern.sub(f'CREATE TABLE {new_name} (', content)
        
        return EditResult(
            success=True,
            original_content=content,
            modified_content=modified,
            diff=self._generate_diff(content, modified),
            message=f"Renamed table '{old_name}' to '{new_name}'"
        )
    
    def _change_field_type(self, intent: EditIntent, content: str) -> EditResult:
        """Change field data type"""
        field_name = intent.target_location.name
        new_type = intent.changes.new_value
        
        if not field_name or not new_type:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message="Missing field name or new type",
                errors=["Field name or new type not specified"]
            )
        
        # Find field definitions and replace type
        # Pattern: field_name OLD_TYPE
        pattern = re.compile(
            rf'(\s+{re.escape(field_name)}\s+)(\w+(?:\([^)]+\))?)',
            re.IGNORECASE
        )
        
        matches = list(pattern.finditer(content))
        if not matches:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Field '{field_name}' not found",
                errors=[f"No field '{field_name}' found in schema"]
            )
        
        # Replace all occurrences
        modified = content
        for match in reversed(matches):  # Reverse to maintain positions
            old_type = match.group(2)
            modified = (
                modified[:match.start(2)] +
                new_type.upper() +
                modified[match.end(2):]
            )
        
        return EditResult(
            success=True,
            original_content=content,
            modified_content=modified,
            diff=self._generate_diff(content, modified),
            message=f"Changed {len(matches)} '{field_name}' field(s) to type {new_type}"
        )
    
    def _change_field_constraint(self, intent: EditIntent, content: str) -> EditResult:
        """Add or modify field constraint (NOT NULL, UNIQUE, etc)"""
        field_name = intent.target_location.name
        constraint = intent.changes.new_value
        
        # Find field definition line
        pattern = re.compile(
            rf'(\s+{re.escape(field_name)}\s+\w+(?:\([^)]+\))?)(.*?)(,|\n)',
            re.IGNORECASE | re.MULTILINE
        )
        
        matches = list(pattern.finditer(content))
        if not matches:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Field '{field_name}' not found",
                errors=[f"No field '{field_name}' found in schema"]
            )
        
        modified = content
        for match in reversed(matches):
            field_def = match.group(1)
            current_constraints = match.group(2).strip()
            terminator = match.group(3)
            
            # Add or replace constraint
            if constraint.upper() in current_constraints.upper():
                # Already has constraint
                continue
            
            # Remove conflicting constraints
            if 'NOT NULL' in constraint.upper():
                current_constraints = re.sub(r'\bNULL\b', '', current_constraints, flags=re.IGNORECASE)
            elif constraint.upper() == 'NULL':
                current_constraints = re.sub(r'\bNOT\s+NULL\b', '', current_constraints, flags=re.IGNORECASE)
            
            # Add new constraint
            new_line = f"{field_def} {current_constraints} {constraint}".strip()
            modified = (
                modified[:match.start()] +
                f"  {new_line}{terminator}" +
                modified[match.end():]
            )
        
        return EditResult(
            success=True,
            original_content=content,
            modified_content=modified,
            diff=self._generate_diff(content, modified),
            message=f"Added {constraint} to '{field_name}' field(s)"
        )
    
    def _add_field(self, intent: EditIntent, content: str) -> EditResult:
        """Add new field to table(s)"""
        # This is complex - need to know which table
        # For now, return not implemented
        return EditResult(
            success=False,
            original_content=content,
            modified_content=content,
            diff="",
            message="Adding fields requires table specification",
            errors=["Specify which table to add the field to"]
        )
    
    def _remove_field(self, intent: EditIntent, content: str) -> EditResult:
        """Remove field from schema"""
        field_name = intent.target_location.name
        
        # Pattern to match field line including comma
        pattern = re.compile(
            rf'\s+{re.escape(field_name)}\s+[^,\n]+,?\n',
            re.IGNORECASE
        )
        
        matches = list(pattern.finditer(content))
        if not matches:
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Field '{field_name}' not found",
                errors=[f"No field '{field_name}' found in schema"]
            )
        
        modified = pattern.sub('', content)
        
        return EditResult(
            success=True,
            original_content=content,
            modified_content=modified,
            diff=self._generate_diff(content, modified),
            message=f"Removed {len(matches)} '{field_name}' field(s)"
        )
    
    def _modify_field_generic(self, intent: EditIntent, content: str) -> EditResult:
        """Generic field modification"""
        return EditResult(
            success=False,
            original_content=content,
            modified_content=content,
            diff="",
            message="Generic field modification not yet supported",
            errors=["Please specify what to modify (type, constraint, etc)"]
        )
    
    def _add_table(self, intent: EditIntent, content: str) -> EditResult:
        """Add new table"""
        return EditResult(
            success=False,
            original_content=content,
            modified_content=content,
            diff="",
            message="Adding tables not yet supported",
            errors=["Table creation requires full specification"]
        )
    
    def _remove_table(self, intent: EditIntent, content: str) -> EditResult:
        """Remove table from schema"""
        table_name = intent.target_location.name
        
        # Find and remove entire CREATE TABLE block
        pattern = re.compile(
            rf'CREATE\s+TABLE\s+{re.escape(table_name)}\s*\([^;]+;',
            re.IGNORECASE | re.DOTALL
        )
        
        if not pattern.search(content):
            return EditResult(
                success=False,
                original_content=content,
                modified_content=content,
                diff="",
                message=f"Table '{table_name}' not found",
                errors=[f"No CREATE TABLE statement found for '{table_name}'"]
            )
        
        modified = pattern.sub('', content)
        
        return EditResult(
            success=True,
            original_content=content,
            modified_content=modified,
            diff=self._generate_diff(content, modified),
            message=f"Removed table '{table_name}'"
        )
    
    def _generate_diff(self, old: str, new: str) -> str:
        """Generate unified diff"""
        import difflib
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, lineterm='')
        return ''.join(diff)
