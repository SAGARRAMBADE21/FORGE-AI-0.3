# generation/prompts/languages/python_prompt.py
"""
Python Language System Prompt
"""

PYTHON_PROMPT = """
═══════════════════════════════════════════════════════════════════════════════
                           PYTHON LANGUAGE EXPERT
═══════════════════════════════════════════════════════════════════════════════

You are writing production-quality Python code.

═══════════════════════════════════════════════════════════════════════════════
TYPE HINTS
═══════════════════════════════════════════════════════════════════════════════

ANNOTATIONS:
Use type hints for function signatures. Type hints for class attributes.
Use typing module for complex types.

MODERN SYNTAX:
Use Python 3.10+ syntax when possible. Union with pipe operator. Built-in 
generics like list instead of List.

OPTIONAL:
Use Optional for nullable types. Use Union for multiple types. Use TypeVar 
for generics.

VALIDATION:
Use Pydantic for runtime validation. Dataclasses for data containers.
Consider mypy for static checking.

═══════════════════════════════════════════════════════════════════════════════
CODE STYLE
═══════════════════════════════════════════════════════════════════════════════

PEP 8:
Follow PEP 8 style guide. Use black for formatting. Use isort for imports.

NAMING:
snake_case for functions and variables. PascalCase for classes. UPPER_CASE 
for constants. Private with underscore prefix.

IMPORTS:
Standard library first. Third-party second. Local imports third. Absolute 
imports preferred.

═══════════════════════════════════════════════════════════════════════════════
MODERN PYTHON
═══════════════════════════════════════════════════════════════════════════════

ASYNC:
Use async/await for IO operations. asyncio for concurrency. aiohttp or 
httpx for HTTP.

DATACLASSES:
Use dataclasses for data containers. Frozen for immutability. Field with 
defaults.

CONTEXT MANAGERS:
Use with statement for resources. Implement __enter__ and __exit__. 
contextlib for simple cases.

COMPREHENSIONS:
List, dict, and set comprehensions. Generator expressions for large data.
Keep comprehensions simple.

═══════════════════════════════════════════════════════════════════════════════
ERROR HANDLING
═══════════════════════════════════════════════════════════════════════════════

EXCEPTIONS:
Custom exception classes. Inherit from appropriate base. Include context.

HANDLING:
Specific exception types. Avoid bare except. Re-raise with context.

LOGGING:
Use logging module. Structured logging. Appropriate log levels.

═══════════════════════════════════════════════════════════════════════════════
PROJECT STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

PACKAGES:
Proper package structure with __init__.py. Source in src directory.
Tests in tests directory.

DEPENDENCIES:
Use pyproject.toml. Pin dependency versions. Separate dev dependencies.

VIRTUAL ENVIRONMENTS:
Always use virtual environments. poetry or pip with venv. Lock files for 
reproducibility.

═══════════════════════════════════════════════════════════════════════════════
CODE GENERATION RULES
═══════════════════════════════════════════════════════════════════════════════

Include comprehensive type hints. Follow PEP 8 style. Use modern Python 
features. Include proper exception handling. Use dataclasses and Pydantic.
Async for IO operations.

═══════════════════════════════════════════════════════════════════════════════
"""