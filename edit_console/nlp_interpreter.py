"""
NLP Interpreter - parses natural language edit commands using LLM
"""

import json
import re
from typing import Optional
from .models import EditIntent, FileContext, ActionType, TargetType, TargetLocation, Changes


class NLPInterpreter:
    """Interprets natural language edit commands"""
    
    def __init__(self, llm_client=None):
        """
        Initialize NLP interpreter
        
        Args:
            llm_client: Optional LLM client (uses FORGE settings if None)
        """
        self.llm = llm_client
        self.fallback_patterns = self._init_fallback_patterns()
    
    def parse_command(self, command: str, context: Optional[FileContext] = None) -> EditIntent:
        """
        Parse natural language command into structured EditIntent
        
        Args:
            command: Natural language edit command
            context: Current file context
            
        Returns:
            EditIntent with parsed action, target, and changes
        """
        # Try LLM parsing first
        if self.llm:
            try:
                return self._parse_with_llm(command, context)
            except Exception as e:
                print(f"LLM parsing failed: {e}, falling back to patterns")
        
        # Fallback to pattern matching
        return self._parse_with_patterns(command, context)
    
    def _parse_with_llm(self, command: str, context: Optional[FileContext]) -> EditIntent:
        """Parse command using LLM"""
        context_info = ""
        if context:
            context_info = f"""
Current file context:
- Filename: {context.filename}
- Type: {context.file_type.value}
- Summary: {context.summary}
- Lines: {context.line_count}
"""
        
        prompt = f"""You are a code/schema editing assistant. Parse this edit command into a structured format.

Command: "{command}"

{context_info}

Return ONLY a valid JSON object with this structure:
{{
  "action": "rename|add|remove|modify|replace|insert|delete",
  "target_type": "table|field|column|function|class|method|line|value|property|file",
  "target_location": {{
    "name": "target name or identifier",
    "line_start": null or line number,
    "line_end": null or line number
  }},
  "changes": {{
    "old_value": "current value to change (if applicable)",
    "new_value": "new value to set",
    "additional_params": {{}}
  }},
  "confidence": 0.0-1.0
}}

Examples:
Command: "change table name from users to accounts"
{{
  "action": "rename",
  "target_type": "table",
  "target_location": {{"name": "users"}},
  "changes": {{"old_value": "users", "new_value": "accounts"}},
  "confidence": 0.95
}}

Command: "make email field required"
{{
  "action": "modify",
  "target_type": "field",
  "target_location": {{"name": "email"}},
  "changes": {{"new_value": "required", "additional_params": {{"constraint": "NOT NULL"}}}},
  "confidence": 0.9
}}

Now parse the given command and return ONLY the JSON:"""
        
        # Call LLM (placeholder - integrate with FORGE's LLM)
        response = self._call_llm(prompt)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                data['raw_command'] = command
                return EditIntent.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        
        raise ValueError("LLM did not return valid JSON")
    
    def _parse_with_patterns(self, command: str, context: Optional[FileContext]) -> EditIntent:
        """Parse command using regex patterns (fallback)"""
        command_lower = command.lower().strip()
        
        # Try each pattern
        for pattern_info in self.fallback_patterns:
            match = pattern_info['pattern'].search(command_lower)
            if match:
                return pattern_info['handler'](match, command)
        
        # Default: treat as line modification
        return EditIntent(
            action=ActionType.MODIFY,
            target_type=TargetType.LINE,
            target_location=TargetLocation(),
            changes=Changes(new_value=command),
            confidence=0.3,
            raw_command=command
        )
    
    def _init_fallback_patterns(self):
        """Initialize regex patterns for common commands"""
        return [
            # Rename patterns
            {
                'pattern': re.compile(r'(?:rename|change)\s+(?:table|field|column|function)\s+(?:name\s+)?(?:from\s+)?["\']?(\w+)["\']?\s+to\s+["\']?(\w+)["\']?'),
                'handler': self._handle_rename
            },
            # Change type patterns
            {
                'pattern': re.compile(r'change\s+(\w+)\s+(?:field|column)\s+(?:type\s+)?to\s+(\w+)'),
                'handler': self._handle_change_type
            },
            # Add field pattern
            {
                'pattern': re.compile(r'add\s+(\w+)\s+(?:field|column)\s+(?:of\s+type\s+)?(\w+)?'),
                'handler': self._handle_add_field
            },
            # Remove pattern
            {
                'pattern': re.compile(r'remove\s+(?:the\s+)?(\w+)\s+(?:field|column|table|function)'),
                'handler': self._handle_remove
            },
            # Make field required/unique
            {
                'pattern': re.compile(r'make\s+(\w+)\s+(?:field\s+)?(required|unique|nullable|non-nullable)'),
                'handler': self._handle_make_constraint
            },
        ]
    
    def _handle_rename(self, match, command):
        """Handle rename commands"""
        old_name = match.group(1)
        new_name = match.group(2)
        
        # Detect target type from command
        target_type = TargetType.TABLE
        if 'field' in command or 'column' in command:
            target_type = TargetType.FIELD
        elif 'function' in command:
            target_type = TargetType.FUNCTION
        
        return EditIntent(
            action=ActionType.RENAME,
            target_type=target_type,
            target_location=TargetLocation(name=old_name),
            changes=Changes(old_value=old_name, new_value=new_name),
            confidence=0.9,
            raw_command=command
        )
    
    def _handle_change_type(self, match, command):
        """Handle change type commands"""
        field_name = match.group(1)
        new_type = match.group(2)
        
        return EditIntent(
            action=ActionType.MODIFY,
            target_type=TargetType.FIELD,
            target_location=TargetLocation(name=field_name),
            changes=Changes(new_value=new_type, additional_params={'property': 'type'}),
            confidence=0.85,
            raw_command=command
        )
    
    def _handle_add_field(self, match, command):
        """Handle add field commands"""
        field_name = match.group(1)
        field_type = match.group(2) if match.group(2) else "VARCHAR(255)"
        
        return EditIntent(
            action=ActionType.ADD,
            target_type=TargetType.FIELD,
            target_location=TargetLocation(name=field_name),
            changes=Changes(new_value=field_name, additional_params={'type': field_type}),
            confidence=0.8,
            raw_command=command
        )
    
    def _handle_remove(self, match, command):
        """Handle remove commands"""
        target_name = match.group(1)
        
        target_type = TargetType.FIELD
        if 'table' in command:
            target_type = TargetType.TABLE
        elif 'function' in command:
            target_type = TargetType.FUNCTION
        
        return EditIntent(
            action=ActionType.REMOVE,
            target_type=target_type,
            target_location=TargetLocation(name=target_name),
            changes=Changes(),
            confidence=0.85,
            raw_command=command
        )
    
    def _handle_make_constraint(self, match, command):
        """Handle make field required/unique/etc commands"""
        field_name = match.group(1)
        constraint = match.group(2)
        
        constraint_map = {
            'required': 'NOT NULL',
            'unique': 'UNIQUE',
            'nullable': 'NULL',
            'non-nullable': 'NOT NULL'
        }
        
        return EditIntent(
            action=ActionType.MODIFY,
            target_type=TargetType.FIELD,
            target_location=TargetLocation(name=field_name),
            changes=Changes(
                new_value=constraint_map.get(constraint, constraint),
                additional_params={'property': 'constraint', 'constraint_type': constraint}
            ),
            confidence=0.9,
            raw_command=command
        )
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt (placeholder for FORGE integration)"""
        # TODO: Integrate with FORGE's LLM client
        # For now, just raise to force fallback
        raise NotImplementedError("LLM integration pending")
