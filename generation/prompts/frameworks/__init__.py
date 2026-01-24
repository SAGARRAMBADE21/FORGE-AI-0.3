# generation/prompts/frameworks/__init__.py
"""
Framework-Specific Prompts
"""

from .django_prompt import DJANGO_PROMPT
from .dotnet_prompt import DOTNET_PROMPT
from .express_prompt import EXPRESS_PROMPT
from .fastapi_prompt import FASTAPI_PROMPT
from .flask_prompt import FLASK_PROMPT
from .gin_prompt import GIN_PROMPT
from .nestjs_prompt import NESTJS_PROMPT
from .spring_prompt import SPRING_PROMPT

FRAMEWORK_PROMPTS = {
    "express": EXPRESS_PROMPT,
    "nestjs": NESTJS_PROMPT,
    "fastapi": FASTAPI_PROMPT,
    "flask": FLASK_PROMPT,
    "django": DJANGO_PROMPT,
    "gin": GIN_PROMPT,
    "spring": SPRING_PROMPT,
    "dotnet": DOTNET_PROMPT,
}

__all__ = [
    "FRAMEWORK_PROMPTS",
    "EXPRESS_PROMPT",
    "NESTJS_PROMPT",
    "FASTAPI_PROMPT",
    "FLASK_PROMPT",
    "DJANGO_PROMPT",
    "GIN_PROMPT",
    "SPRING_PROMPT",
    "DOTNET_PROMPT",
]
