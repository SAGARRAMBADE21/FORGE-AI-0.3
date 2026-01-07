# generation/prompts/auth/__init__.py
"""
Authentication Prompts
"""

from .jwt_prompt import JWT_PROMPT
from .oauth2_prompt import OAUTH2_PROMPT
from .sso_prompt import SSO_PROMPT
from .mfa_prompt import MFA_PROMPT
from .ldap_prompt import LDAP_PROMPT
from .session_management_prompt import SESSION_MANAGEMENT_PROMPT

AUTH_PROMPTS = {
    "jwt": JWT_PROMPT,
    "oauth2": OAUTH2_PROMPT,
    "sso": SSO_PROMPT,
    "mfa": MFA_PROMPT,
    "ldap": LDAP_PROMPT,
    "session_management": SESSION_MANAGEMENT_PROMPT
}

__all__ = [
    "AUTH_PROMPTS",
    "JWT_PROMPT",
    "OAUTH2_PROMPT",
    "SSO_PROMPT",
    "MFA_PROMPT",
    "LDAP_PROMPT",
    "SESSION_MANAGEMENT_PROMPT"
]