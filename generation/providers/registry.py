# generation/providers/registry.py
"""
Provider Registry - Manages LLM provider registration and lookup.
"""

import logging
from typing import Dict, Optional, Type

from .base_provider import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


# Global provider registry
PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]):
    """
    Register a provider class.

    Args:
        name: Provider name (e.g., 'openai', 'anthropic')
        provider_class: The provider class to register
    """
    PROVIDER_REGISTRY[name.lower()] = provider_class
    logger.debug(f"Registered provider: {name}")


def get_provider(name: str, model: str, **kwargs) -> BaseProvider:
    """
    Get a provider instance by name.

    Args:
        name: Provider name
        model: Model to use
        **kwargs: Additional config options

    Returns:
        Configured provider instance
    """
    name_lower = name.lower()

    # Lazy import and register providers
    if not PROVIDER_REGISTRY:
        _register_default_providers()

    if name_lower not in PROVIDER_REGISTRY:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"❌ Unknown provider: {name}\n" f"   Available providers: {available}"
        )

    config = ProviderConfig(model=model, **kwargs)
    return PROVIDER_REGISTRY[name_lower](config)


def _register_default_providers():
    """Register all default providers."""
    try:
        from .openai_provider import OpenAIProvider, OpenRouterProvider

        register_provider("openai", OpenAIProvider)
        register_provider("openrouter", OpenRouterProvider)
    except ImportError:
        logger.debug("OpenAI provider not available")

    try:
        from .anthropic_provider import AnthropicProvider

        register_provider("anthropic", AnthropicProvider)
    except ImportError:
        logger.debug("Anthropic provider not available")

    try:
        from .gemini_provider import GeminiProvider

        register_provider("gemini", GeminiProvider)
    except ImportError:
        logger.debug("Gemini provider not available")

    try:
        from .groq_provider import GroqProvider

        register_provider("groq", GroqProvider)
    except ImportError:
        logger.debug("Groq provider not available")

    try:
        from .huggingface_provider import HuggingFaceProvider

        register_provider("huggingface", HuggingFaceProvider)
    except ImportError:
        logger.debug("HuggingFace provider not available")


def list_providers() -> Dict[str, str]:
    """List all registered providers with their display names."""
    if not PROVIDER_REGISTRY:
        _register_default_providers()

    return {name: cls.display_name for name, cls in PROVIDER_REGISTRY.items()}
