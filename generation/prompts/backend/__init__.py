# generation/prompts/backend/__init__.py
"""
Backend Development Prompts

This module contains comprehensive prompts for all aspects of backend development.
Use BACKEND_MASTER_PROMPT for a comprehensive overview, or specific prompts for
detailed guidance on particular topics.
"""

from .backend_master_prompt import BACKEND_MASTER_PROMPT
from .business_logic_prompt import BUSINESS_LOGIC_PROMPT
from .caching_strategies_prompt import CACHING_STRATEGIES_PROMPT
from .code_quality_checklist_prompt import CODE_QUALITY_CHECKLIST_PROMPT
from .critical_files_prompt import CRITICAL_FILES_PROMPT
from .error_handling_prompt import ERROR_HANDLING_PROMPT
from .http_fundamentals_prompt import HTTP_FUNDAMENTALS_PROMPT
from .middleware_prompt import MIDDLEWARE_PROMPT
from .observability_prompt import OBSERVABILITY_PROMPT
from .realtime_systems_prompt import REALTIME_SYSTEMS_PROMPT
from .scaling_performance_prompt import SCALING_PERFORMANCE_PROMPT
from .task_queuing_prompt import TASK_QUEUING_PROMPT
from .validation_prompt import VALIDATION_PROMPT

__all__ = [
    "BACKEND_MASTER_PROMPT",
    "HTTP_FUNDAMENTALS_PROMPT",
    "MIDDLEWARE_PROMPT",
    "VALIDATION_PROMPT",
    "BUSINESS_LOGIC_PROMPT",
    "ERROR_HANDLING_PROMPT",
    "CACHING_STRATEGIES_PROMPT",
    "CODE_QUALITY_CHECKLIST_PROMPT",
    "CRITICAL_FILES_PROMPT",
    "TASK_QUEUING_PROMPT",
    "OBSERVABILITY_PROMPT",
    "SCALING_PERFORMANCE_PROMPT",
    "REALTIME_SYSTEMS_PROMPT",
]
