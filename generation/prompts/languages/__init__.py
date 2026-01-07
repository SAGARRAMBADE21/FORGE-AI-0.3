# generation/prompts/languages/__init__.py
"""
Language-Specific Prompts
"""

from .typescript_prompt import TYPESCRIPT_PROMPT
from .python_prompt import PYTHON_PROMPT
from .go_prompt import GO_PROMPT
from .rust_prompt import RUST_PROMPT
from .java_prompt import JAVA_PROMPT
from .csharp_prompt import CSHARP_PROMPT

LANGUAGE_PROMPTS = {
    "typescript": TYPESCRIPT_PROMPT,
    "python": PYTHON_PROMPT,
    "go": GO_PROMPT,
    "rust": RUST_PROMPT,
    "java": JAVA_PROMPT,
    "csharp": CSHARP_PROMPT
}

__all__ = [
    "LANGUAGE_PROMPTS",
    "TYPESCRIPT_PROMPT",
    "PYTHON_PROMPT",
    "GO_PROMPT",
    "RUST_PROMPT",
    "JAVA_PROMPT",
    "CSHARP_PROMPT"
]