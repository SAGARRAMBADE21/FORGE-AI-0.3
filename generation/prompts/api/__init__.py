# generation/prompts/api/__init__.py
"""
API Design Prompts
"""

from .graphql_prompt import GRAPHQL_PROMPT
from .grpc_prompt import GRPC_PROMPT
from .pagination_prompt import PAGINATION_PROMPT
from .rate_limiting_prompt import RATE_LIMITING_PROMPT
from .rest_prompt import REST_PROMPT
from .versioning_prompt import VERSIONING_PROMPT

API_PROMPTS = {
    "rest": REST_PROMPT,
    "graphql": GRAPHQL_PROMPT,
    "grpc": GRPC_PROMPT,
    "versioning": VERSIONING_PROMPT,
    "pagination": PAGINATION_PROMPT,
    "rate_limiting": RATE_LIMITING_PROMPT,
}

__all__ = [
    "API_PROMPTS",
    "REST_PROMPT",
    "GRAPHQL_PROMPT",
    "GRPC_PROMPT",
    "VERSIONING_PROMPT",
    "PAGINATION_PROMPT",
    "RATE_LIMITING_PROMPT",
]
