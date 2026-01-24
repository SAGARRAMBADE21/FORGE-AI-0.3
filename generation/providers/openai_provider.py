# generation/providers/openai_provider.py
"""
OpenAI/OpenRouter Provider - Handles OpenAI-compatible API calls.
"""

import logging
import os
from typing import AsyncIterator, Optional

from .base_provider import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI and OpenAI-compatible APIs (OpenRouter)."""

    name = "openai"
    display_name = "OpenAI"
    supports_streaming = True
    supports_system_prompt = True
    supports_json_mode = True

    def __init__(self, config: ProviderConfig, is_openrouter: bool = False):
        super().__init__(config)
        self.is_openrouter = is_openrouter

        if is_openrouter:
            self.name = "openrouter"
            self.display_name = "OpenRouter"

    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI package not installed.\n" "Run: pip install openai"
            )

        # Get API key
        if self.is_openrouter:
            api_key = self.config.api_key or os.getenv("OPENROUTER_API_KEY")
            base_url = self.config.base_url or "https://openrouter.ai/api/v1"

            if not api_key:
                raise ValueError(
                    "❌ OpenRouter API key not found!\n"
                    "   Set OPENROUTER_API_KEY in your .env file\n"
                    "   Get your key at: https://openrouter.ai/keys"
                )
        else:
            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            base_url = self.config.base_url

            if not api_key:
                raise ValueError(
                    "❌ OpenAI API key not found!\n"
                    "   Set OPENAI_API_KEY in your .env file\n"
                    "   Get your key at: https://platform.openai.com/api-keys"
                )

        return openai.OpenAI(api_key=api_key, base_url=base_url)

    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate a response using OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.config.model,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    async def generate_stream(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response using OpenAI API."""
        stream = self.client.chat.completions.create(
            model=self.config.model,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class OpenRouterProvider(OpenAIProvider):
    """Convenience class for OpenRouter."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, is_openrouter=True)
