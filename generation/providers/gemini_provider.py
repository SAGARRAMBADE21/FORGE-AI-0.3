# generation/providers/gemini_provider.py
"""
Gemini Provider - Handles Google Gemini API calls.
"""

import logging
import os
import time
from typing import AsyncIterator

from .base_provider import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Provider for Google Gemini models."""

    name = "gemini"
    display_name = "Google Gemini"
    supports_streaming = True
    supports_system_prompt = False  # Gemini combines system + user
    supports_json_mode = True

    def _initialize_client(self):
        """Initialize Gemini client."""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "Google Generative AI package not installed.\n"
                "Run: pip install google-generativeai"
            )

        api_key = self.config.api_key or os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "❌ Gemini API key not found!\n"
                "   Set GEMINI_API_KEY in your .env file\n"
                "   Get your key at: https://aistudio.google.com/apikey"
            )

        genai.configure(api_key=api_key)
        return genai.GenerativeModel(self.config.model)

    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate a response using Gemini."""
        # Gemini doesn't have separate system prompt, combine them
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        max_retries = kwargs.get("max_retries", 3)
        retry_delay = kwargs.get("retry_delay", 2.0)

        for attempt in range(max_retries):
            try:
                response = self.client.generate_content(
                    full_prompt,
                    generation_config={
                        "max_output_tokens": kwargs.get(
                            "max_tokens", self.config.max_tokens
                        ),
                        "temperature": kwargs.get(
                            "temperature", self.config.temperature
                        ),
                    },
                )
                return response.text

            except Exception as e:
                error_str = str(e).lower()
                if any(x in error_str for x in ["quota", "rate", "429"]):
                    wait_time = retry_delay * (2**attempt)
                    logger.warning(f"Rate limit hit, waiting {wait_time}s...")
                    time.sleep(wait_time)

                    if attempt == max_retries - 1:
                        raise Exception(
                            f"❌ Rate limit exceeded after {max_retries} retries.\n"
                            f"   Try using gemini-2.0-flash-exp (free) or wait a bit.\n"
                            f"   Error: {e}"
                        )
                else:
                    raise

        raise Exception("Failed to generate response")

    async def generate_stream(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response using Gemini."""
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        response = self.client.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            },
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
