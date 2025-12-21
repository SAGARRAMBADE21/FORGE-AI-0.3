"""LLM-based code generation for complex logic."""

import logging
import asyncio
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


class LLMCodeGenerator:
    """
    Generate code using LLM for complex business logic.
    
    Uses templates for structure, LLM for logic.
    """

    def __init__(self, client=None, provider="groq"):
        self._client = client
        self._provider = provider
        self._model = self._get_default_model()
        self._max_retries = 3

    def _get_default_model(self) -> str:
        """Get default model based on provider."""
        models = {
            "groq": "llama-3.3-70b-versatile",
            "anthropic": "claude-3-5-sonnet-20241022",
            "openai": "gpt-4-turbo-preview"
        }
        return models.get(self._provider, "llama-3.3-70b-versatile")

    async def _ensure_client(self):
        """Ensure LLM client is initialized."""
        if self._client is None:
            try:
                if self._provider == "groq":
                    from groq import AsyncGroq
                    import os
                    self._client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
                elif self._provider == "anthropic":
                    from anthropic import AsyncAnthropic
                    self._client = AsyncAnthropic()
                elif self._provider == "openai":
                    from openai import AsyncOpenAI
                    self._client = AsyncOpenAI()
                else:
                    raise ValueError(f"Unknown provider: {self._provider}")
            except ImportError as e:
                logger.warning(f"{self._provider} not installed: {e}, using mock client")
                self._client = MockLLMClient()
            except Exception as e:
                logger.warning(f"Failed to initialize {self._provider}: {e}, using mock client")
                self._client = MockLLMClient()

    async def generate_business_logic(
        self,
        service_name: str,
        method_name: str,
        context: dict[str, Any]
    ) -> str:
        """Generate business logic for a service method."""
        await self._ensure_client()

        prompt = self._build_logic_prompt(service_name, method_name, context)
        
        for attempt in range(self._max_retries):
            try:
                response = await self._complete(prompt)
                code = self._extract_code(response)
                
                if self._validate_code(code):
                    return code
                
                logger.warning(f"Invalid code generated, retry {attempt + 1}")
            except Exception as e:
                logger.error(f"LLM generation error: {e}")
                if attempt == self._max_retries - 1:
                    raise

        return self._get_fallback_logic(method_name)

    async def generate_validation_schema(
        self,
        model_name: str,
        fields: list[dict],
        operation: str = "create"
    ) -> str:
        """Generate Zod validation schema."""
        await self._ensure_client()

        prompt = f"""Generate a Zod validation schema for {operation} operation on {model_name}.

Fields:
{self._format_fields(fields)}

Requirements:
- Use Zod for validation
- Add appropriate constraints based on field names
- Email fields should use .email()
- Password fields should have min length 8
- Optional fields should use .optional()
- Export the schema

Return only the TypeScript code, no explanations."""

        response = await self._complete(prompt)
        return self._extract_code(response)

    async def generate_test(
        self,
        component_type: str,
        component_name: str,
        methods: list[dict]
    ) -> str:
        """Generate test file for a component."""
        await self._ensure_client()

        prompt = f"""Generate Jest/Vitest tests for a {component_type} named {component_name}.

Methods to test:
{self._format_methods(methods)}

Requirements:
- Use describe/it blocks
- Mock dependencies
- Test success and error cases
- Use meaningful assertions

Return only the TypeScript test code."""

        response = await self._complete(prompt)
        return self._extract_code(response)

    async def generate_migration_logic(
        self,
        operation: str,
        details: dict
    ) -> str:
        """Generate complex migration logic."""
        await self._ensure_client()

        prompt = f"""Generate SQL migration for: {operation}

Details: {details}

Requirements:
- PostgreSQL syntax
- Include both UP and DOWN migrations
- Handle data preservation where needed
- Use transactions

Return the migration in format:
-- UP
<up migration SQL>

-- DOWN
<down migration SQL>"""

        response = await self._complete(prompt)
        return response

    async def _complete(self, prompt: str) -> str:
        """Complete a prompt using LLM."""
        if isinstance(self._client, MockLLMClient):
            return await self._client.complete(prompt)

        if self._provider == "groq":
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.3
            )
            return response.choices[0].message.content
        elif self._provider == "anthropic":
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        elif self._provider == "openai":
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.3
            )
            return response.choices[0].message.content
        else:
            raise ValueError(f"Unknown provider: {self._provider}")

    def _build_logic_prompt(
        self,
        service_name: str,
        method_name: str,
        context: dict
    ) -> str:
        """Build prompt for business logic generation."""
        return f"""Generate TypeScript business logic for {service_name}.{method_name}.

Context:
- Model: {context.get('model', 'Unknown')}
- Parameters: {context.get('parameters', [])}
- Return type: {context.get('return_type', 'void')}
- Repository methods available: {context.get('repo_methods', [])}

Requirements:
- Handle errors appropriately
- Add input validation
- Include logging
- Follow clean code principles

Return only the method body (inside the function), no function declaration."""

    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response."""
        # Try to find code blocks
        import re
        
        code_block = re.search(r'```(?:typescript|javascript|ts|js)?\n(.*?)```', response, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()
        
        # If no code block, return cleaned response
        return response.strip()

    def _validate_code(self, code: str) -> bool:
        """Basic validation of generated code."""
        if not code:
            return False
        
        # Check for common syntax errors
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            return False
        
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            return False
        
        return True

    def _get_fallback_logic(self, method_name: str) -> str:
        """Get fallback logic when generation fails."""
        fallbacks = {
            'create': 'return this.repository.create(data);',
            'update': 'return this.repository.update(id, data);',
            'delete': 'await this.repository.delete(id);',
            'getById': 'return this.repository.findById(id);',
            'getAll': 'return this.repository.findMany(filter);',
        }
        return fallbacks.get(method_name, '// TODO: Implement business logic')

    def _format_fields(self, fields: list[dict]) -> str:
        """Format fields for prompt."""
        lines = []
        for f in fields:
            line = f"- {f['name']}: {f.get('type', 'string')}"
            if f.get('required'):
                line += " (required)"
            if f.get('constraints'):
                line += f" constraints: {f['constraints']}"
            lines.append(line)
        return '\n'.join(lines)

    def _format_methods(self, methods: list[dict]) -> str:
        """Format methods for prompt."""
        lines = []
        for m in methods:
            params = ', '.join(p['name'] for p in m.get('parameters', []))
            lines.append(f"- {m['name']}({params}): {m.get('return_type', 'void')}")
        return '\n'.join(lines)


class MockLLMClient:
    """Mock LLM client for testing without API."""

    async def complete(self, prompt: str) -> str:
        """Return mock completion."""
        await asyncio.sleep(0.1)  # Simulate API delay
        
        if 'validation' in prompt.lower():
            return """```typescript
import { z } from 'zod';

export const schema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
});
```"""
        
        if 'test' in prompt.lower():
            return """```typescript
import { describe, it, expect, vi } from 'vitest';

describe('Component', () => {
  it('should work', () => {
    expect(true).toBe(true);
  });
});
```"""
        
        return "// Generated code placeholder"