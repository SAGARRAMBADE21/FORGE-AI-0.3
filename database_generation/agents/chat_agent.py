# Chat agent
"""
Chat Agent - Natural language interface
"""

from typing import Optional, List, Dict, Any
from database_generation.agents.base import BaseAgent, AgentRole, AgentState
from database_generation.agents.message import Message, MessageType


class ChatAgent(BaseAgent):
    """
    Chat Agent
    
    Responsibilities:
    - Understand natural language queries
    - Translate to agent requests
    - Provide explanations
    - Help users interact with the system
    """
    
    def __init__(self):
        super().__init__(AgentRole.CHAT_ASSISTANT, "ChatAssistant")
    
    @property
    def system_prompt(self) -> str:
        return """
<role>
You are the FORGE Chat Assistant, the friendly interface between users and the database engineering team.
You understand natural language and coordinate with specialist agents to fulfill requests.
</role>

<responsibilities>
1. Understand user intent from natural language
2. Route requests to appropriate agents
3. Explain schema decisions in plain language
4. Help users modify schemas
5. Answer questions about the current schema
6. Provide guidance and suggestions
</responsibilities>

<capabilities>
- Create entities: "Create a users table with email and password"
- Add fields: "Add a phone field to users"
- Relationships: "Users have many orders"
- Generate SQL: "Show me the PostgreSQL code"
- Explain: "Why do we need created_at?"
- Modify: "Make email unique"
- Remove: "Remove the phone field"
</capabilities>

<output_format>
{
    "understood": true|false,
    "intent": "create|modify|delete|query|explain|generate|unknown",
    "response": "natural language response to user",
    "action": null|{
        "type": "action_type",
        "target_agent": "agent_role",
        "params": {}
    },
    "clarification_needed": null|"question to ask",
    "suggestions": ["helpful suggestions"]
}
</output_format>

<personality>
- Be friendly and conversational
- Use simple, non-technical language when possible
- Offer suggestions proactively
- Ask for clarification when needed
- Celebrate successes with the user
</personality>
"""
    
    @property
    def expertise(self) -> List[str]:
        return [
            "natural language understanding",
            "user interaction",
            "explanation",
            "guidance"
        ]
    
    async def handle_request(self, message: Message) -> Optional[Message]:
        """Handle incoming request"""
        
        if message.type == MessageType.REQUEST:
            result = await self.process_user_input(message.content)
            return self.message_bus.respond(message, result)
        
        return None
    
    async def process_user_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user's natural language input"""
        
        self.state = AgentState.WORKING
        
        user_message = input_data.get("message", "")
        current_schema = input_data.get("schema")
        
        result = await self.think(
            "Understand and respond to this user message",
            {
                "user_message": user_message,
                "current_schema": current_schema
            }
        )
        
        # If action needed, coordinate with other agents
        action = result.get("action")
        if action:
            await self._execute_action(action)
        
        return result
    
    async def _execute_action(self, action: Dict[str, Any]):
        """Execute action by coordinating with other agents"""
        
        action_type = action.get("type")
        target_agent = action.get("target_agent")
        params = action.get("params", {})
        
        if target_agent:
            await self.send_message(
                target_agent,
                f"User Request: {action_type}",
                params,
                MessageType.REQUEST
            )
    
    async def explain(self, topic: str, context: Dict[str, Any] = None) -> str:
        """Explain something to the user"""
        
        result = await self.think(
            f"Explain this to a non-technical user: {topic}",
            context or {}
        )
        
        return result.get("response", "I'm not sure how to explain that.")