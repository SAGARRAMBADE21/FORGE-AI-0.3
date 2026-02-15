# Base agent
"""
Base Agent - Foundation for all FORGE agents
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import asyncio

from database_generation.agents.message import Message, MessageBus, MessageType, message_bus
from database_generation.engine.ai_engine import ai_engine


class AgentRole(str, Enum):
    """Agent roles in the team"""
    LEAD_ARCHITECT = "lead_architect"
    DATA_MODELER = "data_modeler"
    DBA_EXPERT = "dba_expert"
    SQL_WRITER = "sql_writer"
    REVIEWER = "reviewer"
    CHAT_ASSISTANT = "chat_assistant"


class AgentState(str, Enum):
    """Agent states"""
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"


class AgentMemory(BaseModel):
    """Agent's working memory"""
    
    short_term: List[Dict[str, Any]] = []  # Recent context
    decisions: List[Dict[str, Any]] = []    # Decisions made
    learnings: List[str] = []               # Things learned this session
    
    def add_context(self, context: Dict[str, Any]):
        """Add to short-term memory"""
        self.short_term.append({
            "timestamp": datetime.now().isoformat(),
            "data": context
        })
        # Keep only last 20 items
        if len(self.short_term) > 20:
            self.short_term.pop(0)
    
    def add_decision(self, decision: str, reasoning: str):
        """Record a decision"""
        self.decisions.append({
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "reasoning": reasoning
        })
    
    def add_learning(self, learning: str):
        """Record something learned"""
        self.learnings.append(learning)


class BaseAgent(ABC):
    """
    Base class for all FORGE agents
    
    Each agent has:
    - A unique ID and role
    - A system prompt defining its expertise
    - Memory for context and decisions
    - Ability to communicate via message bus
    - Access to AI engine for reasoning
    """
    
    def __init__(self, role: AgentRole, name: str = None):
        self.id = str(uuid.uuid4())[:8]
        self.role = role
        self.name = name or f"{role.value}_{self.id}"
        self.state = AgentState.IDLE
        self.memory = AgentMemory()
        self.message_bus = message_bus
        
        # Register with message bus
        self.message_bus.subscribe(self.id, self._handle_message)
        self.message_bus.subscribe(self.role.value, self._handle_message)  # Role-based routing
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Define the agent's system prompt"""
        pass
    
    @property
    def expertise(self) -> List[str]:
        """What this agent is expert at"""
        return []
    
    async def _handle_message(self, message: Message):
        """Handle incoming message"""
        self.state = AgentState.THINKING
        
        try:
            if message.type == MessageType.REQUEST:
                response = await self.handle_request(message)
                if response:
                    await self.message_bus.publish(response)
            
            elif message.type == MessageType.HANDOFF:
                await self.handle_handoff(message)
            
            elif message.type == MessageType.FEEDBACK:
                await self.handle_feedback(message)
            
            elif message.type == MessageType.BROADCAST:
                await self.handle_broadcast(message)
                
        except Exception as e:
            self.state = AgentState.ERROR
            await self.send_error(str(e), message.sender)
        
        finally:
            self.state = AgentState.IDLE
    
    @abstractmethod
    async def handle_request(self, message: Message) -> Optional[Message]:
        """Handle a request - must be implemented by subclass"""
        pass
    
    async def handle_handoff(self, message: Message):
        """Handle work handoff from another agent"""
        # Default: store in memory
        self.memory.add_context({
            "type": "handoff",
            "from": message.sender,
            "content": message.content
        })
    
    async def handle_feedback(self, message: Message):
        """Handle feedback from another agent"""
        self.memory.add_learning(f"Feedback from {message.sender}: {message.content}")
    
    async def handle_broadcast(self, message: Message):
        """Handle broadcast message"""
        self.memory.add_context({
            "type": "broadcast",
            "from": message.sender,
            "subject": message.subject,
            "content": message.content
        })
    
    async def think(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Use AI to think about something
        """
        self.state = AgentState.THINKING
        
        # Build input with memory context
        input_data = {
            "query": prompt,
            "context": context or {},
            "memory": {
                "recent_context": self.memory.short_term[-5:],
                "decisions": self.memory.decisions[-3:]
            }
        }
        
        result = ai_engine.run_agent(self.system_prompt, input_data)
        
        self.state = AgentState.IDLE
        return result
    
    async def send_message(self, 
                          recipient: str, 
                          subject: str, 
                          content: Any,
                          msg_type: MessageType = MessageType.NOTIFICATION):
        """Send a message to another agent"""
        message = Message(
            type=msg_type,
            sender=self.id,
            recipient=recipient,
            subject=subject,
            content=content
        )
        await self.message_bus.publish(message)
    
    async def request_from(self, 
                          recipient: str, 
                          subject: str, 
                          content: Any,
                          timeout: float = 30.0) -> Optional[Message]:
        """Send a request and wait for response"""
        message = Message(
            type=MessageType.REQUEST,
            sender=self.id,
            recipient=recipient,
            subject=subject,
            content=content
        )
        return await self.message_bus.request(message, timeout)
    
    async def broadcast(self, subject: str, content: Any):
        """Broadcast to all agents"""
        message = Message(
            type=MessageType.BROADCAST,
            sender=self.id,
            recipient=None,
            subject=subject,
            content=content
        )
        await self.message_bus.publish(message)
    
    async def handoff_to(self, recipient: str, subject: str, work: Any):
        """Hand off work to another agent"""
        message = Message(
            type=MessageType.HANDOFF,
            sender=self.id,
            recipient=recipient,
            subject=subject,
            content=work
        )
        await self.message_bus.publish(message)
    
    async def send_error(self, error: str, recipient: str = None):
        """Send error message"""
        message = Message(
            type=MessageType.ERROR,
            sender=self.id,
            recipient=recipient,
            subject="Error",
            content={"error": error}
        )
        await self.message_bus.publish(message)
    
    def make_decision(self, decision: str, reasoning: str):
        """Record a decision"""
        self.memory.add_decision(decision, reasoning)
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id} role={self.role.value} state={self.state.value}>"