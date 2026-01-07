# generation/prompts/performance/__init__.py
"""
Performance Prompts
"""

from .scaling_prompt import SCALING_PROMPT
from .caching_prompt import CACHING_PROMPT
from .load_balancing_prompt import LOAD_BALANCING_PROMPT
from .message_queue_prompt import MESSAGE_QUEUE_PROMPT
from .disaster_recovery_prompt import DISASTER_RECOVERY_PROMPT

PERFORMANCE_PROMPTS = {
    "scaling": SCALING_PROMPT,
    "caching": CACHING_PROMPT,
    "load_balancing": LOAD_BALANCING_PROMPT,
    "message_queue": MESSAGE_QUEUE_PROMPT,
    "disaster_recovery": DISASTER_RECOVERY_PROMPT
}

__all__ = [
    "PERFORMANCE_PROMPTS",
    "SCALING_PROMPT",
    "CACHING_PROMPT",
    "LOAD_BALANCING_PROMPT",
    "MESSAGE_QUEUE_PROMPT",
    "DISASTER_RECOVERY_PROMPT"
]