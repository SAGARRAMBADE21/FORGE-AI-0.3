# generation/prompts/principles/__init__.py
"""
Software Engineering Principles Prompts
"""

from .clean_code_prompt import CLEAN_CODE_PROMPT
from .solid_prompt import SOLID_PROMPT
from .dry_kiss_yagni_prompt import DRY_KISS_YAGNI_PROMPT
from .design_patterns_prompt import DESIGN_PATTERNS_PROMPT

PRINCIPLES_PROMPTS = {
    "clean_code": CLEAN_CODE_PROMPT,
    "solid": SOLID_PROMPT,
    "dry_kiss_yagni": DRY_KISS_YAGNI_PROMPT,
    "design_patterns": DESIGN_PATTERNS_PROMPT
}

__all__ = [
    "PRINCIPLES_PROMPTS",
    "CLEAN_CODE_PROMPT",
    "SOLID_PROMPT",
    "DRY_KISS_YAGNI_PROMPT",
    "DESIGN_PATTERNS_PROMPT"
]