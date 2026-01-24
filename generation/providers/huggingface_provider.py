# generation/providers/huggingface_provider.py
"""
HuggingFace Provider - Handles HuggingFace Inference API calls.
"""

import logging
import os
from typing import AsyncIterator

from .base_provider import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class HuggingFaceProvider(BaseProvider):
    """
    Provider for HuggingFace Inference API.

    Supports various open-source models hosted on HuggingFace.
    """

    name = "huggingface"
    display_name = "HuggingFace"
    supports_streaming = True
    supports_system_prompt = True
    supports_json_mode = False

    def _initialize_client(self):
        """Initialize HuggingFace client."""
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            raise ImportError(
                "HuggingFace Hub package not installed.\n"
                "Run: pip install huggingface_hub"
            )

        api_key = (
            self.config.api_key
            or os.getenv("HUGGINGFACE_API_KEY")
            or os.getenv("HF_TOKEN")
        )

        if not api_key:
            raise ValueError(
                "❌ HuggingFace API key not found!\n"
                "   Set HUGGINGFACE_API_KEY or HF_TOKEN in your .env file\n"
                "   Get your key at: https://huggingface.co/settings/tokens"
            )

        return InferenceClient(model=self.config.model, token=api_key)

    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate a response using HuggingFace."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.client.chat_completion(
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )

        return response.choices[0].message.content

    async def generate_stream(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response using HuggingFace."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        stream = self.client.chat_completion(
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
