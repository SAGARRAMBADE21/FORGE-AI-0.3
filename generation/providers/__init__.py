# generation/providers/__init__.py
"""
LLM Provider Abstraction Layer

This module provides a clean, extensible interface for different LLM providers.
Adding a new provider is as simple as:
1. Create a new file in this directory (e.g., my_provider.py)
2. Inherit from BaseProvider
3. Implement the required methods
4. Register in PROVIDER_REGISTRY
"""

from .base_provider import BaseProvider, ProviderConfig
from .registry import PROVIDER_REGISTRY, get_provider, list_providers, register_provider

__all__ = [
    "BaseProvider",
    "ProviderConfig",
    "get_provider",
    "register_provider",
    "list_providers",
    "PROVIDER_REGISTRY",
]
