"""Domain-specific database patterns."""
from .ecommerce import ECOMMERCE_XML
from .social import SOCIAL_XML
from .saas import SAAS_XML
from .content import CONTENT_XML
from .marketplace import MARKETPLACE_XML
from .common_entities import COMMON_ENTITIES_XML

ALL_PATTERNS_XML = f"""
<application_patterns>
{ECOMMERCE_XML}
{SOCIAL_XML}
{SAAS_XML}
{CONTENT_XML}
{MARKETPLACE_XML}
{COMMON_ENTITIES_XML}
</application_patterns>
"""

__all__ = [
    "ECOMMERCE_XML", "SOCIAL_XML", "SAAS_XML", "CONTENT_XML",
    "MARKETPLACE_XML", "COMMON_ENTITIES_XML", "ALL_PATTERNS_XML"
]