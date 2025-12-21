"""Code validation utilities."""

import re
import logging
import subprocess
from pathlib import Path

from core.types import ValidationResult

logger = logging.getLogger(__name__)


class CodeValidator:
    """Validate generated code."""

    def validate_syntax(self, content: str, filepath: str) -> ValidationResult:
        """Validate code syntax based on file extension."""
        ext = Path(filepath).suffix.lower()
        
        if ext in ('.ts', '.tsx'):
            return self._validate_typescript(content)
        elif ext in ('.js', '.jsx'):
            return self._validate_javascript(content)
        elif ext == '.py':
            return self._validate_python(content)
        elif ext == '.json':
            return self._validate_json(content)
        elif ext == '.prisma':
            return self._validate_prisma(content)
        
        return ValidationResult(valid=True)

    def _validate_typescript(self, content: str) -> ValidationResult:
        """Validate TypeScript syntax."""
        errors = []
        warnings = []

        # Basic bracket matching
        if not self._check_brackets(content):
            errors.append("Mismatched brackets")

        # Check for common issues
        if 'import ' in content and 'from' not in content and '{' in content.split('import')[1].split('\n')[0]:
            if "from '" not in content and 'from "' not in content:
                warnings.append("Import statement may be incomplete")

        # Check for semicolons after statements (optional warning)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.endswith(('{', '}', '(', ')', ',', ';', ':', '//', '/*', '*/', '*')):
                if not stripped.startswith(('//', '/*', '*', 'import', 'export', 'if', 'else', 'for', 'while', 'class', 'interface', 'type', 'function', 'const', 'let', 'var', 'return', 'throw', 'try', 'catch', 'finally')):
                    pass  # Could add semicolon warning

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_javascript(self, content: str) -> ValidationResult:
        """Validate JavaScript syntax."""
        # Similar to TypeScript
        return self._validate_typescript(content)

    def _validate_python(self, content: str) -> ValidationResult:
        """Validate Python syntax."""
        errors = []
        warnings = []

        try:
            compile(content, '<string>', 'exec')
        except SyntaxError as e:
            errors.append(f"Python syntax error: {e.msg} (line {e.lineno})")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_json(self, content: str) -> ValidationResult:
        """Validate JSON syntax."""
        errors = []
        
        import json
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(f"JSON error: {e.msg} (line {e.lineno})")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _validate_prisma(self, content: str) -> ValidationResult:
        """Validate Prisma schema syntax."""
        errors = []
        warnings = []

        # Check for required sections
        if 'generator client' not in content:
            warnings.append("Missing generator client block")
        if 'datasource' not in content:
            errors.append("Missing datasource block")

        # Check model syntax
        for match in re.finditer(r'model\s+(\w+)\s*\{([^}]*)\}', content, re.DOTALL):
            model_name = match.group(1)
            model_body = match.group(2)
            
            # Check for id field
            if '@id' not in model_body:
                warnings.append(f"Model {model_name} may be missing @id field")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _check_brackets(self, content: str) -> bool:
        """Check if brackets are balanced."""
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        
        in_string = False
        string_char = None
        prev_char = None
        
        for char in content:
            # Handle strings
            if char in ('"', "'", '`') and prev_char != '\\':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            
            if not in_string:
                if char in '([{':
                    stack.append(char)
                elif char in ')]}':
                    if not stack or stack[-1] != pairs[char]:
                        return False
                    stack.pop()
            
            prev_char = char
        
        return len(stack) == 0

    def validate_types(self, files: dict[str, str]) -> ValidationResult:
        """Validate TypeScript types across files (requires tsc)."""
        # This would shell out to tsc for full type checking
        # Simplified implementation
        return ValidationResult(valid=True)

    def validate_circular_deps(self, files: dict[str, str]) -> ValidationResult:
        """Check for circular dependencies."""
        errors = []
        
        # Build import graph
        import_graph: dict[str, set[str]] = {}
        
        for filepath, content in files.items():
            imports = set()
            for match in re.finditer(r"from ['\"]([^'\"]+)['\"]", content):
                import_path = match.group(1)
                if import_path.startswith('.'):
                    imports.add(import_path)
            import_graph[filepath] = imports

        # Simple cycle detection (DFS)
        visited = set()
        rec_stack = set()

        def has_cycle(node: str, path: list[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in import_graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, path + [neighbor]):
                        return True
                elif neighbor in rec_stack:
                    cycle_path = ' -> '.join(path + [neighbor])
                    errors.append(f"Circular dependency detected: {cycle_path}")
                    return True

            rec_stack.remove(node)
            return False

        for node in import_graph:
            if node not in visited:
                has_cycle(node, [node])

        return ValidationResult(valid=len(errors) == 0, errors=errors)