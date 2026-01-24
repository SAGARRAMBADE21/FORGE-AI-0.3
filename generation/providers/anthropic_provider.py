# generation/providers/anthropic_provider.py
"""
Anthropic Provider - Handles Claude API calls.
"""

import logging
import os
from typing import AsyncIterator

from .base_provider import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models."""

    name = "anthropic"
    display_name = "Anthropic Claude"
    supports_streaming = True
    supports_system_prompt = True
    supports_json_mode = False

    def _initialize_client(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "Anthropic package not installed.\n" "Run: pip install anthropic"
            )

        api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError(
                "❌ Anthropic API key not found!\n"
                "   Set ANTHROPIC_API_KEY in your .env file\n"
                "   Get your key at: https://console.anthropic.com/"
            )

        return anthropic.Anthropic(api_key=api_key)

    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate a response using Claude."""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    async def generate_stream(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response using Claude."""
        with self.client.messages.stream(
            model=self.config.model,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
