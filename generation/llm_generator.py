# generation/llm_generator.py
"""
LLM Generator - Handles LLM API calls
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import os


@dataclass
class LLMConfig:
    provider: str
    model: str
    max_tokens: int = 2048  # Reduced to 2048 to avoid rate limits
    temperature: float = 0.1


class LLMGenerator:
    """
    Handles LLM API calls for code generation
    """
    
    def __init__(self, provider: str = "anthropic", model: str = "claude-sonnet-4-20250514"):
        self.config = LLMConfig(provider=provider, model=model)
        self._client = None
        
    def _get_client(self):
        """Lazy load LLM client"""
        if self._client is None:
            if self.config.provider == "anthropic":
                try:
                    import anthropic
                    self._client = anthropic.Anthropic(
                        api_key=os.getenv("ANTHROPIC_API_KEY")
                    )
                except ImportError:
                    raise ImportError("pip install anthropic")
            elif self.config.provider == "openai":
                try:
                    import openai
                    self._client = openai.OpenAI(
                        api_key=os.getenv("OPENAI_API_KEY")
                    )
                except ImportError:
                    raise ImportError("pip install openai")
            elif self.config.provider == "groq":
                try:
                    import groq
                    self._client = groq.Groq(
                        api_key=os.getenv("GROQ_API_KEY")
                    )
                except ImportError:
                    raise ImportError("pip install groq")
            elif self.config.provider == "openrouter":
                try:
                    import openai
                    self._client = openai.OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=os.getenv("OPENROUTER_API_KEY")
                    )
                except ImportError:
                    raise ImportError("pip install openai")
        return self._client
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Any] = None
    ) -> str:
        """
        Generate code using LLM
        """
        client = self._get_client()
        
        if self.config.provider == "anthropic":
            response = client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text
            
        elif self.config.provider == "openai" or self.config.provider == "groq" or self.config.provider == "openrouter":
            response = client.chat.completions.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content
            
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
    
    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str
    ):
        """
        Generate code with streaming
        """
        client = self._get_client()
        
        if self.config.provider == "anthropic":
            with client.messages.stream(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        elif self.config.provider == "openai":
            stream = client.chat.completions.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content