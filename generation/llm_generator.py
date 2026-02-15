# generation/llm_generator.py
"""
LLM Generator - Handles LLM API calls with retry logic, caching, and cost tracking.

Optimizations:
- Response caching to reduce API costs
- Prompt optimization to reduce token usage
- Cost tracking with spending limits
- Better error messages
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    provider: str
    model: str
    max_tokens: int = 2048
    temperature: float = 0.1
    max_retries: int = 3
    retry_delay: float = 2.0  # Base delay in seconds

    # New optimization settings
    enable_cache: bool = False  # Caching disabled
    enable_prompt_optimization: bool = True
    enable_cost_tracking: bool = True


class LLMGenerator:
    """
    Handles LLM API calls for code generation with:
    - Retry logic with exponential backoff
    - Response caching to reduce costs
    - Prompt optimization for token reduction
    - Cost tracking and limits
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
    ):
        # Import settings to get configured values
        from config.settings import settings
        
        # Use settings if not explicitly provided
        if provider is None:
            provider = settings.llm.backend_provider
        if model is None:
            model = settings.llm.backend_model
            
        self.config = LLMConfig(provider=provider, model=model)
        self._client = None

        # Initialize optimization components (lazy loaded)
        self._cache = None
        self._optimizer = None
        self._tracker = None
        
        logger.info(f"LLMGenerator initialized: {provider}/{model}")

    @property
    def cache(self):
        """Lazy load cache."""
        if self._cache is None and self.config.enable_cache:
            from .cache_manager import get_cache
            self._cache = get_cache()
        return self._cache

    @property
    def optimizer(self):
        """Lazy load optimizer."""
        if self._optimizer is None and self.config.enable_prompt_optimization:
            from .prompt_optimizer import get_optimizer
            self._optimizer = get_optimizer()
        return self._optimizer

    @property
    def tracker(self):
        """Lazy load cost tracker."""
        if self._tracker is None and self.config.enable_cost_tracking:
            from .cost_tracker import get_tracker
            self._tracker = get_tracker()
        return self._tracker

    def _get_client(self):
        """Lazy load LLM client with better error messages."""
        if self._client is None:
            if self.config.provider == "anthropic":
                try:
                    import anthropic

                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        raise ValueError(
                            "❌ Anthropic API key not found!\n"
                            "   Set ANTHROPIC_API_KEY in your .env file\n"
                            "   Get your key at: https://console.anthropic.com/"
                        )
                    self._client = anthropic.Anthropic(api_key=api_key)
                except ImportError:
                    raise ImportError("pip install anthropic")

            elif self.config.provider == "openai":
                try:
                    import openai

                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        raise ValueError(
                            "❌ OpenAI API key not found!\n"
                            "   Set OPENAI_API_KEY in your .env file\n"
                            "   Get your key at: https://platform.openai.com/api-keys"
                        )
                    self._client = openai.OpenAI(api_key=api_key)
                except ImportError:
                    raise ImportError("pip install openai")

            else:
                raise ValueError(
                    f"❌ Unknown provider: {self.config.provider}\n"
                    f"   Supported: openai, anthropic"
                )
        return self._client

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Average of ~4 chars per token for code
        return len(text) // 4

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Any] = None,
        skip_cache: bool = False,
    ) -> str:
        """
        Generate code using LLM with caching and cost tracking.

        Args:
            system_prompt: System prompt for the LLM
            user_prompt: User prompt with the request
            context: Optional additional context
            skip_cache: If True, bypass cache

        Returns:
            Generated text response
        """
        # Optimize prompts if enabled
        if self.optimizer:
            system_prompt = self.optimizer.optimize_system_prompt(system_prompt)
            user_prompt = self.optimizer.optimize_user_prompt(user_prompt)

        # Generate response (cache disabled)
        client = self._get_client()
        response = await self._call_api(client, system_prompt, user_prompt)

        # Track usage
        if self.tracker:
            self.tracker.record_usage(
                provider=self.config.provider,
                model=self.config.model,
                input_tokens=self._estimate_tokens(system_prompt + user_prompt),
                output_tokens=self._estimate_tokens(response),
                cached=False,
            )

        return response

    async def _call_api(self, client, system_prompt: str, user_prompt: str) -> str:
        """Make the actual API call with retry logic using async patterns."""

        for attempt in range(self.config.max_retries):
            try:
                if self.config.provider == "huggingface":
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                    # Use asyncio.to_thread for non-blocking execution
                    response = await asyncio.to_thread(
                        client.chat_completion,
                        messages=messages,
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature,
                    )
                    return response.choices[0].message.content

                elif self.config.provider == "anthropic":
                    response = await asyncio.to_thread(
                        client.messages.create,
                        model=self.config.model,
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                    )
                    return response.content[0].text

                elif self.config.provider in ("openai", "groq", "openrouter"):
                    response = await asyncio.to_thread(
                        client.chat.completions.create,
                        model=self.config.model,
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    )
                    return response.choices[0].message.content

                elif self.config.provider == "gemini":
                    full_prompt = f"{system_prompt}\n\n{user_prompt}"
                    response = await asyncio.to_thread(
                        client.generate_content,
                        full_prompt,
                        generation_config={
                            "max_output_tokens": self.config.max_tokens,
                            "temperature": self.config.temperature,
                        },
                    )
                    return response.text

            except Exception as e:
                error_str = str(e).lower()

                # Handle rate limits with exponential backoff (async sleep)
                if any(x in error_str for x in ["quota", "rate", "429", "limit"]):
                    wait_time = self.config.retry_delay * (2**attempt)
                    logger.warning(
                        f"⏳ Rate limit hit, waiting {wait_time:.0f}s "
                        f"(attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    await asyncio.sleep(wait_time)  # Non-blocking sleep

                    if attempt == self.config.max_retries - 1:
                        raise Exception(
                            f"❌ Rate limit exceeded after {self.config.max_retries} retries.\n"
                            f"   Try again later or switch to a different provider.\n"
                            f"   Original error: {e}"
                        )

                # Handle authentication errors
                elif any(
                    x in error_str for x in ["auth", "key", "invalid", "unauthorized"]
                ):
                    raise ValueError(
                        f"❌ Authentication failed for {self.config.provider}!\n"
                        f"   Please check your API key in .env file.\n"
                        f"   Error: {e}"
                    )

                # Handle other errors
                else:
                    if attempt == self.config.max_retries - 1:
                        raise Exception(
                            f"❌ API call failed: {e}\n"
                            f"   Provider: {self.config.provider}\n"
                            f"   Model: {self.config.model}"
                        )
                    logger.warning(f"Retrying after error: {e}")
                    await asyncio.sleep(self.config.retry_delay)  # Non-blocking sleep

        raise Exception("Failed to generate response")

    async def generate_stream(self, system_prompt: str, user_prompt: str):
        """
        Generate code with streaming output.

        Note: Streaming responses are not cached.
        """
        client = self._get_client()

        # Optimize prompts if enabled
        if self.optimizer:
            system_prompt = self.optimizer.optimize_system_prompt(system_prompt)
            user_prompt = self.optimizer.optimize_user_prompt(user_prompt)

        if self.config.provider == "huggingface":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            stream = client.chat_completion(
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        elif self.config.provider == "anthropic":
            with client.messages.stream(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text

        elif self.config.provider in ("openai", "openrouter"):
            stream = client.chat.completions.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        elif self.config.provider == "gemini":
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = client.generate_content(
                full_prompt,
                generation_config={
                    "max_output_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                },
                stream=True,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text

    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics including cache and cost info."""
        stats = {
            "provider": self.config.provider,
            "model": self.config.model,
        }

        if self.cache:
            stats["cache"] = self.cache.stats()

        if self.optimizer:
            stats["optimization"] = self.optimizer.get_stats()

        if self.tracker:
            stats["cost"] = self.tracker.get_summary()

        return stats
