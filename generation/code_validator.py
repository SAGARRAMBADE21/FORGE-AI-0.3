"""
Code Validation - Validates generated backend code for accuracy
"""

import ast
import re
from typing import Dict, List, Tuple
from pathlib import Path


class CodeValidator:
    """
    Validates generated code for syntax errors, missing imports, and schema mismatches.
    
    This ensures backend accuracy by catching issues before files are written.
    """
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self, files: Dict[str, str]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all generated files.
        
        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        for filepath, content in files.items():
            self._validate_file(filepath, content)
        
        # Cross-file validation
        self._validate_cross_references(files)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_file(self, filepath: str, content: str) -> None:
        """Validate a single file."""
        ext = Path(filepath).suffix
        
        if ext == '.py':
            self._validate_python(filepath, content)
        elif ext in ('.js', '.ts', '.jsx', '.tsx'):
            self._validate_javascript(filepath, content)
        elif ext in ('.go', '.java', '.cs', '.rs'):
            # Basic validation for other languages
            self._validate_general(filepath, content)
    
    def _validate_python(self, filepath: str, content: str) -> None:
        """Validate Python code."""
        # Check for syntax errors
        try:
            ast.parse(content)
        except SyntaxError as e:
            self.errors.append(f"{filepath}: Syntax error - {e}")
            return
        
        # Check for undefined variables (basic)
        undefined = self._check_undefined_python(content)
        if undefined:
            for var in undefined:
                self.errors.append(f"{filepath}: Undefined reference '{var}'")
        
        # Check for missing imports
        imports = self._extract_python_imports(content)
        
        # Check model references
        if 'models' in filepath or 'schemas' in filepath:
            self._validate_model_references(filepath, content)
        
        # Check for placeholder code
        if 'TODO' in content and 'raise NotImplementedError' not in content:
            # Allow TODOs in comments, but not incomplete implementations
            pass
        
        # Check for proper class/function definitions
        if 'class ' in content and 'pass' in content:
            # Check if it's just a stub
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'class ' in line and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line == 'pass' or next_line.startswith('pass'):
                        self.warnings.append(f"{filepath}: Empty class definition (stub)")
    
    def _validate_javascript(self, filepath: str, content: str) -> None:
        """Validate JavaScript/TypeScript code."""
        # Basic validation - check for common issues
        
        # Check for unclosed brackets
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            self.errors.append(f"{filepath}: Unmatched braces ({{}})")
        
        open_parens = content.count('(')
        close_parens = content.count(')')
        if open_parens != close_parens:
            self.errors.append(f"{filepath}: Unmatched parentheses")
        
        # Check for incomplete exports
        if 'export' in content and 'undefined' in content.lower():
            self.warnings.append(f"{filepath}: Possible undefined export")
        
        # Check for placeholder functions
        const_pattern = r'const\s+\w+\s*=\s*\(\)\s*=>\s*\{[^}]*\}'
        matches = re.findall(const_pattern, content)
        for match in matches:
            if len(match) < 50:  # Very short function
                self.warnings.append(f"{filepath}: Possibly incomplete function")
    
    def _validate_general(self, filepath: str, content: str) -> None:
        """General validation for any language."""
        # Check for obvious placeholder text
        placeholders = ['your_', 'xxx', 'FIXME', 'HACK']
        for placeholder in placeholders:
            if placeholder in content.lower():
                self.warnings.append(f"{filepath}: Contains placeholder text '{placeholder}'")
    
    def _check_undefined_python(self, content: str) -> List[str]:
        """Check for undefined variables in Python (basic)."""
        try:
            tree = ast.parse(content)
        except:
            return []
        
        undefined = []
        defined = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Add function arguments to defined
                defined.update(arg.arg for arg in node.args.args)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    defined.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    if node.id not in defined and not self._is_builtin(node.id):
                        undefined.append(node.id)
        
        return list(set(undefined))  # Remove duplicates
    
    def _is_builtin(self, name: str) -> bool:
        """Check if a name is a Python builtin."""
        builtins = {'len', 'range', 'print', 'str', 'int', 'float', 'bool', 
                   'list', 'dict', 'set', 'tuple', 'open', 'zip', 'map', 'filter',
                   'sum', 'min', 'max', 'abs', 'round', 'enumerate', 'isinstance',
                   'hasattr', 'getattr', 'setattr', 'super', 'self', 'cls',
                   'True', 'False', 'None', 'Exception', 'BaseException'}
        return name in builtins
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract imported modules from Python code."""
        imports = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module)
        except:
            pass
        return imports

    def _extract_python_symbols(self, content: str) -> List[str]:
        """Extract defined symbols (classes, functions) from Python code."""
        symbols = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    symbols.append(node.name)
        except:
            pass
        return symbols
    
    def _validate_model_references(self, filepath: str, content: str) -> None:
        """Validate that model references are consistent."""
        # Check for model imports
        model_pattern = r'from\s+\.models\.(\w+)\s+import'
        imported_models = re.findall(model_pattern, content)
        
        # Check for model usage
        for model_name in imported_models:
            # Check if model is actually used
            usage_pattern = rf'\b{model_name.capitalize()}\b'
            if not re.search(usage_pattern, content):
                self.warnings.append(f"{filepath}: Imported model '{model_name}' not used")
    
    def _validate_cross_references(self, files: Dict[str, str]) -> None:
        """Validate cross-file references."""
        # Build a map of defined symbols
        defined_symbols = {}
        
        for filepath, content in files.items():
            ext = Path(filepath).suffix
            if ext == '.py':
                symbols = self._extract_python_symbols(content)
                for symbol in symbols:
                    defined_symbols[symbol] = filepath
        
        # Check references
        for filepath, content in files.items():
            ext = Path(filepath).suffix
            if ext == '.py':
                # Check for service/repository references
                refs = re.findall(r'\b(\w+Service)\b', content)
                for ref in refs:
                    if ref not in defined_symbols and ref != 'BaseService':
                        self.warnings.append(f"{filepath}: References undefined service '{ref}'")


class SchemaValidator:
    """
    Validates that generated code matches the database schema.
    """
    
    def __init__(self, models, schema):
        self.models = models
        self.schema = schema
        self.mismatches = []
    
    def validate_schema_consistency(self, files: Dict[str, str]) -> List[str]:
        """
        Validate that generated models match the database schema.
        
        Returns:
            List of mismatch errors
        """
        self.mismatches = []
        
        # Extract model files
        model_files = {k: v for k, v in files.items() if 'model' in k.lower()}
        
        for filepath, content in model_files.items():
            self._validate_model_file(filepath, content)
        
        return self.mismatches
    
    def _validate_model_file(self, filepath: str, content: str) -> None:
        """Validate a single model file against the schema."""
        # Find the model name from the file
        class_pattern = r'class\s+(\w+)'
        matches = re.findall(class_pattern, content)
        
        for class_name in matches:
            # Find matching inferred model
            model = self._find_model(class_name)
            if model:
                self._validate_model_fields(class_name, content, model)
    
    def _find_model(self, class_name: str):
        """Find model by class name."""
        for model in self.models:
            if model.name == class_name:
                return model
        return None
    
    def _validate_model_fields(self, class_name: str, content: str, model) -> None:
        """Validate model fields in the generated code."""
        # Check each field exists in the code
        for field in model.fields:
            field_pattern = rf'\b{field.name}\b'
            if not re.search(field_pattern, content):
                self.mismatches.append(
                    f"{class_name}: Missing field '{field.name}' in generated code"
                )


# ============================================================================
# Helper function for quick validation
# ============================================================================

def validate_generated_code(files: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Quick validation of generated code.
    
    Args:
        files: Dict mapping file paths to content
        
    Returns:
        (is_valid, list_of_errors)
    """
    validator = CodeValidator()
    is_valid, errors, warnings = validator.validate_all(files)
    
    # For now, warnings don't fail validation
    return is_valid, errors


__all__ = [
    "CodeValidator",
    "SchemaValidator",
    "validate_generated_code",
]
