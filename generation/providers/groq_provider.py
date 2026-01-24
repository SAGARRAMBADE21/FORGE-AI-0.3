# generation/providers/groq_provider.py
"""
Groq Provider - Handles Groq API calls for fast inference.
"""

import logging
import os
from typing import AsyncIterator

from .base_provider import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class GroqProvider(BaseProvider):
    """
    Provider for Groq's fast LLM inference.

    Groq provides very fast inference for open-source models like Llama.
    Free tier has generous limits.
    """

    name = "groq"
    display_name = "Groq"
    supports_streaming = True
    supports_system_prompt = True
    supports_json_mode = True

    def _initialize_client(self):
        """Initialize Groq client."""
        try:
            import groq
        except ImportError:
            raise ImportError("Groq package not installed.\n" "Run: pip install groq")

        api_key = self.config.api_key or os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "❌ Groq API key not found!\n"
                "   Set GROQ_API_KEY in your .env file\n"
                "   Get your key at: https://console.groq.com/keys"
            )

        return groq.Groq(api_key=api_key)

    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate a response using Groq."""
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
        """Generate a streaming response using Groq."""
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
