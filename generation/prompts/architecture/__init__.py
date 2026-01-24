# generation/prompts/architecture/__init__.py
"""
Architecture Prompts
"""

from .cqrs_prompt import CQRS_PROMPT
from .ddd_prompt import DDD_PROMPT
from .event_driven_prompt import EVENT_DRIVEN_PROMPT
from .microservices_prompt import MICROSERVICES_PROMPT
from .monolithic_prompt import MONOLITHIC_PROMPT
from .serverless_prompt import SERVERLESS_PROMPT

ARCHITECTURE_PROMPTS = {
    "microservices": MICROSERVICES_PROMPT,
    "monolithic": MONOLITHIC_PROMPT,
    "serverless": SERVERLESS_PROMPT,
    "ddd": DDD_PROMPT,
    "event_driven": EVENT_DRIVEN_PROMPT,
    "cqrs": CQRS_PROMPT,
}

__all__ = [
    "ARCHITECTURE_PROMPTS",
    "MICROSERVICES_PROMPT",
    "MONOLITHIC_PROMPT",
    "SERVERLESS_PROMPT",
    "DDD_PROMPT",
    "EVENT_DRIVEN_PROMPT",
    "CQRS_PROMPT",
]
