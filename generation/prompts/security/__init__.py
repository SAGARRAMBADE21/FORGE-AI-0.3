# generation/prompts/security/__init__.py
"""
Security Prompts
"""

from .owasp_prompt import OWASP_PROMPT
from .rbac_prompt import RBAC_PROMPT
from .encryption_prompt import ENCRYPTION_PROMPT
from .secrets_management_prompt import SECRETS_MANAGEMENT_PROMPT
from .vulnerability_scanning_prompt import VULNERABILITY_SCANNING_PROMPT

SECURITY_PROMPTS = {
    "owasp": OWASP_PROMPT,
    "rbac": RBAC_PROMPT,
    "encryption": ENCRYPTION_PROMPT,
    "secrets_management": SECRETS_MANAGEMENT_PROMPT,
    "vulnerability_scanning": VULNERABILITY_SCANNING_PROMPT
}

__all__ = [
    "SECURITY_PROMPTS",
    "OWASP_PROMPT",
    "RBAC_PROMPT",
    "ENCRYPTION_PROMPT",
    "SECRETS_MANAGEMENT_PROMPT",
    "VULNERABILITY_SCANNING_PROMPT"
]