# AI engine
"""
AI Engine - Handles LLM interactions with system prompts
"""

import json
from typing import Any, Dict, Optional
from openai import OpenAI
from database_generation.db_config import config


class AIEngine:
    """Manages AI interactions using system prompts"""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.ai.api_key)
        self.model = config.ai.model
        self.max_tokens = config.ai.max_tokens
        self.temperature = config.ai.temperature
    
    def run_agent(self, 
                  system_prompt: str, 
                  user_input: Dict[str, Any],
                  response_format: str = "json") -> Dict[str, Any]:
        """
        Run an agent with system prompt and user input
        
        Args:
            system_prompt: The agent's system prompt
            user_input: Input data for the agent
            response_format: Expected response format (json/text)
        
        Returns:
            Parsed response from the agent
        """
        
        # Format user input as message
        user_message = f"""<input>
{json.dumps(user_input, indent=2, default=str)}
</input>

Analyze the input and respond according to your instructions."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"} if response_format == "json" else {"type": "text"}
            )
            
            content = response.choices[0].message.content
            
            # Parse response based on format
            if response_format == "json":
                return self._extract_json(content)
            
            return {"text": content}
            
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from response text"""
        
        # Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in the text
        start_markers = ['{', '[']
        end_markers = ['}', ']']
        
        for start, end in zip(start_markers, end_markers):
            start_idx = text.find(start)
            if start_idx != -1:
                # Find matching end
                depth = 0
                for i, char in enumerate(text[start_idx:], start_idx):
                    if char == start:
                        depth += 1
                    elif char == end:
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start_idx:i+1])
                            except json.JSONDecodeError:
                                break
        
        return {"error": "Failed to parse JSON response", "raw": text}
    
    def run_with_retry(self,
                       system_prompt: str,
                       user_input: Dict[str, Any],
                       max_retries: int = 2) -> Dict[str, Any]:
        """Run agent with retry on failure"""
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            result = self.run_agent(system_prompt, user_input)
            
            if "error" not in result:
                return result
            
            last_error = result.get("error")
            
            # Add error context for retry
            if attempt < max_retries:
                user_input["_previous_error"] = last_error
                user_input["_retry_attempt"] = attempt + 1
        
        return {"error": last_error, "success": False}


# Singleton instance
ai_engine = AIEngine()