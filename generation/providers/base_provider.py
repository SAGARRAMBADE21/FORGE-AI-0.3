# generation/providers/base_provider.py
"""
Base Provider - Abstract base class for LLM providers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    model: str
    max_tokens: int = 2048
    temperature: float = 0.1

    # Provider-specific options
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 120
    extra_options: Dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement:
    - generate(): Single response generation
    - generate_stream(): Streaming response generation
    - validate_config(): Check if provider is properly configured
    """

    # Provider identification
    name: str = "base"
    display_name: str = "Base Provider"

    # Supported features
    supports_streaming: bool = True
    supports_system_prompt: bool = True
    supports_json_mode: bool = False

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client = None

    @abstractmethod
    def _initialize_client(self):
        """Initialize the provider's API client."""
        pass

    @property
    def client(self):
        """Lazy-load the API client."""
        if self._client is None:
            self._client = self._initialize_client()
        return self._client

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User's request
            **kwargs: Additional provider-specific options

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def generate_stream(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User's request
            **kwargs: Additional provider-specific options

        Yields:
            Chunks of generated text
        """
        pass

    def validate_config(self) -> tuple[bool, str]:
        """
        Validate that the provider is properly configured.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.config.api_key:
            return False, f"API key not set for {self.display_name}"
        return True, ""

    def get_info(self) -> Dict[str, Any]:
        """Get provider information."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "model": self.config.model,
            "supports_streaming": self.supports_streaming,
            "supports_system_prompt": self.supports_system_prompt,
        }
